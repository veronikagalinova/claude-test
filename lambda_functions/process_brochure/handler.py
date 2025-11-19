# -*- coding: utf-8 -*-
"""
ProcessBrochureLambda: Orchestrates Textract processing for uploaded brochures
"""
import json
import os
import logging
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from PyPDF2 import PdfReader
from io import BytesIO

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')
dynamodb_client = boto3.client('dynamodb')

# Environment variables
SOURCE_BUCKET = os.environ['SOURCE_BUCKET']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
METADATA_TABLE = os.environ['METADATA_TABLE_NAME']
TEXTRACT_SNS_TOPIC_ARN = os.environ['TEXTRACT_SNS_TOPIC_ARN']
TEXTRACT_ROLE_ARN = os.environ['TEXTRACT_ROLE_ARN']
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Page threshold for sync vs async
SYNC_PAGE_THRESHOLD = 5


def lambda_handler(event, context):
    """
    Main Lambda handler triggered by S3 PUT events

    Event format (S3):
    {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "..."},
                    "object": {"key": "..."}
                }
            }
        ]
    }
    """
    logger.info(f"ProcessBrochureLambda invoked with event: {json.dumps(event)}")

    try:
        # Parse S3 event
        for record in event.get('Records', []):
            s3_info = record.get('s3', {})
            bucket = s3_info.get('bucket', {}).get('name')
            key = s3_info.get('object', {}).get('key')

            if not bucket or not key:
                logger.warning(f"Invalid S3 event record: {record}")
                continue

            # Skip config files
            if key.startswith('config/'):
                logger.info(f"Skipping config file: {key}")
                continue

            # Process the brochure
            result = process_brochure(bucket, key)
            logger.info(f"Processing result for {key}: {result}")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Processing completed'})
        }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_brochure(bucket: str, key: str) -> Dict[str, Any]:
    """Process a single brochure file"""
    logger.info(f"Processing brochure: s3://{bucket}/{key}")

    try:
        # Get brochure metadata from S3
        s3_metadata = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = s3_metadata['ContentLength']
        content_type = s3_metadata.get('ContentType', '')
        custom_metadata = s3_metadata.get('Metadata', {})

        brochure_id = custom_metadata.get('brochure_id')
        if not brochure_id:
            # Extract brochure_id from key pattern
            brochure_id = extract_brochure_id_from_key(key)

        logger.info(f"Brochure ID: {brochure_id}, Content-Type: {content_type}, Size: {file_size}")

        # Determine file type and page count
        file_type = 'pdf' if 'pdf' in content_type.lower() else 'image'
        page_count = 1

        if file_type == 'pdf':
            page_count = get_pdf_page_count(bucket, key)
            logger.info(f"PDF has {page_count} pages")

        # Update status in DynamoDB
        update_metadata_status(brochure_id, 'PROCESSING', {
            'page_count': page_count,
            'file_type': file_type
        })

        # Decide: sync vs async processing
        if page_count < SYNC_PAGE_THRESHOLD and file_type == 'pdf':
            # Synchronous processing for small PDFs
            logger.info(f"Using synchronous Textract (pages: {page_count})")
            result = process_sync(bucket, key, brochure_id)
        else:
            # Asynchronous processing for large PDFs
            logger.info(f"Using asynchronous Textract (pages: {page_count})")
            result = process_async(bucket, key, brochure_id)

        return result

    except ClientError as e:
        logger.error(f"AWS error processing {key}: {str(e)}")
        if brochure_id:
            update_metadata_status(brochure_id, 'FAILED', {'error': str(e)})
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing {key}: {str(e)}", exc_info=True)
        if brochure_id:
            update_metadata_status(brochure_id, 'FAILED', {'error': str(e)})
        raise


def process_sync(bucket: str, key: str, brochure_id: str) -> Dict[str, Any]:
    """Synchronous Textract processing for small documents"""
    try:
        # Get document from S3
        s3_object = s3_client.get_object(Bucket=bucket, Key=key)
        document_bytes = s3_object['Body'].read()

        # Call Textract DetectDocumentText
        response = textract_client.detect_document_text(
            Document={'Bytes': document_bytes}
        )

        # Extract text from Textract response
        extracted_text = extract_text_from_textract_response(response)

        # Save results to S3
        output_key = f"{brochure_id}/textract_output.json"
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=json.dumps(response, indent=2),
            ContentType='application/json'
        )

        logger.info(f"Saved sync Textract results to: s3://{OUTPUT_BUCKET}/{output_key}")

        # Update metadata
        update_metadata_status(brochure_id, 'TEXTRACT_COMPLETE', {
            'textract_output_key': output_key,
            'extracted_text_length': len(extracted_text)
        })

        return {
            'status': 'success',
            'mode': 'sync',
            'brochure_id': brochure_id,
            'output_key': output_key
        }

    except ClientError as e:
        logger.error(f"Textract sync error: {str(e)}")
        update_metadata_status(brochure_id, 'FAILED', {'error': str(e)})
        raise


def process_async(bucket: str, key: str, brochure_id: str) -> Dict[str, Any]:
    """Asynchronous Textract processing for large documents"""
    try:
        # Start async Textract job
        response = textract_client.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            NotificationChannel={
                'SNSTopicArn': TEXTRACT_SNS_TOPIC_ARN,
                'RoleArn': TEXTRACT_ROLE_ARN
            }
        )

        job_id = response['JobId']
        logger.info(f"Started async Textract job: {job_id}")

        # Update metadata with job ID
        update_metadata_status(brochure_id, 'TEXTRACT_IN_PROGRESS', {
            'textract_job_id': job_id
        })

        return {
            'status': 'success',
            'mode': 'async',
            'brochure_id': brochure_id,
            'job_id': job_id
        }

    except ClientError as e:
        logger.error(f"Textract async error: {str(e)}")
        update_metadata_status(brochure_id, 'FAILED', {'error': str(e)})
        raise


def get_pdf_page_count(bucket: str, key: str) -> int:
    """Get the number of pages in a PDF"""
    try:
        s3_object = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_bytes = s3_object['Body'].read()

        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        return len(pdf_reader.pages)

    except Exception as e:
        logger.warning(f"Could not determine PDF page count: {str(e)}")
        return 10  # Default to async if we can't determine


def extract_brochure_id_from_key(key: str) -> str:
    """Extract brochure ID from S3 key"""
    # Key format: {store_id}/{YYYY}/{MM}/{DD}/{filename}
    parts = key.split('/')
    if len(parts) >= 1:
        store_id = parts[0]
        # Use key as unique ID
        return key.replace('/', '_').replace('.', '_')
    return key


def extract_text_from_textract_response(response: Dict) -> str:
    """Extract plain text from Textract response"""
    text_lines = []

    for block in response.get('Blocks', []):
        if block.get('BlockType') == 'LINE':
            text = block.get('Text', '')
            if text:
                text_lines.append(text)

    return '\n'.join(text_lines)


def update_metadata_status(brochure_id: str, status: str, additional_attrs: Dict[str, Any] = None):
    """Update brochure metadata status in DynamoDB"""
    try:
        from datetime import datetime

        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_attribute_names = {'#status': 'status'}
        expression_attribute_values = {
            ':status': {'S': status},
            ':updated_at': {'S': datetime.utcnow().isoformat() + 'Z'}
        }

        # Add additional attributes
        if additional_attrs:
            for key, value in additional_attrs.items():
                placeholder = f":attr_{key}"
                update_expression += f", {key} = {placeholder}"

                # Determine DynamoDB type
                if isinstance(value, str):
                    expression_attribute_values[placeholder] = {'S': value}
                elif isinstance(value, int):
                    expression_attribute_values[placeholder] = {'N': str(value)}
                elif isinstance(value, bool):
                    expression_attribute_values[placeholder] = {'BOOL': value}
                else:
                    expression_attribute_values[placeholder] = {'S': str(value)}

        dynamodb_client.update_item(
            TableName=METADATA_TABLE,
            Key={'brochure_id': {'S': brochure_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        logger.info(f"Updated metadata for {brochure_id}: status={status}")

    except ClientError as e:
        logger.error(f"Error updating metadata: {str(e)}")
        # Don't raise - metadata update failure shouldn't break processing
