"""
TextractCallbackLambda - Handles Textract async job completion notifications.

Triggered by SNS messages from textract-job-completion-topic.
Retrieves Textract results, stores to S3, and updates DynamoDB metadata.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from botocore.exceptions import ClientError

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger
from common.metrics import get_metrics_publisher
from common.aws_clients import get_s3_client, get_dynamodb_client
from common.exceptions import TextractProcessingError

from result_retriever import TextractResultRetriever


# Environment variables
OUTPUT_BUCKET_NAME = os.environ.get('OUTPUT_BUCKET_NAME')
METADATA_TABLE_NAME = os.environ.get('METADATA_TABLE_NAME')

logger = get_logger('TextractCallbackLambda')
metrics = get_metrics_publisher()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Textract job completion notifications.

    Args:
        event: SNS event with Textract job completion message
        context: Lambda context

    Returns:
        Response dictionary with status
    """
    # Set correlation ID
    request_id = context.request_id if context else str(uuid.uuid4())
    logger.set_correlation_id(request_id)

    logger.info("TextractCallbackLambda invoked", event_records=len(event.get('Records', [])))

    processed_count = 0
    error_count = 0

    try:
        # Process each SNS record
        for record in event.get('Records', []):
            try:
                process_sns_record(record)
                processed_count += 1
            except Exception as e:
                error_count += 1
                logger.log_exception(e, "Failed to process SNS record")

        # Publish metrics
        metrics.put_metric('TextractJobsCompleted', processed_count)
        if error_count > 0:
            metrics.put_metric('TextractCallbackErrors', error_count)

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
        metrics.put_metric('TextractCallbackErrors', 1)
        metrics.flush()

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_sns_record(record: Dict[str, Any]):
    """
    Process a single SNS record containing Textract job completion.

    Args:
        record: SNS event record

    Raises:
        TextractProcessingError: If processing fails
    """
    # Parse SNS message
    sns = record.get('Sns', {})
    message_str = sns.get('Message', '{}')

    try:
        message = json.loads(message_str)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse SNS message", error=str(e))
        raise TextractProcessingError(f"Invalid SNS message JSON: {str(e)}")

    # Extract Textract job information
    job_id = message.get('JobId')
    status = message.get('Status')
    timestamp = message.get('Timestamp')
    document_location = message.get('DocumentLocation', {})

    if not job_id:
        logger.error("SNS message missing JobId", message=message)
        raise TextractProcessingError("SNS message missing JobId")

    logger.info(
        "Processing Textract job completion",
        job_id=job_id,
        status=status,
        timestamp=timestamp
    )

    # Get brochure metadata from DynamoDB using job_id
    brochure_id = get_brochure_id_by_job_id(job_id)

    if not brochure_id:
        logger.error(
            "No brochure found for Textract job ID",
            job_id=job_id
        )
        raise TextractProcessingError(
            f"No brochure found for job_id: {job_id}",
            job_id=job_id
        )

    logger.info(
        "Found brochure for Textract job",
        job_id=job_id,
        brochure_id=brochure_id
    )

    # Handle different job statuses
    if status == 'SUCCEEDED':
        handle_job_success(job_id, brochure_id, document_location)
    elif status == 'FAILED':
        handle_job_failure(job_id, brochure_id, message.get('StatusMessage', 'Unknown error'))
    else:
        logger.warning(
            "Unexpected Textract job status",
            job_id=job_id,
            brochure_id=brochure_id,
            status=status
        )


def handle_job_success(job_id: str, brochure_id: str, document_location: Dict):
    """
    Handle successful Textract job completion.

    Args:
        job_id: Textract job ID
        brochure_id: Brochure identifier
        document_location: Document location from SNS message
    """
    logger.info(
        "Handling successful Textract job",
        job_id=job_id,
        brochure_id=brochure_id
    )

    try:
        # Retrieve Textract results with pagination
        retriever = TextractResultRetriever()
        textract_response = retriever.retrieve_results(job_id, brochure_id)

        # Get brochure metadata to construct output path
        metadata = get_brochure_metadata(brochure_id)
        s3_key = metadata.get('s3_key', {}).get('S', '')

        # Construct output S3 key
        # Format: {store_id}/{year}/{month}/{day}/{brochure_id}/textract-result.json
        key_parts = s3_key.split('/')
        if len(key_parts) >= 4:
            output_key = f"{key_parts[0]}/{key_parts[1]}/{key_parts[2]}/{key_parts[3]}/{brochure_id}/textract-result.json"
        else:
            # Fallback if key format is unexpected
            output_key = f"{brochure_id}/textract-result.json"

        # Store results to S3
        store_textract_results(
            textract_response=textract_response,
            output_bucket=OUTPUT_BUCKET_NAME,
            output_key=output_key,
            brochure_id=brochure_id
        )

        # Update metadata
        page_count = textract_response.get('DocumentMetadata', {}).get('Pages', 0)
        update_metadata_status(
            brochure_id=brochure_id,
            status='OCR_COMPLETE',
            error_message=None,
            additional_fields={
                'textract_result_s3_key': output_key,
                'page_count': page_count,
                'ocr_complete_time': datetime.utcnow().isoformat() + 'Z'
            }
        )

        logger.info(
            "Textract job processed successfully",
            job_id=job_id,
            brochure_id=brochure_id,
            page_count=page_count
        )

        metrics.increment_counter('TextractPagesRetrieved', page_count)

    except Exception as e:
        logger.log_exception(
            e,
            "Error processing successful Textract job",
            job_id=job_id,
            brochure_id=brochure_id
        )
        update_metadata_status(
            brochure_id=brochure_id,
            status='OCR_FAILED',
            error_message=f"Result retrieval failed: {str(e)}"
        )
        raise


def handle_job_failure(job_id: str, brochure_id: str, error_message: str):
    """
    Handle failed Textract job.

    Args:
        job_id: Textract job ID
        brochure_id: Brochure identifier
        error_message: Error message from Textract
    """
    logger.error(
        "Textract job failed",
        job_id=job_id,
        brochure_id=brochure_id,
        error_message=error_message
    )

    update_metadata_status(
        brochure_id=brochure_id,
        status='OCR_FAILED',
        error_message=error_message
    )

    metrics.increment_counter('TextractJobsFailed')


def get_brochure_id_by_job_id(job_id: str) -> str:
    """
    Find brochure ID associated with Textract job ID.

    Uses DynamoDB scan to find record with matching textract_job_id.
    In production, consider adding a GSI on textract_job_id for better performance.

    Args:
        job_id: Textract job ID

    Returns:
        Brochure ID or None if not found
    """
    dynamodb_client = get_dynamodb_client()

    try:
        # Scan for matching job_id (not optimal, but works for MVP)
        # TODO: Add GSI on textract_job_id for production
        response = dynamodb_client.scan(
            TableName=METADATA_TABLE_NAME,
            FilterExpression='textract_job_id = :job_id',
            ExpressionAttributeValues={
                ':job_id': {'S': job_id}
            },
            Limit=1
        )

        items = response.get('Items', [])
        if items:
            return items[0].get('brochure_id', {}).get('S')

        return None

    except ClientError as e:
        logger.error(
            "Failed to query DynamoDB for job_id",
            job_id=job_id,
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
            raise TextractProcessingError(
                f"Brochure not found: {brochure_id}",
                brochure_id=brochure_id
            )

        return item

    except ClientError as e:
        logger.error(
            "Failed to get brochure metadata",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise


def store_textract_results(
    textract_response: Dict,
    output_bucket: str,
    output_key: str,
    brochure_id: str
):
    """
    Store Textract results to S3 as JSON.

    Args:
        textract_response: Textract API response
        output_bucket: S3 bucket for results
        output_key: S3 key for result file
        brochure_id: Brochure identifier
    """
    logger.info(
        "Storing Textract results to S3",
        brochure_id=brochure_id,
        output_bucket=output_bucket,
        output_key=output_key
    )

    try:
        s3_client = get_s3_client()

        # Convert to JSON
        result_json = json.dumps(textract_response, indent=2)

        # Upload to S3
        s3_client.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=result_json.encode('utf-8'),
            ContentType='application/json',
            Metadata={
                'brochure_id': brochure_id,
                'processing_mode': 'ASYNC'
            }
        )

        result_size = len(result_json)
        logger.info(
            "Textract results stored successfully",
            brochure_id=brochure_id,
            output_s3_uri=f"s3://{output_bucket}/{output_key}",
            size_bytes=result_size
        )

        metrics.put_metric('ResultSizeBytes', result_size)

    except ClientError as e:
        logger.error(
            "Failed to store Textract results to S3",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise TextractProcessingError(
            f"Failed to store results: {str(e)}",
            brochure_id=brochure_id
        )


def update_metadata_status(
    brochure_id: str,
    status: str,
    error_message: str = None,
    additional_fields: Dict = None
):
    """
    Update brochure metadata in DynamoDB.

    Args:
        brochure_id: Brochure identifier
        status: New status value
        error_message: Optional error message
        additional_fields: Optional additional fields to update
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

    if additional_fields:
        for key, value in additional_fields.items():
            placeholder = f":field_{key}"
            update_expression += f", {key} = {placeholder}"

            # Determine DynamoDB type
            if isinstance(value, str):
                expression_attribute_values[placeholder] = {'S': value}
            elif isinstance(value, int):
                expression_attribute_values[placeholder] = {'N': str(value)}
            elif isinstance(value, bool):
                expression_attribute_values[placeholder] = {'BOOL': value}

    try:
        dynamodb_client.update_item(
            TableName=METADATA_TABLE_NAME,
            Key={'brochure_id': {'S': brochure_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        logger.info(
            "Metadata status updated",
            brochure_id=brochure_id,
            status=status
        )

    except ClientError as e:
        logger.error(
            "Failed to update metadata",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise
