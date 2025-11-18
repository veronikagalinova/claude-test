"""
Keyword matching engine for brochure text.

Implements case-insensitive, whole-word keyword matching with context extraction.
"""

import re
from typing import List, Dict
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger

logger = get_logger(__name__)


class KeywordMatcher:
    """
    Matches keywords in text with context extraction.
    """

    def __init__(self, context_chars: int = 50):
        """
        Initialize keyword matcher.

        Args:
            context_chars: Number of characters to extract before and after match
        """
        self.context_chars = context_chars

    def find_keyword_matches(
        self,
        keywords: List[str],
        pages_text: Dict[int, str]
    ) -> List[Dict]:
        """
        Find all keyword matches across pages with context.

        Args:
            keywords: List of keywords to search for
            pages_text: Dictionary mapping page number to full page text

        Returns:
            List of match dictionaries:
            [
                {
                    'keyword': str,
                    'page': int,
                    'line': int,  # Approximate line number
                    'context': str,  # Surrounding text
                    'confidence': float  # Always 100.0 for keyword matches
                }
            ]
        """
        all_matches = []

        for keyword in keywords:
            logger.debug(f"Searching for keyword: {keyword}")

            for page_num, page_text in pages_text.items():
                matches = self._find_keyword_in_text(
                    keyword=keyword,
                    text=page_text,
                    page_num=page_num
                )
                all_matches.extend(matches)

        logger.info(
            "Keyword matching complete",
            keywords_searched=len(keywords),
            pages_searched=len(pages_text),
            total_matches=len(all_matches)
        )

        return all_matches

    def _find_keyword_in_text(
        self,
        keyword: str,
        text: str,
        page_num: int
    ) -> List[Dict]:
        """
        Find all occurrences of a keyword in text.

        Args:
            keyword: Keyword to search for
            text: Text to search in
            page_num: Page number for this text

        Returns:
            List of match dictionaries
        """
        matches = []

        # Create case-insensitive regex pattern for whole-word matching
        # Handle multi-word keywords (phrases)
        if ' ' in keyword:
            # For phrases, match the exact phrase
            pattern = re.compile(
                r'\b' + re.escape(keyword) + r'\b',
                re.IGNORECASE
            )
        else:
            # For single words, use word boundary
            pattern = re.compile(
                r'\b' + re.escape(keyword) + r'\b',
                re.IGNORECASE
            )

        # Find all matches
        for match in pattern.finditer(text):
            start_pos = match.start()
            end_pos = match.end()

            # Extract context
            context = self._extract_context(text, start_pos, end_pos)

            # Calculate approximate line number
            line_num = text[:start_pos].count('\n') + 1

            matches.append({
                'keyword': keyword,
                'page': page_num,
                'line': line_num,
                'context': context,
                'confidence': 100.0  # Keyword matches are always 100% confident
            })

        if matches:
            logger.debug(
                f"Found {len(matches)} match(es) for keyword '{keyword}' on page {page_num}"
            )

        return matches

    def _extract_context(self, text: str, start_pos: int, end_pos: int) -> str:
        """
        Extract context around a match.

        Args:
            text: Full text
            start_pos: Match start position
            end_pos: Match end position

        Returns:
            Context string with "..." prefix/suffix as needed
        """
        # Extract characters before and after
        context_start = max(0, start_pos - self.context_chars)
        context_end = min(len(text), end_pos + self.context_chars)

        context = text[context_start:context_end]

        # Clean up context
        # Remove leading/trailing whitespace
        context = context.strip()

        # Replace multiple whitespace/newlines with single space
        context = re.sub(r'\s+', ' ', context)

        # Add ellipsis if context is truncated
        prefix = '...' if context_start > 0 else ''
        suffix = '...' if context_end < len(text) else ''

        return f"{prefix}{context}{suffix}"

    def aggregate_matches(self, matches: List[Dict]) -> Dict:
        """
        Aggregate match statistics.

        Args:
            matches: List of match dictionaries

        Returns:
            Aggregated statistics:
            {
                'total_matches': int,
                'unique_keywords': List[str],
                'matches_by_page': Dict[int, int],
                'matches_by_keyword': Dict[str, int]
            }
        """
        unique_keywords = list(set(m['keyword'] for m in matches))

        matches_by_page = {}
        for match in matches:
            page = match['page']
            matches_by_page[page] = matches_by_page.get(page, 0) + 1

        matches_by_keyword = {}
        for match in matches:
            keyword = match['keyword']
            matches_by_keyword[keyword] = matches_by_keyword.get(keyword, 0) + 1

        return {
            'total_matches': len(matches),
            'unique_keywords': unique_keywords,
            'matches_by_page': matches_by_page,
            'matches_by_keyword': matches_by_keyword
        }
