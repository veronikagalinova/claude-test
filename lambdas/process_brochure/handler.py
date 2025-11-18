"""
ProcessBrochureLambda - Main handler for brochure OCR processing.

Triggered by S3 PUT events on brochures-source-bucket.
Orchestrates file inspection, Textract processing, and metadata updates.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from urllib.parse import unquote_plus
from botocore.exceptions import ClientError

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger
from common.metrics import get_metrics_publisher
from common.aws_clients import get_s3_client, get_dynamodb_client
from common.exceptions import (
    UnsupportedFileFormatError,
    InvalidFileError,
    TextractThrottlingError,
    TextractProcessingError
)

from file_inspector import FileInspector
from textract_sync import TextractSyncProcessor
from textract_async import TextractAsyncProcessor


# Environment variables
SOURCE_BUCKET_NAME = os.environ.get('SOURCE_BUCKET_NAME')
OUTPUT_BUCKET_NAME = os.environ.get('OUTPUT_BUCKET_NAME')
METADATA_TABLE_NAME = os.environ.get('METADATA_TABLE_NAME')
TEXTRACT_SNS_TOPIC_ARN = os.environ.get('TEXTRACT_SNS_TOPIC_ARN')
TEXTRACT_ROLE_ARN = os.environ.get('TEXTRACT_ROLE_ARN')
SYNC_PAGE_THRESHOLD = int(os.environ.get('SYNC_PAGE_THRESHOLD', '5'))
SYNC_SIZE_THRESHOLD_MB = int(os.environ.get('SYNC_SIZE_THRESHOLD_MB', '5'))

logger = get_logger('ProcessBrochureLambda')
metrics = get_metrics_publisher()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing brochure uploads.

    Args:
        event: S3 PUT event notification
        context: Lambda context

    Returns:
        Response dictionary with status
    """
    # Set correlation ID from request
    request_id = context.request_id if context else str(uuid.uuid4())
    logger.set_correlation_id(request_id)

    logger.info("ProcessBrochureLambda invoked", event_records=len(event.get('Records', [])))

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
        metrics.put_metric('BrochuresProcessed', processed_count)
        if error_count > 0:
            metrics.put_metric('ProcessingErrors', error_count)

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
        metrics.put_metric('ProcessingErrors', 1)
        metrics.flush()

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_s3_record(record: Dict[str, Any]):
    """
    Process a single S3 event record.

    Args:
        record: S3 event record

    Raises:
        Various exceptions for different failure modes
    """
    # Extract S3 information
    s3_info = record.get('s3', {})
    bucket = s3_info.get('bucket', {}).get('name')
    key = unquote_plus(s3_info.get('object', {}).get('key', ''))
    size = s3_info.get('object', {}).get('size', 0)

    logger.info(
        "Processing S3 object",
        bucket=bucket,
        key=key,
        size=size
    )

    # Generate brochure ID
    brochure_id = str(uuid.uuid4())

    # Parse store information from S3 key
    # Expected format: {store_id}/{year}/{month}/{day}/{filename}
    key_parts = key.split('/')
    if len(key_parts) < 5:
        logger.error("Invalid S3 key format", key=key)
        raise ValueError(f"Invalid S3 key format: {key}")

    store_id = key_parts[0]
    filename = key_parts[-1]

    logger.info(
        "Parsed S3 key",
        brochure_id=brochure_id,
        store_id=store_id,
        filename=filename
    )

    try:
        # Download file from S3
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_bytes = response['Body'].read()

        logger.info(
            "Downloaded file from S3",
            brochure_id=brochure_id,
            file_size=len(file_bytes)
        )

        # Inspect file
        inspector = FileInspector(
            sync_page_threshold=SYNC_PAGE_THRESHOLD,
            sync_size_threshold_mb=SYNC_SIZE_THRESHOLD_MB
        )

        file_info = inspector.inspect_file(file_bytes, filename)

        # Create initial metadata record
        create_metadata_record(
            brochure_id=brochure_id,
            store_id=store_id,
            filename=filename,
            s3_bucket=bucket,
            s3_key=key,
            file_info=file_info
        )

        # Process based on mode
        if file_info['processing_mode'] == 'SYNC':
            process_synchronous(
                brochure_id=brochure_id,
                store_id=store_id,
                file_bytes=file_bytes,
                file_info=file_info,
                s3_key=key
            )
            metrics.increment_counter('TextractSyncJobs', {'StoreId': store_id})
        else:
            process_asynchronous(
                brochure_id=brochure_id,
                store_id=store_id,
                source_bucket=bucket,
                source_key=key,
                file_info=file_info
            )
            metrics.increment_counter('TextractAsyncJobs', {'StoreId': store_id})

    except UnsupportedFileFormatError as e:
        logger.error("Unsupported file format", brochure_id=brochure_id, error=str(e))
        update_metadata_status(brochure_id, 'UNSUPPORTED_FORMAT', str(e))
        metrics.increment_counter('UnsupportedFormats')
        raise

    except InvalidFileError as e:
        logger.error("Invalid file", brochure_id=brochure_id, error=str(e))
        update_metadata_status(brochure_id, 'INVALID_FORMAT', str(e))
        metrics.increment_counter('InvalidFiles')
        raise

    except TextractThrottlingError as e:
        logger.error("Textract throttled", brochure_id=brochure_id, error=str(e))
        update_metadata_status(brochure_id, 'TEXTRACT_IN_PROGRESS', 'Throttled, will retry')
        raise

    except Exception as e:
        logger.log_exception(e, "Unexpected error processing brochure", brochure_id=brochure_id)
        update_metadata_status(brochure_id, 'FAILED', str(e))
        raise


def process_synchronous(
    brochure_id: str,
    store_id: str,
    file_bytes: bytes,
    file_info: Dict,
    s3_key: str
):
    """
    Process brochure using synchronous Textract API.

    Args:
        brochure_id: Unique brochure identifier
        store_id: Store identifier
        file_bytes: File content
        file_info: File inspection results
        s3_key: Source S3 key
    """
    logger.info("Processing with synchronous Textract", brochure_id=brochure_id)

    processor = TextractSyncProcessor()

    # Run Textract OCR
    textract_response = processor.process_document(file_bytes, brochure_id)

    # Construct output S3 key
    # Format: {store_id}/{year}/{month}/{day}/{brochure_id}/textract-result.json
    key_parts = s3_key.split('/')
    output_key = f"{key_parts[0]}/{key_parts[1]}/{key_parts[2]}/{key_parts[3]}/{brochure_id}/textract-result.json"

    # Store result to S3
    processor.store_result(
        textract_response=textract_response,
        output_bucket=OUTPUT_BUCKET_NAME,
        output_key=output_key,
        brochure_id=brochure_id
    )

    # Update metadata
    update_metadata_status(
        brochure_id=brochure_id,
        status='OCR_COMPLETE',
        error_message=None,
        additional_fields={
            'textract_mode': 'SYNC',
            'textract_result_s3_key': output_key,
            'page_count': file_info['page_count'],
            'ocr_complete_time': datetime.utcnow().isoformat() + 'Z'
        }
    )

    logger.info("Synchronous processing complete", brochure_id=brochure_id)


def process_asynchronous(
    brochure_id: str,
    store_id: str,
    source_bucket: str,
    source_key: str,
    file_info: Dict
):
    """
    Process brochure using asynchronous Textract API.

    Args:
        brochure_id: Unique brochure identifier
        store_id: Store identifier
        source_bucket: S3 bucket containing the file
        source_key: S3 key for the file
        file_info: File inspection results
    """
    logger.info("Processing with asynchronous Textract", brochure_id=brochure_id)

    processor = TextractAsyncProcessor(
        sns_topic_arn=TEXTRACT_SNS_TOPIC_ARN,
        textract_role_arn=TEXTRACT_ROLE_ARN
    )

    # Start Textract job
    job_id = processor.start_document_analysis(
        source_bucket=source_bucket,
        source_key=source_key,
        brochure_id=brochure_id
    )

    # Update metadata
    update_metadata_status(
        brochure_id=brochure_id,
        status='TEXTRACT_IN_PROGRESS',
        error_message=None,
        additional_fields={
            'textract_mode': 'ASYNC',
            'textract_job_id': job_id,
            'page_count': file_info['page_count']
        }
    )

    logger.info("Asynchronous processing started", brochure_id=brochure_id, job_id=job_id)


def create_metadata_record(
    brochure_id: str,
    store_id: str,
    filename: str,
    s3_bucket: str,
    s3_key: str,
    file_info: Dict
):
    """
    Create initial metadata record in DynamoDB.

    Args:
        brochure_id: Unique brochure identifier
        store_id: Store identifier
        filename: Original filename
        s3_bucket: S3 bucket name
        s3_key: S3 key
        file_info: File inspection results
    """
    dynamodb_client = get_dynamodb_client()
    timestamp = datetime.utcnow().isoformat() + 'Z'

    item = {
        'brochure_id': {'S': brochure_id},
        'store_id': {'S': store_id},
        'brochure_filename': {'S': filename},
        's3_bucket': {'S': s3_bucket},
        's3_key': {'S': s3_key},
        'file_size_bytes': {'N': str(file_info['file_size_bytes'])},
        'upload_time': {'S': timestamp},
        'status': {'S': 'UPLOADED'},
        'created_at': {'S': timestamp},
        'updated_at': {'S': timestamp}
    }

    try:
        dynamodb_client.put_item(
            TableName=METADATA_TABLE_NAME,
            Item=item
        )
        logger.info("Metadata record created", brochure_id=brochure_id)
    except ClientError as e:
        logger.error(
            "Failed to create metadata record",
            brochure_id=brochure_id,
            error=str(e)
        )
        raise


def update_metadata_status(
    brochure_id: str,
    status: str,
    error_message: str = None,
    additional_fields: Dict = None
):
    """
    Update brochure metadata status in DynamoDB.

    Args:
        brochure_id: Unique brochure identifier
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

            # Determine DynamoDB type based on Python type
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
