"""
HTTP downloader with retry logic and timeout handling.

Downloads brochure files from store URLs with exponential backoff for transient failures.
"""

import time
import requests
from typing import Tuple, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger
from common.exceptions import BrochureScannerException

logger = get_logger(__name__)


class DownloadError(BrochureScannerException):
    """Raised when download fails after retries."""
    pass


class BrochureDownloader:
    """
    Downloads brochure files from URLs with retry logic.
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 30,
        max_file_size_mb: int = 100
    ):
        """
        Initialize downloader.

        Args:
            max_retries: Maximum number of retry attempts
            timeout_seconds: Request timeout in seconds
            max_file_size_mb: Maximum allowed file size in MB
        """
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=2,  # 2s, 4s, 8s
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set user agent to identify the crawler
        self.session.headers.update({
            'User-Agent': 'BrochureScanner/1.0 (Automated Brochure Crawler)'
        })

    def download_file(self, url: str, store_id: str) -> Tuple[bytes, str]:
        """
        Download file from URL with retry logic.

        Args:
            url: URL to download from
            store_id: Store identifier for logging

        Returns:
            Tuple of (file_bytes, content_type)

        Raises:
            DownloadError: If download fails after retries
        """
        logger.info(
            "Starting download",
            url=url,
            store_id=store_id,
            max_retries=self.max_retries,
            timeout=self.timeout_seconds
        )

        try:
            # Perform HEAD request first to check file size
            head_response = self.session.head(
                url,
                timeout=self.timeout_seconds,
                allow_redirects=True
            )

            content_length = head_response.headers.get('Content-Length')
            if content_length:
                file_size = int(content_length)
                if file_size > self.max_file_size_bytes:
                    raise DownloadError(
                        f"File size ({file_size} bytes) exceeds maximum ({self.max_file_size_bytes} bytes)",
                        url=url,
                        store_id=store_id,
                        file_size=file_size
                    )

                logger.info(
                    "File size check passed",
                    url=url,
                    store_id=store_id,
                    file_size_bytes=file_size
                )

            # Download the file with streaming
            response = self.session.get(
                url,
                timeout=self.timeout_seconds,
                stream=True,
                allow_redirects=True
            )

            # Check HTTP status
            response.raise_for_status()

            # Download content with size limit
            file_bytes = b''
            downloaded_size = 0

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded_size += len(chunk)
                    if downloaded_size > self.max_file_size_bytes:
                        raise DownloadError(
                            f"Downloaded size exceeds maximum ({self.max_file_size_bytes} bytes)",
                            url=url,
                            store_id=store_id,
                            downloaded_size=downloaded_size
                        )
                    file_bytes += chunk

            content_type = response.headers.get('Content-Type', 'application/octet-stream')

            logger.info(
                "Download successful",
                url=url,
                store_id=store_id,
                file_size_bytes=len(file_bytes),
                content_type=content_type
            )

            return file_bytes, content_type

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'unknown'
            logger.error(
                "HTTP error during download",
                url=url,
                store_id=store_id,
                status_code=status_code,
                error=str(e)
            )

            raise DownloadError(
                f"HTTP {status_code} error: {str(e)}",
                url=url,
                store_id=store_id,
                status_code=status_code
            )

        except requests.exceptions.Timeout as e:
            logger.error(
                "Download timeout",
                url=url,
                store_id=store_id,
                timeout=self.timeout_seconds,
                error=str(e)
            )

            raise DownloadError(
                f"Download timeout after {self.timeout_seconds}s: {str(e)}",
                url=url,
                store_id=store_id
            )

        except requests.exceptions.ConnectionError as e:
            logger.error(
                "Connection error during download",
                url=url,
                store_id=store_id,
                error=str(e)
            )

            raise DownloadError(
                f"Connection error: {str(e)}",
                url=url,
                store_id=store_id
            )

        except requests.exceptions.RequestException as e:
            logger.error(
                "Request exception during download",
                url=url,
                store_id=store_id,
                error=str(e)
            )

            raise DownloadError(
                f"Request failed: {str(e)}",
                url=url,
                store_id=store_id
            )

        except Exception as e:
            logger.error(
                "Unexpected error during download",
                url=url,
                store_id=store_id,
                error=str(e)
            )

            raise DownloadError(
                f"Unexpected error: {str(e)}",
                url=url,
                store_id=store_id
            )

    def validate_url(self, url: str) -> bool:
        """
        Validate URL format and accessibility.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and accessible
        """
        if not url:
            return False

        # Check URL scheme
        if not url.startswith(('http://', 'https://')):
            logger.warning("Invalid URL scheme", url=url)
            return False

        # Basic URL format validation
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if not parsed.netloc:
                logger.warning("URL missing netloc", url=url)
                return False
        except Exception as e:
            logger.warning("URL parsing failed", url=url, error=str(e))
            return False

        return True

    def get_filename_from_url(self, url: str) -> Optional[str]:
        """
        Extract filename from URL.

        Args:
            url: URL to extract filename from

        Returns:
            Filename or None if not extractable
        """
        try:
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            path = parsed.path

            # Get last component of path
            filename = path.split('/')[-1]

            # URL decode
            filename = unquote(filename)

            # If empty or no extension, return None
            if not filename or '.' not in filename:
                return None

            return filename

        except Exception as e:
            logger.warning("Failed to extract filename from URL", url=url, error=str(e))
            return None
