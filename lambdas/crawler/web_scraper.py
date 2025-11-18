"""
Web scraping utilities for extracting brochure URLs from web pages.

Handles various brochure viewer patterns including:
- Direct PDF links
- PDFs embedded in JavaScript/data attributes
- Image-based brochure viewers
- JSON-embedded brochure data
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger
from common.exceptions import BrochureScannerException

logger = get_logger(__name__)


class ScrapingError(BrochureScannerException):
    """Raised when web scraping fails."""
    pass


class BrochureScraper:
    """
    Extracts brochure URLs from web pages using various strategies.
    """

    def __init__(self, timeout_seconds: int = 30):
        """
        Initialize scraper.

        Args:
            timeout_seconds: Request timeout in seconds
        """
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def extract_brochure_url(self, page_url: str, store_id: str) -> Tuple[str, str]:
        """
        Extract brochure URL from a web page.

        Tries multiple extraction strategies:
        1. Direct PDF link detection
        2. JavaScript-embedded URLs
        3. Data attributes
        4. JSON-LD structured data
        5. Common API patterns

        Args:
            page_url: URL of the web page containing the brochure
            store_id: Store identifier for logging

        Returns:
            Tuple of (brochure_url, content_type) where content_type is 'pdf' or 'html'

        Raises:
            ScrapingError: If brochure URL cannot be extracted
        """
        logger.info(
            "Extracting brochure URL from page",
            page_url=page_url,
            store_id=store_id
        )

        try:
            # Fetch the page
            response = self.session.get(
                page_url,
                timeout=self.timeout_seconds,
                allow_redirects=True
            )
            response.raise_for_status()

            # Check if the response itself is a PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/pdf' in content_type:
                logger.info(
                    "Page URL is already a direct PDF",
                    page_url=page_url,
                    store_id=store_id
                )
                return page_url, 'pdf'

            # Parse HTML
            html_content = response.text
            soup = BeautifulSoup(html_content, 'lxml')

            # Try different extraction strategies in order
            strategies = [
                self._extract_from_meta_tags,
                self._extract_from_links,
                self._extract_from_scripts,
                self._extract_from_iframes,
                self._extract_from_data_attributes,
                self._extract_from_json_ld,
                self._extract_from_common_patterns,
            ]

            for strategy in strategies:
                try:
                    result = strategy(soup, page_url, store_id)
                    if result:
                        url, url_type = result
                        logger.info(
                            "Successfully extracted brochure URL",
                            strategy=strategy.__name__,
                            extracted_url=url,
                            url_type=url_type,
                            store_id=store_id
                        )
                        return url, url_type
                except Exception as e:
                    logger.debug(
                        f"Strategy {strategy.__name__} failed",
                        error=str(e),
                        store_id=store_id
                    )
                    continue

            # If no strategy succeeded, raise error
            logger.error(
                "Failed to extract brochure URL from page",
                page_url=page_url,
                store_id=store_id
            )
            raise ScrapingError(
                f"Could not extract brochure URL from page: {page_url}",
                page_url=page_url,
                store_id=store_id
            )

        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to fetch page for scraping",
                page_url=page_url,
                store_id=store_id,
                error=str(e)
            )
            raise ScrapingError(
                f"Failed to fetch page: {str(e)}",
                page_url=page_url,
                store_id=store_id
            )

    def _extract_from_meta_tags(
        self,
        soup: BeautifulSoup,
        page_url: str,
        store_id: str
    ) -> Optional[Tuple[str, str]]:
        """Extract PDF URL from meta tags."""
        # Look for og:url or similar meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            content = meta.get('content', '')
            if content.endswith('.pdf'):
                url = urljoin(page_url, content)
                return url, 'pdf'
        return None

    def _extract_from_links(
        self,
        soup: BeautifulSoup,
        page_url: str,
        store_id: str
    ) -> Optional[Tuple[str, str]]:
        """Extract PDF URL from <a> tags."""
        # Look for links with .pdf extension
        links = soup.find_all('a', href=True)

        pdf_keywords = ['brochure', 'brošura', 'leaflet', 'flyer', 'catalog', 'catalogue']

        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()

            # Direct PDF link
            if href.endswith('.pdf'):
                url = urljoin(page_url, href)
                return url, 'pdf'

            # Link text contains brochure keywords
            if any(keyword in text for keyword in pdf_keywords):
                if href.endswith('.pdf'):
                    url = urljoin(page_url, href)
                    return url, 'pdf'

        return None

    def _extract_from_scripts(
        self,
        soup: BeautifulSoup,
        page_url: str,
        store_id: str
    ) -> Optional[Tuple[str, str]]:
        """Extract PDF URL from JavaScript code."""
        scripts = soup.find_all('script')

        # Common patterns for PDF URLs in JavaScript
        pdf_patterns = [
            r'["\']([^"\']*\.pdf)["\']',  # Quoted PDF URLs
            r'pdfUrl["\s:=]+["\']([^"\']+)["\']',  # pdfUrl variable
            r'file["\s:=]+["\']([^"\']+\.pdf)["\']',  # file variable
            r'url["\s:=]+["\']([^"\']+\.pdf)["\']',  # url variable
            r'src["\s:=]+["\']([^"\']+\.pdf)["\']',  # src attribute
        ]

        for script in scripts:
            script_text = script.string
            if not script_text:
                continue

            for pattern in pdf_patterns:
                matches = re.findall(pattern, script_text, re.IGNORECASE)
                if matches:
                    # Take the first match
                    pdf_url = matches[0]
                    url = urljoin(page_url, pdf_url)

                    # Validate it looks like a URL
                    if urlparse(url).scheme in ['http', 'https']:
                        return url, 'pdf'

        return None

    def _extract_from_iframes(
        self,
        soup: BeautifulSoup,
        page_url: str,
        store_id: str
    ) -> Optional[Tuple[str, str]]:
        """Extract PDF URL from iframe embeds."""
        iframes = soup.find_all('iframe', src=True)

        for iframe in iframes:
            src = iframe.get('src', '')

            # Direct PDF in iframe
            if src.endswith('.pdf'):
                url = urljoin(page_url, src)
                return url, 'pdf'

            # PDF viewer URLs (like Google Drive, Issuu, etc.)
            if 'viewer' in src.lower() or 'embed' in src.lower():
                # Try to extract PDF URL from viewer
                parsed = urlparse(src)
                query_params = parse_qs(parsed.query)

                # Check for 'url' or 'file' parameters
                for param in ['url', 'file', 'pdf', 'document']:
                    if param in query_params:
                        pdf_url = query_params[param][0]
                        url = urljoin(page_url, pdf_url)
                        return url, 'pdf'

        return None

    def _extract_from_data_attributes(
        self,
        soup: BeautifulSoup,
        page_url: str,
        store_id: str
    ) -> Optional[Tuple[str, str]]:
        """Extract PDF URL from data-* attributes."""
        # Look for elements with data attributes containing PDF URLs
        elements = soup.find_all(attrs={'data-pdf': True})
        if elements:
            url = urljoin(page_url, elements[0]['data-pdf'])
            return url, 'pdf'

        elements = soup.find_all(attrs={'data-src': True})
        for elem in elements:
            src = elem['data-src']
            if src.endswith('.pdf'):
                url = urljoin(page_url, src)
                return url, 'pdf'

        elements = soup.find_all(attrs={'data-url': True})
        for elem in elements:
            data_url = elem['data-url']
            if data_url.endswith('.pdf'):
                url = urljoin(page_url, data_url)
                return url, 'pdf'

        return None

    def _extract_from_json_ld(
        self,
        soup: BeautifulSoup,
        page_url: str,
        store_id: str
    ) -> Optional[Tuple[str, str]]:
        """Extract PDF URL from JSON-LD structured data."""
        json_ld_scripts = soup.find_all('script', type='application/ld+json')

        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)

                # Recursively search for PDF URLs in JSON
                def find_pdf_in_json(obj):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if isinstance(value, str) and value.endswith('.pdf'):
                                return value
                            result = find_pdf_in_json(value)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_pdf_in_json(item)
                            if result:
                                return result
                    return None

                pdf_url = find_pdf_in_json(data)
                if pdf_url:
                    url = urljoin(page_url, pdf_url)
                    return url, 'pdf'

            except json.JSONDecodeError:
                continue

        return None

    def _extract_from_common_patterns(
        self,
        soup: BeautifulSoup,
        page_url: str,
        store_id: str
    ) -> Optional[Tuple[str, str]]:
        """Extract PDF URL using common patterns for known services."""
        # Issuu pattern
        if 'issuu.com' in page_url:
            # Try to extract document ID and construct PDF download URL
            match = re.search(r'issuu\.com/[^/]+/docs/([^/?]+)', page_url)
            if match:
                doc_id = match.group(1)
                # Issuu doesn't provide direct PDF downloads easily, would need API
                logger.warning(
                    "Issuu brochure detected, direct PDF extraction not supported",
                    page_url=page_url,
                    store_id=store_id
                )

        # Yumpu pattern
        if 'yumpu.com' in page_url:
            logger.warning(
                "Yumpu brochure detected, direct PDF extraction may be limited",
                page_url=page_url,
                store_id=store_id
            )

        # Calaméo pattern
        if 'calameo.com' in page_url:
            logger.warning(
                "Calaméo brochure detected, direct PDF extraction may be limited",
                page_url=page_url,
                store_id=store_id
            )

        # Flipsnack pattern
        if 'flipsnack.com' in page_url:
            logger.warning(
                "Flipsnack brochure detected, direct PDF extraction may be limited",
                page_url=page_url,
                store_id=store_id
            )

        # For Lidl Bulgaria and similar sites
        if 'lidl.bg' in page_url or 'lidl.com' in page_url:
            return self._extract_lidl_pattern(soup, page_url, store_id)

        return None

    def _extract_lidl_pattern(
        self,
        soup: BeautifulSoup,
        page_url: str,
        store_id: str
    ) -> Optional[Tuple[str, str]]:
        """Extract brochure URL from Lidl-specific patterns."""
        logger.info("Attempting Lidl-specific extraction", page_url=page_url)

        # Look for PDF links in specific Lidl elements
        # Lidl often uses data attributes or hidden inputs

        # Try to find PDF URL in page content
        page_text = soup.get_text()

        # Look for PDF URLs in the entire page content
        pdf_matches = re.findall(r'https?://[^\s<>"]+\.pdf', page_text)
        if pdf_matches:
            # Filter for Lidl CDN or relevant domains
            for match in pdf_matches:
                if 'lidl' in match.lower() or 'cdn' in match.lower():
                    return match, 'pdf'
            # If no Lidl-specific, return first match
            return pdf_matches[0], 'pdf'

        # Look for API endpoints that might serve brochure data
        api_patterns = [
            r'api[^\"\']*brochure[^\"\']*',
            r'api[^\"\']*leaflet[^\"\']*',
            r'/api/[^\"\']*',
        ]

        scripts = soup.find_all('script')
        for script in scripts:
            script_text = script.string if script.string else ''
            for pattern in api_patterns:
                matches = re.findall(pattern, script_text, re.IGNORECASE)
                if matches:
                    logger.info(
                        "Found potential API endpoint",
                        endpoint=matches[0],
                        store_id=store_id
                    )
                    # Would need to fetch API endpoint separately
                    # This is a future enhancement

        return None

    def extract_images_from_viewer(
        self,
        page_url: str,
        store_id: str
    ) -> List[str]:
        """
        Extract image URLs from brochure viewers.

        For viewers that display brochures as images (Flipbook, etc.),
        extracts all page image URLs.

        Args:
            page_url: URL of the viewer page
            store_id: Store identifier

        Returns:
            List of image URLs

        Raises:
            ScrapingError: If extraction fails
        """
        logger.info(
            "Extracting images from viewer",
            page_url=page_url,
            store_id=store_id
        )

        try:
            response = self.session.get(
                page_url,
                timeout=self.timeout_seconds
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')
            image_urls = []

            # Look for images with specific patterns
            images = soup.find_all('img')
            for img in images:
                src = img.get('src', '') or img.get('data-src', '')

                # Filter for likely brochure images
                if any(keyword in src.lower() for keyword in ['page', 'brochure', 'leaflet', 'thumb']):
                    url = urljoin(page_url, src)
                    image_urls.append(url)

            if image_urls:
                logger.info(
                    "Extracted images from viewer",
                    image_count=len(image_urls),
                    store_id=store_id
                )
                return image_urls

            raise ScrapingError(
                f"No images found in viewer: {page_url}",
                page_url=page_url,
                store_id=store_id
            )

        except requests.exceptions.RequestException as e:
            raise ScrapingError(
                f"Failed to fetch viewer page: {str(e)}",
                page_url=page_url,
                store_id=store_id
            )

    def validate_pdf_url(self, url: str) -> bool:
        """
        Validate that a URL points to an accessible PDF.

        Args:
            url: URL to validate

        Returns:
            True if URL is accessible and returns PDF content
        """
        try:
            response = self.session.head(
                url,
                timeout=self.timeout_seconds,
                allow_redirects=True
            )
            content_type = response.headers.get('Content-Type', '').lower()

            return (
                response.status_code == 200 and
                'application/pdf' in content_type
            )
        except Exception as e:
            logger.warning(
                "PDF URL validation failed",
                url=url,
                error=str(e)
            )
            return False
