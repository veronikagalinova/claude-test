"""
Textract result retrieval with pagination support.

Handles retrieving asynchronous Textract job results using
GetDocumentTextDetection API with automatic pagination.
"""

from typing import Dict, List
from botocore.exceptions import ClientError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.aws_clients import get_textract_client
from common.exceptions import TextractProcessingError
from common.logger import get_logger

logger = get_logger(__name__)


class TextractResultRetriever:
    """
    Retrieves Textract async job results with pagination.
    """

    def __init__(self):
        """Initialize result retriever."""
        self.textract_client = get_textract_client()

    def retrieve_results(self, job_id: str, brochure_id: str) -> Dict:
        """
        Retrieve complete Textract job results with pagination.

        Args:
            job_id: Textract job ID
            brochure_id: Brochure identifier for logging

        Returns:
            Aggregated Textract response with all blocks

        Raises:
            TextractProcessingError: If retrieval fails
        """
        logger.info(
            "Retrieving Textract results",
            job_id=job_id,
            brochure_id=brochure_id
        )

        all_blocks = []
        document_metadata = None
        next_token = None
        page_count = 0

        try:
            while True:
                # Build request parameters
                params = {'JobId': job_id}
                if next_token:
                    params['NextToken'] = next_token

                # Get results page
                response = self.textract_client.get_document_text_detection(**params)

                # Check job status
                job_status = response.get('JobStatus')
                if job_status == 'FAILED':
                    error_message = response.get('StatusMessage', 'Unknown error')
                    logger.error(
                        "Textract job failed",
                        job_id=job_id,
                        brochure_id=brochure_id,
                        error_message=error_message
                    )
                    raise TextractProcessingError(
                        f"Textract job failed: {error_message}",
                        job_id=job_id,
                        brochure_id=brochure_id
                    )

                if job_status != 'SUCCEEDED':
                    logger.warning(
                        "Textract job not yet complete",
                        job_id=job_id,
                        brochure_id=brochure_id,
                        job_status=job_status
                    )
                    raise TextractProcessingError(
                        f"Textract job status: {job_status}",
                        job_id=job_id,
                        brochure_id=brochure_id,
                        job_status=job_status
                    )

                # Collect blocks
                blocks = response.get('Blocks', [])
                all_blocks.extend(blocks)
                page_count += 1

                # Get document metadata from first response
                if document_metadata is None:
                    document_metadata = response.get('DocumentMetadata', {})

                logger.info(
                    "Retrieved Textract results page",
                    job_id=job_id,
                    brochure_id=brochure_id,
                    page=page_count,
                    blocks_in_page=len(blocks),
                    total_blocks=len(all_blocks)
                )

                # Check for next page
                next_token = response.get('NextToken')
                if not next_token:
                    break

            # Build aggregated response
            aggregated_response = {
                'JobStatus': 'SUCCEEDED',
                'DocumentMetadata': document_metadata,
                'Blocks': all_blocks
            }

            logger.info(
                "Textract results retrieval complete",
                job_id=job_id,
                brochure_id=brochure_id,
                total_blocks=len(all_blocks),
                pages_retrieved=page_count,
                document_pages=document_metadata.get('Pages', 0)
            )

            return aggregated_response

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')

            if error_code == 'InvalidJobIdException':
                logger.error(
                    "Invalid Textract job ID",
                    job_id=job_id,
                    brochure_id=brochure_id
                )
                raise TextractProcessingError(
                    "Invalid Textract job ID",
                    job_id=job_id,
                    brochure_id=brochure_id,
                    error_code=error_code
                )

            if error_code == 'ProvisionedThroughputExceededException':
                logger.error(
                    "Textract API throttled during result retrieval",
                    job_id=job_id,
                    brochure_id=brochure_id
                )
                raise TextractProcessingError(
                    "Textract API throttled",
                    job_id=job_id,
                    brochure_id=brochure_id,
                    error_code=error_code
                )

            logger.error(
                "Error retrieving Textract results",
                job_id=job_id,
                brochure_id=brochure_id,
                error_code=error_code,
                error_message=str(e)
            )
            raise TextractProcessingError(
                f"Failed to retrieve Textract results: {str(e)}",
                job_id=job_id,
                brochure_id=brochure_id,
                error_code=error_code
            )

        except TextractProcessingError:
            raise

        except Exception as e:
            logger.error(
                "Unexpected error retrieving Textract results",
                job_id=job_id,
                brochure_id=brochure_id,
                error=str(e)
            )
            raise TextractProcessingError(
                f"Unexpected error: {str(e)}",
                job_id=job_id,
                brochure_id=brochure_id
            )
