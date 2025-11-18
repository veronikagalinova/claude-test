"""
Synchronous Textract processing for small brochures.

Handles immediate OCR processing for single-page or small documents
using Textract's DetectDocumentText API.
"""

import json
from typing import Dict
from botocore.exceptions import ClientError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.aws_clients import get_textract_client, get_s3_client
from common.exceptions import TextractProcessingError, TextractThrottlingError
from common.logger import get_logger

logger = get_logger(__name__)


class TextractSyncProcessor:
    """
    Handles synchronous Textract OCR processing.
    """

    def __init__(self):
        """Initialize Textract sync processor."""
        self.textract_client = get_textract_client()
        self.s3_client = get_s3_client()

    def process_document(
        self,
        file_bytes: bytes,
        brochure_id: str
    ) -> Dict:
        """
        Process document synchronously using Textract DetectDocumentText.

        Args:
            file_bytes: Document content as bytes
            brochure_id: Unique brochure identifier

        Returns:
            Textract response dictionary with Blocks and DocumentMetadata

        Raises:
            TextractThrottlingError: If Textract API is throttled
            TextractProcessingError: If Textract processing fails
        """
        logger.info(
            "Starting synchronous Textract processing",
            brochure_id=brochure_id,
            file_size_bytes=len(file_bytes)
        )

        try:
            response = self.textract_client.detect_document_text(
                Document={'Bytes': file_bytes}
            )

            # Validate response
            if 'Blocks' not in response:
                raise TextractProcessingError(
                    "Textract response missing Blocks",
                    brochure_id=brochure_id
                )

            block_count = len(response['Blocks'])
            page_count = response.get('DocumentMetadata', {}).get('Pages', 0)

            logger.info(
                "Synchronous Textract processing complete",
                brochure_id=brochure_id,
                block_count=block_count,
                page_count=page_count
            )

            return response

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')

            if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException']:
                logger.error(
                    "Textract API throttled",
                    brochure_id=brochure_id,
                    error_code=error_code
                )
                raise TextractThrottlingError(
                    "Textract API throttled",
                    brochure_id=brochure_id,
                    error_code=error_code
                )

            logger.error(
                "Textract processing failed",
                brochure_id=brochure_id,
                error_code=error_code,
                error_message=str(e)
            )
            raise TextractProcessingError(
                f"Textract processing failed: {str(e)}",
                brochure_id=brochure_id,
                error_code=error_code
            )

        except Exception as e:
            logger.error(
                "Unexpected error during Textract processing",
                brochure_id=brochure_id,
                error=str(e)
            )
            raise TextractProcessingError(
                f"Unexpected error: {str(e)}",
                brochure_id=brochure_id
            )

    def store_result(
        self,
        textract_response: Dict,
        output_bucket: str,
        output_key: str,
        brochure_id: str
    ):
        """
        Store Textract result to S3 as JSON.

        Args:
            textract_response: Textract API response
            output_bucket: S3 bucket for results
            output_key: S3 key for result file
            brochure_id: Unique brochure identifier

        Raises:
            TextractProcessingError: If S3 upload fails
        """
        logger.info(
            "Storing Textract result to S3",
            brochure_id=brochure_id,
            output_bucket=output_bucket,
            output_key=output_key
        )

        try:
            # Convert response to JSON
            result_json = json.dumps(textract_response, indent=2)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=result_json.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'brochure_id': brochure_id,
                    'processing_mode': 'SYNC'
                }
            )

            logger.info(
                "Textract result stored successfully",
                brochure_id=brochure_id,
                output_s3_uri=f"s3://{output_bucket}/{output_key}"
            )

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            logger.error(
                "Failed to store Textract result to S3",
                brochure_id=brochure_id,
                error_code=error_code,
                error_message=str(e)
            )
            raise TextractProcessingError(
                f"Failed to store result: {str(e)}",
                brochure_id=brochure_id,
                error_code=error_code
            )
