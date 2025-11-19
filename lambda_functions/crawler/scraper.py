# -*- coding: utf-8 -*-
"""
Web scraper for extracting brochure URLs from embedded viewers
"""
import re
import logging
from typing import Tuple
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import time

logger = logging.getLogger()


class ScrapingError(Exception):
    """Custom exception for scraping errors"""
    pass


class BrochureScraper:
    """Extracts brochure URLs from web pages using various strategies"""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,bg;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def download_brochure(self, url: str, store_id: str, max_retries: int = 3) -> Tuple[bytes, str, str]:
        """
        Download brochure with automatic web scraping if needed

        Returns:
            Tuple of (file_bytes, content_type, actual_download_url)
        """
        logger.info(f"Attempting to download brochure from: {url}")

        # Try direct download first
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout_seconds, allow_redirects=True)
                response.raise_for_status()

                content_type = response.headers.get('Content-Type', '').lower()

                # Check if we got a PDF directly
                if 'application/pdf' in content_type:
                    logger.info(f"Direct PDF download successful ({len(response.content)} bytes)")
                    return response.content, 'application/pdf', url

                # Check if we got an image
                if any(img_type in content_type for img_type in ['image/jpeg', 'image/png', 'image/webp']):
                    logger.info(f"Direct image download successful ({len(response.content)} bytes)")
                    return response.content, content_type, url

                # If we got HTML, try web scraping
                if 'text/html' in content_type:
                    logger.info("Received HTML, attempting web scraping")
                    extracted_url = self.extract_brochure_url(url, store_id, response.text)

                    # Download the extracted URL
                    logger.info(f"Downloading extracted URL: {extracted_url}")
                    pdf_response = self.session.get(extracted_url, timeout=self.timeout_seconds)
                    pdf_response.raise_for_status()

                    pdf_content_type = pdf_response.headers.get('Content-Type', 'application/pdf').lower()
                    return pdf_response.content, pdf_content_type, extracted_url

                # Unknown content type
                raise ScrapingError(f"Unexpected content type: {content_type}")

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Download attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise ScrapingError(f"Failed to download after {max_retries} attempts: {str(e)}")

    def extract_brochure_url(self, page_url: str, store_id: str, html_content: str = None) -> str:
        """
        Extract brochure URL from a web page

        Args:
            page_url: URL of the page containing the brochure
            store_id: Store identifier
            html_content: Optional pre-fetched HTML content

        Returns:
            Extracted brochure URL
        """
        logger.info(f"Extracting brochure URL from page: {page_url}")

        # Fetch HTML if not provided
        if html_content is None:
            try:
                response = self.session.get(page_url, timeout=self.timeout_seconds)
                response.raise_for_status()
                html_content = response.text
            except requests.RequestException as e:
                raise ScrapingError(f"Failed to fetch page: {str(e)}")

        # Parse HTML
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
                    logger.info(f"Successfully extracted URL using {strategy.__name__}: {result}")
                    return result
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {str(e)}")

        # No strategy succeeded
        raise ScrapingError("Could not extract brochure URL from page")

    def _extract_from_meta_tags(self, soup: BeautifulSoup, page_url: str, store_id: str) -> str:
        """Extract PDF URL from meta tags"""
        meta_tags = soup.find_all('meta', property=re.compile(r'og:.*|twitter:.*'))

        for tag in meta_tags:
            content = tag.get('content', '')
            if content and content.lower().endswith('.pdf'):
                return urljoin(page_url, content)

        return None

    def _extract_from_links(self, soup: BeautifulSoup, page_url: str, store_id: str) -> str:
        """Extract PDF URL from <a> tags"""
        links = soup.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))

        for link in links:
            href = link.get('href')
            if href:
                full_url = urljoin(page_url, href)
                if self._is_valid_pdf_url(full_url):
                    return full_url

        return None

    def _extract_from_scripts(self, soup: BeautifulSoup, page_url: str, store_id: str) -> str:
        """Extract PDF URL from JavaScript code"""
        scripts = soup.find_all('script')

        pdf_patterns = [
            r'["\']([^"\']*\.pdf)["\']',  # Quoted PDF URLs
            r'pdfUrl["\s:=]+["\']([^"\']+)["\']',  # pdfUrl variable
            r'file["\s:=]+["\']([^"\']+\.pdf)["\']',  # file variable
            r'url["\s:=]+["\']([^"\']+\.pdf)["\']',  # url variable
            r'src["\s:=]+["\']([^"\']+\.pdf)["\']',  # src attribute
            r'href["\s:=]+["\']([^"\']+\.pdf)["\']',  # href attribute
            r'https?://[^\s<>"]+\.pdf',  # Direct PDF URLs
        ]

        for script in scripts:
            script_text = script.string or ''

            for pattern in pdf_patterns:
                matches = re.findall(pattern, script_text, re.IGNORECASE)
                for match in matches:
                    potential_url = match if match.startswith('http') else urljoin(page_url, match)
                    if self._is_valid_pdf_url(potential_url):
                        return potential_url

        return None

    def _extract_from_iframes(self, soup: BeautifulSoup, page_url: str, store_id: str) -> str:
        """Extract PDF URL from iframes"""
        iframes = soup.find_all('iframe')

        for iframe in iframes:
            src = iframe.get('src', '')
            if src:
                # Check if iframe src is a PDF
                if src.lower().endswith('.pdf'):
                    return urljoin(page_url, src)

                # Check if iframe contains PDF viewer
                if any(viewer in src.lower() for viewer in ['pdf', 'viewer', 'document']):
                    # Try to extract PDF URL from iframe src parameters
                    pdf_param_patterns = [
                        r'[?&](?:file|url|pdf|doc)=([^&]+)',
                        r'[?&](?:src|source)=([^&]+\.pdf)',
                    ]
                    for pattern in pdf_param_patterns:
                        match = re.search(pattern, src, re.IGNORECASE)
                        if match:
                            potential_url = match.group(1)
                            # URL decode if needed
                            import urllib.parse
                            potential_url = urllib.parse.unquote(potential_url)
                            if self._is_valid_pdf_url(potential_url):
                                return potential_url

        return None

    def _extract_from_data_attributes(self, soup: BeautifulSoup, page_url: str, store_id: str) -> str:
        """Extract PDF URL from data-* attributes"""
        elements_with_data = soup.find_all(attrs={'data-pdf': True})
        elements_with_data += soup.find_all(attrs={'data-file': True})
        elements_with_data += soup.find_all(attrs={'data-url': True})
        elements_with_data += soup.find_all(attrs={'data-src': True})

        for element in elements_with_data:
            for attr in ['data-pdf', 'data-file', 'data-url', 'data-src']:
                value = element.get(attr)
                if value and ('.pdf' in value.lower() or 'pdf' in attr.lower()):
                    full_url = urljoin(page_url, value)
                    if self._is_valid_pdf_url(full_url):
                        return full_url

        return None

    def _extract_from_json_ld(self, soup: BeautifulSoup, page_url: str, store_id: str) -> str:
        """Extract PDF URL from JSON-LD structured data"""
        import json

        json_ld_scripts = soup.find_all('script', type='application/ld+json')

        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)

                # Search for PDF URLs in the JSON structure
                def find_pdf_in_dict(d):
                    if isinstance(d, dict):
                        for key, value in d.items():
                            if isinstance(value, str) and value.lower().endswith('.pdf'):
                                return value
                            result = find_pdf_in_dict(value)
                            if result:
                                return result
                    elif isinstance(d, list):
                        for item in d:
                            result = find_pdf_in_dict(item)
                            if result:
                                return result
                    return None

                pdf_url = find_pdf_in_dict(data)
                if pdf_url:
                    return urljoin(page_url, pdf_url)

            except json.JSONDecodeError:
                continue

        return None

    def _extract_from_common_patterns(self, soup: BeautifulSoup, page_url: str, store_id: str) -> str:
        """Extract using store-specific or common viewer patterns"""

        # Lidl-specific pattern
        if 'lidl' in page_url.lower() or 'lidl' in store_id.lower():
            result = self._extract_lidl_pattern(soup, page_url, store_id)
            if result:
                return result

        # Issuu pattern
        if 'issuu.com' in page_url.lower():
            # Issuu uses API endpoints
            match = re.search(r'/([^/]+)/docs/([^/?]+)', page_url)
            if match:
                username, doc_id = match.groups()
                api_url = f"https://issuu.com/call/stream/v1/documents/{doc_id}"
                try:
                    response = self.session.get(api_url, timeout=10)
                    data = response.json()
                    pdf_url = data.get('document', {}).get('documentPdfUrl')
                    if pdf_url:
                        return pdf_url
                except:
                    pass

        # Look for PDF URLs in the entire page content
        page_text = soup.get_text()
        pdf_matches = re.findall(r'https?://[^\s<>"]+\.pdf', page_text, re.IGNORECASE)
        if pdf_matches:
            # Return the first valid PDF URL
            for match in pdf_matches:
                if self._is_valid_pdf_url(match):
                    return match

        return None

    def _extract_lidl_pattern(self, soup: BeautifulSoup, page_url: str, store_id: str) -> str:
        """Extract brochure URL from Lidl-specific patterns"""

        # Look for PDF URLs in the entire page content
        page_text = str(soup)
        pdf_matches = re.findall(r'https?://[^\s<>"]+\.pdf', page_text, re.IGNORECASE)

        if pdf_matches:
            # Prefer URLs containing 'lidl' or 'cdn'
            for match in pdf_matches:
                if 'lidl' in match.lower() or 'cdn' in match.lower():
                    logger.info(f"Found Lidl PDF URL: {match}")
                    return match

            # Return first valid PDF URL
            if self._is_valid_pdf_url(pdf_matches[0]):
                return pdf_matches[0]

        # Try to find API endpoints
        api_patterns = [
            r'api[^\s<>"]*brochure[^\s<>"]*',
            r'/api/[^\s<>"]+',
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                try:
                    api_url = urljoin(page_url, match)
                    response = self.session.get(api_url, timeout=10)
                    if response.status_code == 200:
                        # Check if response contains PDF URL
                        response_text = response.text
                        pdf_in_response = re.findall(r'https?://[^\s<>"]+\.pdf', response_text, re.IGNORECASE)
                        if pdf_in_response:
                            return pdf_in_response[0]
                except:
                    continue

        return None

    def _is_valid_pdf_url(self, url: str) -> bool:
        """Validate if URL is likely a valid PDF URL"""
        if not url:
            return False

        # Must be HTTP/HTTPS
        if not url.startswith(('http://', 'https://')):
            return False

        # Check for PDF extension or pdf in path
        url_lower = url.lower()
        if '.pdf' in url_lower or '/pdf/' in url_lower:
            return True

        return False
