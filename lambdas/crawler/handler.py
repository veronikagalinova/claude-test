"""
CrawlerLambda - Downloads brochures from store URLs and uploads to S3.

Triggered by EventBridge scheduled events.
Downloads brochures from configured URLs, checks for duplicates, and uploads to S3.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger
from common.metrics import get_metrics_publisher
from common.aws_clients import get_s3_client, get_dynamodb_client
from common.exceptions import UnsupportedFileFormatError

from downloader import BrochureDownloader, DownloadError
from hash_utils import compute_file_hash
from web_scraper import BrochureScraper, ScrapingError


# Environment variables
SOURCE_BUCKET_NAME = os.environ.get('SOURCE_BUCKET_NAME')
METADATA_TABLE_NAME = os.environ.get('METADATA_TABLE_NAME')
CONFIG_BUCKET_NAME = os.environ.get('CONFIG_BUCKET_NAME') or os.environ.get('SOURCE_BUCKET_NAME')
STORE_CONFIG_S3_KEY = os.environ.get('STORE_CONFIG_S3_KEY', 'config/keyword-config.json')

logger = get_logger('CrawlerLambda')
metrics = get_metrics_publisher()

# File type validation
SUPPORTED_FILE_SIGNATURES = {
    b'%PDF': 'pdf',
    b'\x89PNG': 'png',
    b'\xff\xd8\xff': 'jpeg',
    b'II*\x00': 'tiff',
    b'MM\x00*': 'tiff',
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for scheduled brochure crawling.

    Args:
        event: EventBridge scheduled event with store configuration
        context: Lambda context

    Returns:
        Response dictionary with crawl results
    """
    # Set correlation ID
    request_id = context.request_id if context else str(uuid.uuid4())
    logger.set_correlation_id(request_id)

    logger.info("CrawlerLambda invoked", event_source=event.get('source'))

    success_count = 0
    error_count = 0
    duplicate_count = 0
    results = []

    try:
        # Load store configuration
        stores = load_store_configuration(event)

        logger.info(
            "Starting crawl for stores",
            store_count=len(stores)
        )

        # Process each store
        for store in stores:
            store_id = store.get('store_id')

            try:
                result = process_store(store)
                results.append(result)

                if result['status'] == 'success':
                    success_count += 1
                    metrics.increment_counter('BrochuresDownloaded', {'StoreId': store_id})
                elif result['status'] == 'duplicate':
                    duplicate_count += 1
                    metrics.increment_counter('DuplicatesSkipped', {'StoreId': store_id})
                else:
                    error_count += 1
                    metrics.increment_counter('BrochuresFailed', {'StoreId': store_id})

            except Exception as e:
                error_count += 1
                logger.log_exception(
                    e,
                    "Failed to process store",
                    store_id=store_id
                )
                results.append({
                    'store_id': store_id,
                    'status': 'error',
                    'error': str(e)
                })
                metrics.increment_counter('BrochuresFailed', {'StoreId': store_id})

        # Publish summary metrics
        metrics.flush()

        logger.info(
            "Crawl completed",
            total_stores=len(stores),
            success=success_count,
            duplicates=duplicate_count,
            errors=error_count
        )

        return {
            'statusCode': 200 if error_count == 0 else 207,
            'body': json.dumps({
                'total_stores': len(stores),
                'success': success_count,
                'duplicates': duplicate_count,
                'errors': error_count,
                'results': results
            })
        }

    except Exception as e:
        logger.log_exception(e, "Fatal error in lambda_handler")
        metrics.put_metric('CrawlErrors', 1)
        metrics.flush()

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def load_store_configuration(event: Dict[str, Any]) -> List[Dict]:
    """
    Load store configuration from event or S3.

    Args:
        event: EventBridge event

    Returns:
        List of store configurations
    """
    # First, check if stores are provided directly in event
    detail = event.get('detail', {})
    if 'stores' in detail:
        stores = detail['stores']
        logger.info(
            "Loaded stores from event detail",
            store_count=len(stores)
        )
        return stores

    # Otherwise, load from S3 configuration file
    logger.info(
        "Loading store configuration from S3",
        bucket=CONFIG_BUCKET_NAME,
        key=STORE_CONFIG_S3_KEY
    )

    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(
            Bucket=CONFIG_BUCKET_NAME,
            Key=STORE_CONFIG_S3_KEY
        )

        config_json = response['Body'].read().decode('utf-8')
        config = json.loads(config_json)

        stores = config.get('stores', [])

        logger.info(
            "Store configuration loaded from S3",
            store_count=len(stores)
        )

        return stores

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        logger.error(
            "Failed to load configuration from S3",
            bucket=CONFIG_BUCKET_NAME,
            key=STORE_CONFIG_S3_KEY,
            error_code=error_code
        )
        raise

    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in configuration file",
            bucket=CONFIG_BUCKET_NAME,
            key=STORE_CONFIG_S3_KEY,
            error=str(e)
        )
        raise


def process_store(store: Dict) -> Dict:
    """
    Process a single store - download, check duplicates, upload.

    Args:
        store: Store configuration dictionary

    Returns:
        Result dictionary with status and details
    """
    store_id = store.get('store_id')
    store_name = store.get('store_name', store_id)
    brochure_url = store.get('brochure_url')

    logger.info(
        "Processing store",
        store_id=store_id,
        store_name=store_name,
        url=brochure_url
    )

    # Validate URL
    temp_downloader = BrochureDownloader()

    if not temp_downloader.validate_url(brochure_url):
        logger.error(
            "Invalid brochure URL",
            store_id=store_id,
            url=brochure_url
        )
        return {
            'store_id': store_id,
            'status': 'error',
            'error': 'Invalid URL'
        }

    try:
        # Initialize downloader and scraper
        downloader = BrochureDownloader()
        scraper = BrochureScraper()

        file_bytes = None
        content_type = None
        actual_download_url = brochure_url

        # Try direct download first
        try:
            file_bytes, content_type = downloader.download_file(brochure_url, store_id)

            # Check if we got HTML instead of a PDF/image
            if content_type and 'text/html' in content_type.lower():
                logger.info(
                    "Received HTML content, attempting web scraping",
                    store_id=store_id,
                    url=brochure_url
                )
                file_bytes = None  # Reset to trigger scraping

        except DownloadError as e:
            logger.warning(
                "Direct download failed, attempting web scraping",
                store_id=store_id,
                error=str(e)
            )
            file_bytes = None  # Will trigger scraping

        # If direct download didn't work, try web scraping
        if file_bytes is None:
            try:
                # Extract actual brochure URL from web page
                extracted_url, url_type = scraper.extract_brochure_url(brochure_url, store_id)

                logger.info(
                    "Extracted brochure URL from web page",
                    original_url=brochure_url,
                    extracted_url=extracted_url,
                    url_type=url_type,
                    store_id=store_id
                )

                # Download the extracted URL
                file_bytes, content_type = downloader.download_file(extracted_url, store_id)
                actual_download_url = extracted_url

                metrics.increment_counter('BrochuresScraped', {'StoreId': store_id})

            except ScrapingError as scrape_err:
                logger.error(
                    "Web scraping failed",
                    store_id=store_id,
                    error=str(scrape_err)
                )
                return {
                    'store_id': store_id,
                    'status': 'error',
                    'error': f"Scraping failed: {str(scrape_err)}"
                }

        # Validate file type
        file_type = detect_file_type(file_bytes)

        # Compute hash for deduplication
        file_hash = compute_file_hash(file_bytes)

        logger.info(
            "File downloaded and hashed",
            store_id=store_id,
            file_size=len(file_bytes),
            file_type=file_type,
            file_hash=file_hash
        )

        # Check for duplicate
        if is_duplicate(file_hash, store_id):
            logger.info(
                "Duplicate brochure detected, skipping",
                store_id=store_id,
                file_hash=file_hash
            )
            return {
                'store_id': store_id,
                'status': 'duplicate',
                'file_hash': file_hash
            }

        # Generate brochure ID and S3 key
        brochure_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Extract filename from actual download URL or generate one
        filename = downloader.get_filename_from_url(actual_download_url)
        if not filename:
            filename = f"brochure-{now.strftime('%Y%m%d')}.{file_type}"

        # Construct S3 key: {store_id}/{year}/{month}/{day}/{filename}
        s3_key = f"{store_id}/{now.year}/{now.month:02d}/{now.day:02d}/{filename}"

        # Upload to S3
        upload_to_s3(
            file_bytes=file_bytes,
            bucket=SOURCE_BUCKET_NAME,
            key=s3_key,
            content_type=content_type,
            brochure_id=brochure_id
        )

        # Create metadata record
        create_metadata_record(
            brochure_id=brochure_id,
            store_id=store_id,
            store_name=store_name,
            filename=filename,
            s3_bucket=SOURCE_BUCKET_NAME,
            s3_key=s3_key,
            file_hash=file_hash,
            file_size=len(file_bytes),
            source_url=brochure_url,
            actual_download_url=actual_download_url if actual_download_url != brochure_url else None
        )

        logger.info(
            "Brochure processed successfully",
            store_id=store_id,
            brochure_id=brochure_id,
            s3_key=s3_key
        )

        return {
            'store_id': store_id,
            'status': 'success',
            'brochure_id': brochure_id,
            's3_key': s3_key,
            'file_hash': file_hash
        }

    except DownloadError as e:
        logger.error(
            "Failed to download brochure",
            store_id=store_id,
            error=str(e)
        )
        return {
            'store_id': store_id,
            'status': 'error',
            'error': f"Download failed: {str(e)}"
        }

    except UnsupportedFileFormatError as e:
        logger.error(
            "Unsupported file format",
            store_id=store_id,
            error=str(e)
        )
        return {
            'store_id': store_id,
            'status': 'error',
            'error': f"Unsupported format: {str(e)}"
        }

    except Exception as e:
        logger.log_exception(
            e,
            "Unexpected error processing store",
            store_id=store_id
        )
        return {
            'store_id': store_id,
            'status': 'error',
            'error': str(e)
        }


def detect_file_type(file_bytes: bytes) -> str:
    """
    Detect file type from magic numbers.

    Args:
        file_bytes: File content

    Returns:
        File type string ('pdf', 'png', 'jpeg', 'tiff')

    Raises:
        UnsupportedFileFormatError: If file type is not supported
    """
    for signature, file_type in SUPPORTED_FILE_SIGNATURES.items():
        if file_bytes.startswith(signature):
            return file_type

    raise UnsupportedFileFormatError(
        "Unsupported file format",
        file_signature=file_bytes[:10].hex() if len(file_bytes) >= 10 else None
    )


def is_duplicate(file_hash: str, store_id: str) -> bool:
    """
    Check if file hash already exists in DynamoDB.

    Queries the hash-index GSI to find duplicates.

    Args:
        file_hash: SHA-256 hash of file
        store_id: Store identifier for logging

    Returns:
        True if duplicate exists and is recent (< 30 days)
    """
    dynamodb_client = get_dynamodb_client()

    try:
        # Query hash-index GSI
        response = dynamodb_client.query(
            TableName=METADATA_TABLE_NAME,
            IndexName='hash-index',
            KeyConditionExpression='file_hash = :hash',
            ExpressionAttributeValues={
                ':hash': {'S': file_hash}
            },
            Limit=1
        )

        items = response.get('Items', [])

        if not items:
            logger.debug("No duplicate found", file_hash=file_hash, store_id=store_id)
            return False

        # Check if duplicate is recent
        existing_item = items[0]
        upload_time_str = existing_item.get('upload_time', {}).get('S', '')

        if upload_time_str:
            upload_time = datetime.fromisoformat(upload_time_str.replace('Z', '+00:00'))
            age_days = (datetime.now(upload_time.tzinfo) - upload_time).days

            # Only consider as duplicate if < 30 days old
            if age_days < 30:
                logger.info(
                    "Recent duplicate found",
                    file_hash=file_hash,
                    store_id=store_id,
                    existing_brochure_id=existing_item.get('brochure_id', {}).get('S'),
                    age_days=age_days
                )
                return True
            else:
                logger.info(
                    "Old duplicate found, allowing re-upload",
                    file_hash=file_hash,
                    store_id=store_id,
                    age_days=age_days
                )
                return False

        return False

    except ClientError as e:
        logger.error(
            "Failed to query for duplicates",
            file_hash=file_hash,
            store_id=store_id,
            error=str(e)
        )
        # On error, assume not duplicate to avoid blocking uploads
        return False


def upload_to_s3(
    file_bytes: bytes,
    bucket: str,
    key: str,
    content_type: str,
    brochure_id: str
):
    """
    Upload brochure to S3.

    Args:
        file_bytes: File content
        bucket: S3 bucket name
        key: S3 key
        content_type: Content type
        brochure_id: Brochure identifier
    """
    logger.info(
        "Uploading to S3",
        bucket=bucket,
        key=key,
        size=len(file_bytes)
    )

    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            Metadata={
                'brochure_id': brochure_id,
                'source': 'crawler'
            }
        )

        logger.info(
            "Upload successful",
            bucket=bucket,
            key=key,
            brochure_id=brochure_id
        )

    except ClientError as e:
        logger.error(
            "Failed to upload to S3",
            bucket=bucket,
            key=key,
            brochure_id=brochure_id,
            error=str(e)
        )
        raise


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
    actual_download_url: Optional[str] = None
):
    """
    Create metadata record in DynamoDB.

    Args:
        brochure_id: Unique brochure identifier
        store_id: Store identifier
        store_name: Store name
        filename: Original filename
        s3_bucket: S3 bucket name
        s3_key: S3 key
        file_hash: SHA-256 hash
        file_size: File size in bytes
        source_url: Source URL
    """
    dynamodb_client = get_dynamodb_client()
    timestamp = datetime.utcnow().isoformat() + 'Z'

    item = {
        'brochure_id': {'S': brochure_id},
        'store_id': {'S': store_id},
        'store_name': {'S': store_name},
        'brochure_filename': {'S': filename},
        's3_bucket': {'S': s3_bucket},
        's3_key': {'S': s3_key},
        'file_hash': {'S': file_hash},
        'file_size_bytes': {'N': str(file_size)},
        'upload_time': {'S': timestamp},
        'source_url': {'S': source_url},
        'status': {'S': 'UPLOADED'},
        'created_at': {'S': timestamp},
        'updated_at': {'S': timestamp}
    }

    # Add actual download URL if different from source (indicates scraping was used)
    if actual_download_url:
        item['actual_download_url'] = {'S': actual_download_url}
        item['scraped'] = {'BOOL': True}

    try:
        dynamodb_client.put_item(
            TableName=METADATA_TABLE_NAME,
            Item=item
        )

        logger.info(
            "Metadata record created",
            brochure_id=brochure_id,
            store_id=store_id
        )

    except ClientError as e:
        logger.error(
            "Failed to create metadata record",
            brochure_id=brochure_id,
            store_id=store_id,
            error=str(e)
        )
        raise
