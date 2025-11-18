"""
File inspection utilities for brochure processing.

Determines file type, size, and page count to decide between
synchronous and asynchronous Textract processing.
"""

import io
from typing import Dict, Tuple
from PyPDF2 import PdfReader

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.exceptions import UnsupportedFileFormatError, InvalidFileError
from common.logger import get_logger

logger = get_logger(__name__)


# Supported file formats with magic numbers
FILE_SIGNATURES = {
    b'%PDF': 'pdf',
    b'\x89PNG': 'png',
    b'\xff\xd8\xff': 'jpeg',
    b'II*\x00': 'tiff',  # Little-endian TIFF
    b'MM\x00*': 'tiff',  # Big-endian TIFF
}


class FileInspector:
    """
    Inspects brochure files to determine processing strategy.
    """

    def __init__(self, sync_page_threshold: int = 5, sync_size_threshold_mb: int = 5):
        """
        Initialize file inspector.

        Args:
            sync_page_threshold: Max pages for synchronous Textract processing
            sync_size_threshold_mb: Max file size in MB for synchronous processing
        """
        self.sync_page_threshold = sync_page_threshold
        self.sync_size_threshold_bytes = sync_size_threshold_mb * 1024 * 1024

    def inspect_file(self, file_bytes: bytes, filename: str) -> Dict:
        """
        Inspect file and determine processing strategy.

        Args:
            file_bytes: File content as bytes
            filename: Original filename

        Returns:
            Dictionary with file metadata and processing recommendation:
            {
                'file_type': str,
                'file_size_bytes': int,
                'page_count': int,
                'processing_mode': 'SYNC' or 'ASYNC'
            }

        Raises:
            UnsupportedFileFormatError: If file format is not supported
            InvalidFileError: If file is corrupted or cannot be read
        """
        file_size = len(file_bytes)
        file_type = self._detect_file_type(file_bytes, filename)

        logger.info(
            "Inspecting file",
            filename=filename,
            file_type=file_type,
            file_size_bytes=file_size
        )

        # Determine page count
        page_count = self._get_page_count(file_bytes, file_type)

        # Determine processing mode
        processing_mode = self._determine_processing_mode(file_size, page_count)

        result = {
            'file_type': file_type,
            'file_size_bytes': file_size,
            'page_count': page_count,
            'processing_mode': processing_mode
        }

        logger.info(
            "File inspection complete",
            filename=filename,
            **result
        )

        return result

    def _detect_file_type(self, file_bytes: bytes, filename: str) -> str:
        """
        Detect file type from magic numbers and extension.

        Args:
            file_bytes: File content
            filename: Original filename

        Returns:
            File type string ('pdf', 'png', 'jpeg', 'tiff')

        Raises:
            UnsupportedFileFormatError: If file type cannot be determined
        """
        # Check magic numbers
        for signature, file_type in FILE_SIGNATURES.items():
            if file_bytes.startswith(signature):
                return file_type

        # Fallback to extension
        extension = filename.lower().split('.')[-1]
        if extension in ['pdf', 'png', 'jpg', 'jpeg', 'tif', 'tiff']:
            file_type = 'jpeg' if extension in ['jpg', 'jpeg'] else extension
            file_type = 'tiff' if extension in ['tif', 'tiff'] else file_type
            logger.warning(
                "File type detected from extension only (magic number mismatch)",
                filename=filename,
                extension=extension
            )
            return file_type

        raise UnsupportedFileFormatError(
            f"Unsupported file format: {filename}",
            filename=filename,
            extension=extension if extension else None
        )

    def _get_page_count(self, file_bytes: bytes, file_type: str) -> int:
        """
        Get page count for the file.

        Args:
            file_bytes: File content
            file_type: Detected file type

        Returns:
            Number of pages (1 for images)

        Raises:
            InvalidFileError: If PDF cannot be read
        """
        if file_type == 'pdf':
            try:
                pdf_file = io.BytesIO(file_bytes)
                pdf_reader = PdfReader(pdf_file)
                page_count = len(pdf_reader.pages)

                if page_count == 0:
                    raise InvalidFileError(
                        "PDF has no pages",
                        file_type=file_type
                    )

                return page_count

            except Exception as e:
                if isinstance(e, InvalidFileError):
                    raise
                raise InvalidFileError(
                    f"Failed to read PDF: {str(e)}",
                    file_type=file_type,
                    error=str(e)
                )
        else:
            # Images are single-page
            return 1

    def _determine_processing_mode(self, file_size: int, page_count: int) -> str:
        """
        Determine whether to use synchronous or asynchronous Textract processing.

        Synchronous API is faster but limited to:
        - Single-page images (PNG, JPEG, TIFF)
        - PDFs with < sync_page_threshold pages
        - Files < sync_size_threshold_bytes

        Args:
            file_size: File size in bytes
            page_count: Number of pages

        Returns:
            'SYNC' or 'ASYNC'
        """
        if file_size >= self.sync_size_threshold_bytes:
            logger.info(
                "Using ASYNC mode due to file size",
                file_size_bytes=file_size,
                threshold_bytes=self.sync_size_threshold_bytes
            )
            return 'ASYNC'

        if page_count >= self.sync_page_threshold:
            logger.info(
                "Using ASYNC mode due to page count",
                page_count=page_count,
                threshold=self.sync_page_threshold
            )
            return 'ASYNC'

        logger.info(
            "Using SYNC mode",
            file_size_bytes=file_size,
            page_count=page_count
        )
        return 'SYNC'
