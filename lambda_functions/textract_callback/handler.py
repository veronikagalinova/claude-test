# -*- coding: utf-8 -*-
"""
TextractCallbackLambda: Retrieves async Textract results and saves to S3
"""
import json
import os
import logging
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
textract_client = boto3.client('textract')
s3_client = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')

# Environment variables
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
METADATA_TABLE = os.environ['METADATA_TABLE_NAME']
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


def lambda_handler(event, context):
    """
    Main Lambda handler triggered by SNS from Textract

    Event format (SNS):
    {
        "Records": [
            {
                "Sns": {
                    "Message": "{\"JobId\": \"...\", \"Status\": \"SUCCEEDED\", ...}"
                }
            }
        ]
    }
    """
    logger.info(f"TextractCallbackLambda invoked with event: {json.dumps(event)}")

    try:
        for record in event.get('Records', []):
            sns_message = record.get('Sns', {}).get('Message', '{}')
            message = json.loads(sns_message)

            job_id = message.get('JobId')
            status = message.get('Status')

            logger.info(f"Textract job {job_id} status: {status}")

            if status == 'SUCCEEDED':
                process_textract_results(job_id)
            else:
                logger.error(f"Textract job {job_id} failed with status: {status}")
                # Update metadata to reflect failure
                update_brochure_status_by_job_id(job_id, 'FAILED', {
                    'error': f"Textract job failed: {status}"
                })

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Callback processed'})
        }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_textract_results(job_id: str):
    """Retrieve and save Textract job results"""
    logger.info(f"Processing Textract job results: {job_id}")

    try:
        # Get brochure_id from DynamoDB using job_id
        brochure_id = get_brochure_id_by_job_id(job_id)

        if not brochure_id:
            logger.error(f"Could not find brochure_id for job_id: {job_id}")
            return

        # Retrieve all results (with pagination)
        all_blocks = []
        next_token = None

        while True:
            if next_token:
                response = textract_client.get_document_text_detection(
                    JobId=job_id,
                    NextToken=next_token
                )
            else:
                response = textract_client.get_document_text_detection(JobId=job_id)

            all_blocks.extend(response.get('Blocks', []))

            next_token = response.get('NextToken')
            if not next_token:
                break

            logger.info(f"Retrieved {len(all_blocks)} blocks so far, continuing pagination...")

        logger.info(f"Total blocks retrieved: {len(all_blocks)}")

        # Construct full result
        full_result = {
            'JobId': job_id,
            'Status': response.get('JobStatus'),
            'Blocks': all_blocks,
            'DocumentMetadata': response.get('DocumentMetadata', {}),
            'DetectDocumentTextModelVersion': response.get('DetectDocumentTextModelVersion', '')
        }

        # Extract text
        extracted_text = extract_text_from_blocks(all_blocks)
        logger.info(f"Extracted {len(extracted_text)} characters of text")

        # Save to S3
        output_key = f"{brochure_id}/textract_output.json"
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=json.dumps(full_result, indent=2, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json',
            Metadata={
                'brochure_id': brochure_id,
                'job_id': job_id,
                'text_length': str(len(extracted_text))
            }
        )

        logger.info(f"Saved Textract results to: s3://{OUTPUT_BUCKET}/{output_key}")

        # Update metadata
        update_metadata_status(brochure_id, 'TEXTRACT_COMPLETE', {
            'textract_output_key': output_key,
            'extracted_text_length': len(extracted_text)
        })

    except ClientError as e:
        logger.error(f"AWS error processing job {job_id}: {str(e)}")
        if brochure_id:
            update_metadata_status(brochure_id, 'FAILED', {'error': str(e)})
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing job {job_id}: {str(e)}", exc_info=True)
        if brochure_id:
            update_metadata_status(brochure_id, 'FAILED', {'error': str(e)})
        raise


def get_brochure_id_by_job_id(job_id: str) -> str:
    """Find brochure_id by searching for textract_job_id in DynamoDB"""
    try:
        # Scan table looking for matching job_id
        # Note: This is inefficient for large tables - consider adding GSI if needed
        response = dynamodb_client.scan(
            TableName=METADATA_TABLE,
            FilterExpression='textract_job_id = :job_id',
            ExpressionAttributeValues={
                ':job_id': {'S': job_id}
            },
            Limit=1
        )

        items = response.get('Items', [])
        if items:
            return items[0]['brochure_id']['S']

        return None

    except ClientError as e:
        logger.error(f"Error querying DynamoDB: {str(e)}")
        return None


def extract_text_from_blocks(blocks: List[Dict]) -> str:
    """Extract plain text from Textract blocks"""
    text_lines = []

    for block in blocks:
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


def update_brochure_status_by_job_id(job_id: str, status: str, additional_attrs: Dict[str, Any] = None):
    """Update brochure status by finding it via job_id"""
    brochure_id = get_brochure_id_by_job_id(job_id)
    if brochure_id:
        update_metadata_status(brochure_id, status, additional_attrs)
