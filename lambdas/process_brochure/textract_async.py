"""
Asynchronous Textract processing for large brochures.

Handles asynchronous OCR processing for multi-page or large documents
using Textract's StartDocumentTextDetection API.
"""

from typing import Dict
from botocore.exceptions import ClientError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.aws_clients import get_textract_client
from common.exceptions import TextractProcessingError, TextractThrottlingError
from common.logger import get_logger

logger = get_logger(__name__)


class TextractAsyncProcessor:
    """
    Handles asynchronous Textract OCR processing.
    """

    def __init__(self, sns_topic_arn: str, textract_role_arn: str):
        """
        Initialize Textract async processor.

        Args:
            sns_topic_arn: SNS topic ARN for job completion notifications
            textract_role_arn: IAM role ARN for Textract to publish to SNS
        """
        self.textract_client = get_textract_client()
        self.sns_topic_arn = sns_topic_arn
        self.textract_role_arn = textract_role_arn

    def start_document_analysis(
        self,
        source_bucket: str,
        source_key: str,
        brochure_id: str
    ) -> str:
        """
        Start asynchronous Textract document text detection job.

        Args:
            source_bucket: S3 bucket containing the document
            source_key: S3 key for the document
            brochure_id: Unique brochure identifier

        Returns:
            Textract job ID

        Raises:
            TextractThrottlingError: If Textract API is throttled
            TextractProcessingError: If job submission fails
        """
        logger.info(
            "Starting asynchronous Textract job",
            brochure_id=brochure_id,
            source_bucket=source_bucket,
            source_key=source_key
        )

        try:
            response = self.textract_client.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': source_bucket,
                        'Name': source_key
                    }
                },
                NotificationChannel={
                    'SNSTopicArn': self.sns_topic_arn,
                    'RoleArn': self.textract_role_arn
                },
                ClientRequestToken=brochure_id  # Idempotency token
            )

            job_id = response.get('JobId')

            if not job_id:
                raise TextractProcessingError(
                    "Textract response missing JobId",
                    brochure_id=brochure_id
                )

            logger.info(
                "Textract async job started successfully",
                brochure_id=brochure_id,
                job_id=job_id
            )

            return job_id

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')

            # Handle idempotent duplicate request
            if error_code == 'IdempotentParameterMismatchException':
                logger.warning(
                    "Textract job already exists for this brochure",
                    brochure_id=brochure_id
                )
                # Extract job ID from error message if possible, otherwise re-raise
                raise TextractProcessingError(
                    "Duplicate Textract job request",
                    brochure_id=brochure_id,
                    error_code=error_code
                )

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

            if error_code == 'LimitExceededException':
                logger.error(
                    "Textract concurrent job limit exceeded",
                    brochure_id=brochure_id,
                    error_code=error_code
                )
                raise TextractThrottlingError(
                    "Textract concurrent job limit exceeded",
                    brochure_id=brochure_id,
                    error_code=error_code
                )

            logger.error(
                "Failed to start Textract job",
                brochure_id=brochure_id,
                error_code=error_code,
                error_message=str(e)
            )
            raise TextractProcessingError(
                f"Failed to start Textract job: {str(e)}",
                brochure_id=brochure_id,
                error_code=error_code
            )

        except Exception as e:
            logger.error(
                "Unexpected error starting Textract job",
                brochure_id=brochure_id,
                error=str(e)
            )
            raise TextractProcessingError(
                f"Unexpected error: {str(e)}",
                brochure_id=brochure_id
            )
