# -*- coding: utf-8 -*-
"""
CrawlerLambda: Downloads brochures from store URLs with web scraping support
"""
import json
import os
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError
import requests
from scraper import BrochureScraper, ScrapingError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')
cloudwatch_client = boto3.client('cloudwatch')

# Environment variables
SOURCE_BUCKET = os.environ['SOURCE_BUCKET_NAME']
METADATA_TABLE = os.environ['METADATA_TABLE_NAME']
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


def lambda_handler(event, context):
    """
    Main Lambda handler for crawling brochures

    Event format:
    {
        "stores": [
            {
                "store_id": "lidl_bg",
                "store_name": "Lidl Bulgaria",
                "brochure_url": "https://...",
                "keywords": ["baby", "бебе", ...]
            }
        ]
    }
    """
    logger.info(f"CrawlerLambda invoked with event: {json.dumps(event, ensure_ascii=False)}")

    try:
        stores = event.get('stores', [])

        if not stores:
            logger.error("No stores provided in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No stores provided'})
            }

        results = []
        for store in stores:
            result = process_store(store)
            results.append(result)

        # Publish CloudWatch metrics
        success_count = sum(1 for r in results if r['status'] == 'success')
        failure_count = len(results) - success_count

        publish_metric('BrochuresDownloaded', success_count)
        publish_metric('BrochureDownloadFailures', failure_count)

        logger.info(f"Crawler completed: {success_count} success, {failure_count} failures")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Crawler completed',
                'results': results
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_store(store: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single store's brochure"""
    store_id = store.get('store_id')
    store_name = store.get('store_name')
    brochure_url = store.get('brochure_url')

    logger.info(f"Processing store: {store_id} - {store_name}")

    try:
        # Initialize scraper
        scraper = BrochureScraper()

        # Try to download brochure (with web scraping if needed)
        file_bytes, content_type, actual_url = scraper.download_brochure(brochure_url, store_id)

        # Calculate SHA-256 hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        logger.info(f"Downloaded brochure, hash: {file_hash}")

        # Check for duplicate
        if is_duplicate(file_hash):
            logger.info(f"Duplicate brochure detected: {file_hash}")
            publish_metric('DuplicateBrochures', 1, {'StoreId': store_id})
            return {
                'store_id': store_id,
                'status': 'duplicate',
                'file_hash': file_hash
            }

        # Generate brochure ID and S3 key
        brochure_id = f"{store_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Determine file extension from content type
        extension = get_file_extension(content_type)
        filename = f"brochure_{datetime.utcnow().strftime('%Y%m%d')}.{extension}"

        # S3 key format: {store_id}/{YYYY}/{MM}/{DD}/{filename}
        now = datetime.utcnow()
        s3_key = f"{store_id}/{now.year}/{now.month:02d}/{now.day:02d}/{filename}"

        # Upload to S3
        s3_client.put_object(
            Bucket=SOURCE_BUCKET,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
            Metadata={
                'store_id': store_id,
                'store_name': store_name,
                'source_url': brochure_url,
                'actual_url': actual_url,
                'file_hash': file_hash
            }
        )
        logger.info(f"Uploaded to S3: s3://{SOURCE_BUCKET}/{s3_key}")

        # Store metadata in DynamoDB
        create_metadata_record(
            brochure_id=brochure_id,
            store_id=store_id,
            store_name=store_name,
            filename=filename,
            s3_bucket=SOURCE_BUCKET,
            s3_key=s3_key,
            file_hash=file_hash,
            file_size=len(file_bytes),
            source_url=brochure_url,
            actual_download_url=actual_url,
            scraped=(brochure_url != actual_url)
        )

        publish_metric('BrochuresScraped', 1 if brochure_url != actual_url else 0, {'StoreId': store_id})

        return {
            'store_id': store_id,
            'status': 'success',
            'brochure_id': brochure_id,
            's3_key': s3_key,
            'file_hash': file_hash,
            'scraped': (brochure_url != actual_url)
        }

    except ScrapingError as e:
        logger.error(f"Scraping error for {store_id}: {str(e)}")
        return {
            'store_id': store_id,
            'status': 'error',
            'error': f"Scraping failed: {str(e)}"
        }
    except requests.RequestException as e:
        logger.error(f"Network error for {store_id}: {str(e)}")
        return {
            'store_id': store_id,
            'status': 'error',
            'error': f"Network error: {str(e)}"
        }
    except ClientError as e:
        logger.error(f"AWS error for {store_id}: {str(e)}")
        return {
            'store_id': store_id,
            'status': 'error',
            'error': f"AWS error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error for {store_id}: {str(e)}", exc_info=True)
        return {
            'store_id': store_id,
            'status': 'error',
            'error': str(e)
        }


def is_duplicate(file_hash: str) -> bool:
    """Check if brochure with this hash already exists"""
    try:
        response = dynamodb_client.query(
            TableName=METADATA_TABLE,
            IndexName='hash-index',
            KeyConditionExpression='file_hash = :hash',
            ExpressionAttributeValues={
                ':hash': {'S': file_hash}
            },
            Limit=1
        )
        return len(response.get('Items', [])) > 0
    except ClientError as e:
        logger.error(f"Error checking duplicate: {str(e)}")
        return False


def create_metadata_record(
    brochure_id: str,
    store_id: str,
    store_name: str,
    filename: str,
    s3_bucket: str,
    s3_key: str,
    file_hash: str,
    file_size: int,
    source_url: str,
    actual_download_url: str,
    scraped: bool
):
    """Create metadata record in DynamoDB"""
    timestamp = datetime.utcnow().isoformat() + 'Z'

    item = {
        'brochure_id': {'S': brochure_id},
        'store_id': {'S': store_id},
        'store_name': {'S': store_name},
        'filename': {'S': filename},
        's3_bucket': {'S': s3_bucket},
        's3_key': {'S': s3_key},
        'file_hash': {'S': file_hash},
        'file_size': {'N': str(file_size)},
        'source_url': {'S': source_url},
        'status': {'S': 'UPLOADED'},
        'upload_time': {'S': timestamp},
        'created_at': {'S': timestamp},
        'updated_at': {'S': timestamp}
    }

    # Add actual download URL if different from source (indicates scraping was used)
    if actual_download_url and actual_download_url != source_url:
        item['actual_download_url'] = {'S': actual_download_url}
        item['scraped'] = {'BOOL': scraped}

    try:
        dynamodb_client.put_item(
            TableName=METADATA_TABLE,
            Item=item
        )
        logger.info(f"Created metadata record: {brochure_id}")
    except ClientError as e:
        logger.error(f"Error creating metadata: {str(e)}")
        raise


def get_file_extension(content_type: str) -> str:
    """Determine file extension from content type"""
    content_type_map = {
        'application/pdf': 'pdf',
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/webp': 'webp'
    }
    return content_type_map.get(content_type, 'pdf')


def publish_metric(metric_name: str, value: float, dimensions: Dict[str, str] = None):
    """Publish custom CloudWatch metric"""
    try:
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        }

        if dimensions:
            metric_data['Dimensions'] = [
                {'Name': k, 'Value': v} for k, v in dimensions.items()
            ]

        cloudwatch_client.put_metric_data(
            Namespace='BrochureScanner',
            MetricData=[metric_data]
        )
    except Exception as e:
        logger.warning(f"Failed to publish metric {metric_name}: {str(e)}")
