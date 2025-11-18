"""
Textract JSON parsing utilities.

Extracts text blocks with page numbers from Textract results.
"""

from typing import Dict, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger

logger = get_logger(__name__)


class TextractParser:
    """
    Parses Textract JSON responses to extract searchable text.
    """

    def parse_textract_result(self, textract_response: Dict) -> List[Dict]:
        """
        Parse Textract response and extract text blocks with metadata.

        Args:
            textract_response: Textract API response with Blocks

        Returns:
            List of text blocks with format:
            [
                {
                    'text': str,
                    'page': int,
                    'block_type': str,
                    'confidence': float,
                    'block_id': str
                }
            ]
        """
        blocks = textract_response.get('Blocks', [])

        if not blocks:
            logger.warning("Textract response contains no blocks")
            return []

        text_blocks = []

        for block in blocks:
            block_type = block.get('BlockType')

            # We primarily want LINE blocks for keyword matching
            # WORD blocks can be too granular, PAGE blocks have no text
            if block_type in ['LINE', 'WORD']:
                text = block.get('Text', '')
                if text:  # Skip empty text
                    text_blocks.append({
                        'text': text,
                        'page': block.get('Page', 1),
                        'block_type': block_type,
                        'confidence': block.get('Confidence', 0.0),
                        'block_id': block.get('Id', '')
                    })

        logger.info(
            "Parsed Textract result",
            total_blocks=len(blocks),
            text_blocks=len(text_blocks)
        )

        return text_blocks

    def get_full_text_by_page(self, text_blocks: List[Dict]) -> Dict[int, str]:
        """
        Aggregate text blocks into full text per page.

        Args:
            text_blocks: List of text blocks from parse_textract_result

        Returns:
            Dictionary mapping page number to full page text:
            {
                1: "Full text of page 1...",
                2: "Full text of page 2..."
            }
        """
        pages = {}

        for block in text_blocks:
            if block['block_type'] == 'LINE':  # Use LINE blocks for aggregation
                page = block['page']
                text = block['text']

                if page not in pages:
                    pages[page] = []

                pages[page].append(text)

        # Join lines with newlines
        full_text_pages = {
            page: '\n'.join(lines)
            for page, lines in pages.items()
        }

        logger.info(
            "Aggregated text by page",
            page_count=len(full_text_pages),
            total_chars=sum(len(text) for text in full_text_pages.values())
        )

        return full_text_pages
