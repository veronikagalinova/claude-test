"""
KeywordSearchLambda - Searches Textract results for keywords and triggers notifications.

Triggered by S3 PUT events on textract-output-bucket.
Parses Textract JSON, searches for keywords, and publishes matches to SNS.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from urllib.parse import unquote_plus
from botocore.exceptions import ClientError

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger
from common.metrics import get_metrics_publisher
from common.aws_clients import get_s3_client, get_dynamodb_client, get_sns_client
from common.exceptions import ConfigurationError, KeywordConfigError

from textract_parser import TextractParser
from keyword_matcher import KeywordMatcher
from config_loader import ConfigLoader


# Environment variables
OUTPUT_BUCKET_NAME = os.environ.get('OUTPUT_BUCKET_NAME')
METADATA_TABLE_NAME = os.environ.get('METADATA_TABLE_NAME')
KEYWORD_FOUND_TOPIC_ARN = os.environ.get('KEYWORD_FOUND_TOPIC_ARN')
CONFIG_BUCKET_NAME = os.environ.get('CONFIG_BUCKET_NAME') or os.environ.get('SOURCE_BUCKET_NAME')
KEYWORD_CONFIG_S3_KEY = os.environ.get('KEYWORD_CONFIG_S3_KEY', 'config/keyword-config.json')

logger = get_logger('KeywordSearchLambda')
metrics = get_metrics_publisher()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for keyword search in Textract results.

    Args:
        event: S3 PUT event notification for Textract result
        context: Lambda context

    Returns:
        Response dictionary with status
    """
    # Set correlation ID
    request_id = context.request_id if context else str(uuid.uuid4())
    logger.set_correlation_id(request_id)

    logger.info("KeywordSearchLambda invoked", event_records=len(event.get('Records', [])))

    processed_count = 0
    error_count = 0

    try:
        # Process each S3 record
        for record in event.get('Records', []):
            try:
                process_s3_record(record)
                processed_count += 1
            except Exception as e:
                error_count += 1
                logger.log_exception(e, "Failed to process S3 record")

        # Publish metrics
        if error_count > 0:
            metrics.put_metric('KeywordSearchErrors', error_count)

        metrics.flush()

        return {
            'statusCode': 200 if error_count == 0 else 207,
            'body': json.dumps({
                'processed': processed_count,
                'errors': error_count
            })
        }

    except Exception as e:
        logger.log_exception(e, "Fatal error in lambda_handler")
        metrics.put_metric('KeywordSearchErrors', 1)
        metrics.flush()

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_s3_record(record: Dict[str, Any]):
    """
    Process a single S3 event record for Textract result.

    Args:
        record: S3 event record
    """
    # Extract S3 information
    s3_info = record.get('s3', {})
    bucket = s3_info.get('bucket', {}).get('name')
    key = unquote_plus(s3_info.get('object', {}).get('key', ''))

    logger.info(
        "Processing Textract result",
        bucket=bucket,
        key=key
    )

    # Parse brochure information from S3 key
    # Expected format: {store_id}/{year}/{month}/{day}/{brochure_id}/textract-result.json
    key_parts = key.split('/')
    if len(key_parts) < 6:
        logger.error("Invalid S3 key format for Textract result", key=key)
        raise ValueError(f"Invalid S3 key format: {key}")

    store_id = key_parts[0]
    brochure_id = key_parts[4]

    logger.info(
        "Parsed S3 key",
        store_id=store_id,
        brochure_id=brochure_id
    )

    try:
        # Load Textract result from S3
        textract_response = load_textract_result(bucket, key, brochure_id)

        # Load keywords for store
        config_loader = ConfigLoader(
            config_bucket=CONFIG_BUCKET_NAME,
            config_key=KEYWORD_CONFIG_S3_KEY
        )

        keywords = config_loader.get_keywords_for_store(store_id)

        if not keywords:
            logger.info(
                "No keywords configured for store, skipping search",
                store_id=store_id,
                brochure_id=brochure_id
            )
            update_metadata_status(brochure_id, 'NO_MATCHES', 'No keywords configured')
            return

        logger.info(
            "Loaded keywords for search",
            store_id=store_id,
            brochure_id=brochure_id,
            keyword_count=len(keywords)
        )

        # Parse Textract result
        parser = TextractParser()
        text_blocks = parser.parse_textract_result(textract_response)

        if not text_blocks:
            logger.warning(
                "No text blocks found in Textract result",
                brochure_id=brochure_id
            )
            update_metadata_status(brochure_id, 'NO_MATCHES', 'No text found')
            return

        # Get full text by page
        pages_text = parser.get_full_text_by_page(text_blocks)

        # Search for keywords
        matcher = KeywordMatcher(context_chars=50)
        matches = matcher.find_keyword_matches(keywords, pages_text)

        # Record metrics
        metrics.put_metric(
            'KeywordsMatched',
            len(matches),
            dimensions={'StoreId': store_id}
        )

        if matches:
            # Process matches
            process_keyword_matches(
                brochure_id=brochure_id,
                store_id=store_id,
                matches=matches,
                config_loader=config_loader
            )

            metrics.increment_counter('BrochuresWithMatches', {'StoreId': store_id})

            logger.info(
                "Keyword matches found and processed",
                brochure_id=brochure_id,
                match_count=len(matches)
            )
        else:
            # No matches found
            update_metadata_status(brochure_id, 'NO_MATCHES')

            metrics.increment_counter('BrochuresWithoutMatches', {'StoreId': store_id})

            logger.info(
                "No keyword matches found",
                brochure_id=brochure_id
            )

    except ConfigurationError as e:
        logger.error(
            "Configuration error",
            brochure_id=brochure_id,
            error=str(e)
        )
        update_metadata_status(brochure_id, 'PARSE_ERROR', str(e))
        raise

    except Exception as e:
        logger.log_exception(
            e,
            "Error searching for keywords",
            brochure_id=brochure_id
        )
        update_metadata_status(brochure_id, 'PARSE_ERROR', str(e))
        raise


def load_textract_result(bucket: str, key: str, brochure_id: str) -> Dict:
    """
    Load Textract result JSON from S3.

    Args:
        bucket: S3 bucket name
        key: S3 key
        brochure_id: Brochure identifier for logging

    Returns:
        Textract response dictionary
    """
    logger.info(
        "Loading Textract result from S3",
        brochure_id=brochure_id,
        bucket=bucket,
        key=key
    )

    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket, Key=key)
        result_json = response['Body'].read().decode('utf-8')
        textract_response = json.loads(result_json)

        logger.info(
            "Textract result loaded",
            brochure_id=brochure_id,
            block_count=len(textract_response.get('Blocks', []))
        )

        return textract_response

    except ClientError as e:
        logger.error(
            "Failed to load Textract result from S3",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise

    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in Textract result",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise


def process_keyword_matches(
    brochure_id: str,
    store_id: str,
    matches: List[Dict],
    config_loader: ConfigLoader
):
    """
    Process keyword matches and trigger notifications.

    Args:
        brochure_id: Brochure identifier
        store_id: Store identifier
        matches: List of keyword matches
        config_loader: Configuration loader instance
    """
    # Get brochure metadata
    metadata = get_brochure_metadata(brochure_id)

    # Get store info for notification
    try:
        store_info = config_loader.get_store_info(store_id)
        store_name = store_info.get('store_name', store_id)
    except KeywordConfigError:
        store_name = store_id

    # Aggregate match statistics
    matcher = KeywordMatcher()
    stats = matcher.aggregate_matches(matches)

    # Prepare notification message
    notification_message = {
        'brochure_id': brochure_id,
        'store_id': store_id,
        'store_name': store_name,
        'brochure_filename': metadata.get('brochure_filename', {}).get('S', 'unknown'),
        's3_bucket': metadata.get('s3_bucket', {}).get('S', ''),
        's3_key': metadata.get('s3_key', {}).get('S', ''),
        'upload_time': metadata.get('upload_time', {}).get('S', ''),
        'ocr_complete_time': metadata.get('ocr_complete_time', {}).get('S', ''),
        'notification_time': datetime.utcnow().isoformat() + 'Z',
        'keywords_matched': stats['unique_keywords'],
        'match_count': stats['total_matches'],
        'match_details': matches[:20]  # Limit to first 20 matches to avoid message size issues
    }

    # Publish to SNS
    publish_notification(notification_message, brochure_id)

    # Update metadata in DynamoDB
    update_metadata_with_matches(
        brochure_id=brochure_id,
        keywords_matched=stats['unique_keywords'],
        match_count=stats['total_matches'],
        match_details=matches[:100]  # Store up to 100 matches in DynamoDB
    )

    logger.info(
        "Keyword matches processed and notification sent",
        brochure_id=brochure_id,
        unique_keywords=len(stats['unique_keywords']),
        total_matches=stats['total_matches']
    )


def publish_notification(message: Dict, brochure_id: str):
    """
    Publish notification to SNS topic.

    Args:
        message: Notification message dictionary
        brochure_id: Brochure identifier for logging
    """
    logger.info(
        "Publishing keyword match notification",
        brochure_id=brochure_id,
        topic_arn=KEYWORD_FOUND_TOPIC_ARN
    )

    try:
        sns_client = get_sns_client()

        # Create subject line
        subject = f"Keyword Match Found: {message['store_name']} - {message['brochure_filename']}"

        # Publish to SNS
        response = sns_client.publish(
            TopicArn=KEYWORD_FOUND_TOPIC_ARN,
            Subject=subject[:100],  # SNS subject limit is 100 characters
            Message=json.dumps(message, indent=2)
        )

        message_id = response.get('MessageId')

        logger.info(
            "Notification published successfully",
            brochure_id=brochure_id,
            message_id=message_id
        )

    except ClientError as e:
        logger.error(
            "Failed to publish notification",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise


def get_brochure_metadata(brochure_id: str) -> Dict:
    """
    Get brochure metadata from DynamoDB.

    Args:
        brochure_id: Brochure identifier

    Returns:
        DynamoDB item
    """
    dynamodb_client = get_dynamodb_client()

    try:
        response = dynamodb_client.get_item(
            TableName=METADATA_TABLE_NAME,
            Key={'brochure_id': {'S': brochure_id}}
        )

        item = response.get('Item', {})
        if not item:
            logger.error("Brochure not found in DynamoDB", brochure_id=brochure_id)
            raise ValueError(f"Brochure not found: {brochure_id}")

        return item

    except ClientError as e:
        logger.error(
            "Failed to get brochure metadata",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise


def update_metadata_status(brochure_id: str, status: str, error_message: str = None):
    """
    Update brochure status in DynamoDB.

    Args:
        brochure_id: Brochure identifier
        status: New status value
        error_message: Optional error message
    """
    dynamodb_client = get_dynamodb_client()
    timestamp = datetime.utcnow().isoformat() + 'Z'

    update_expression = "SET #status = :status, updated_at = :timestamp"
    expression_attribute_names = {'#status': 'status'}
    expression_attribute_values = {
        ':status': {'S': status},
        ':timestamp': {'S': timestamp}
    }

    if error_message:
        update_expression += ", error_message = :error"
        expression_attribute_values[':error'] = {'S': error_message}

    try:
        dynamodb_client.update_item(
            TableName=METADATA_TABLE_NAME,
            Key={'brochure_id': {'S': brochure_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        logger.info("Metadata status updated", brochure_id=brochure_id, status=status)

    except ClientError as e:
        logger.error(
            "Failed to update metadata",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise


def update_metadata_with_matches(
    brochure_id: str,
    keywords_matched: List[str],
    match_count: int,
    match_details: List[Dict]
):
    """
    Update brochure metadata with keyword match information.

    Args:
        brochure_id: Brochure identifier
        keywords_matched: List of matched keywords
        match_count: Total number of matches
        match_details: List of match detail dictionaries
    """
    dynamodb_client = get_dynamodb_client()
    timestamp = datetime.utcnow().isoformat() + 'Z'

    # Convert match details to DynamoDB format
    match_details_db = []
    for match in match_details:
        match_details_db.append({
            'M': {
                'keyword': {'S': match['keyword']},
                'page': {'N': str(match['page'])},
                'line': {'N': str(match['line'])},
                'context': {'S': match['context']},
                'confidence': {'N': str(match['confidence'])}
            }
        })

    try:
        dynamodb_client.update_item(
            TableName=METADATA_TABLE_NAME,
            Key={'brochure_id': {'S': brochure_id}},
            UpdateExpression="SET #status = :status, keywords_matched = :keywords, match_count = :count, match_details = :details, notification_sent = :sent, notification_time = :time, updated_at = :timestamp",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'MATCH_FOUND'},
                ':keywords': {'SS': keywords_matched},
                ':count': {'N': str(match_count)},
                ':details': {'L': match_details_db},
                ':sent': {'BOOL': True},
                ':time': {'S': timestamp},
                ':timestamp': {'S': timestamp}
            }
        )

        logger.info(
            "Metadata updated with match information",
            brochure_id=brochure_id,
            keywords_matched=len(keywords_matched),
            match_count=match_count
        )

    except ClientError as e:
        logger.error(
            "Failed to update metadata with matches",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise
