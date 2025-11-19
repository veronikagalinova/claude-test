# -*- coding: utf-8 -*-
"""
KeywordSearchLambda: Searches for keywords in Textract output with Cyrillic support
"""
import json
import os
import logging
import re
from typing import Dict, Any, List, Tuple
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')
sns_client = boto3.client('sns')

# Environment variables
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
SOURCE_BUCKET = os.environ['SOURCE_BUCKET']
METADATA_TABLE = os.environ['METADATA_TABLE_NAME']
KEYWORD_FOUND_TOPIC_ARN = os.environ['KEYWORD_FOUND_TOPIC_ARN']
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


def lambda_handler(event, context):
    """
    Main Lambda handler triggered by S3 PUT on Textract output

    Event format (S3):
    {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "..."},
                    "object": {"key": "..."}
                }
            }
        ]
    }
    """
    logger.info(f"KeywordSearchLambda invoked")

    try:
        for record in event.get('Records', []):
            s3_info = record.get('s3', {})
            bucket = s3_info.get('bucket', {}).get('name')
            key = s3_info.get('object', {}).get('key')

            if not bucket or not key:
                logger.warning(f"Invalid S3 event record: {record}")
                continue

            # Process the Textract output
            result = process_textract_output(bucket, key)
            logger.info(f"Processing result for {key}: {result}")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Keyword search completed'})
        }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_textract_output(bucket: str, key: str) -> Dict[str, Any]:
    """Process a Textract output file and search for keywords"""
    logger.info(f"Processing Textract output: s3://{bucket}/{key}")

    try:
        # Extract brochure_id from key (format: {brochure_id}/textract_output.json)
        brochure_id = key.split('/')[0]

        # Get brochure metadata from DynamoDB
        metadata = get_brochure_metadata(brochure_id)

        if not metadata:
            logger.error(f"Metadata not found for brochure_id: {brochure_id}")
            return {'status': 'error', 'error': 'Metadata not found'}

        store_id = metadata.get('store_id', {}).get('S', '')
        store_name = metadata.get('store_name', {}).get('S', '')

        # Get keyword configuration
        keywords = get_keywords_for_store(store_id)

        if not keywords:
            logger.info(f"No keywords configured for store: {store_id}")
            update_metadata_status(brochure_id, 'COMPLETED', {
                'keywords_found': 0
            })
            return {'status': 'success', 'keywords_found': 0}

        logger.info(f"Searching for {len(keywords)} keywords: {keywords}")

        # Download and parse Textract output
        textract_data = get_textract_data(bucket, key)

        # Extract text from Textract blocks
        extracted_text = extract_text_from_textract(textract_data)
        logger.info(f"Extracted {len(extracted_text)} characters of text")

        # Normalize text for searching (preserve case for context)
        normalized_text = normalize_text(extracted_text)

        # Search for keywords
        matches = search_keywords(normalized_text, extracted_text, keywords, textract_data)

        logger.info(f"Found {len(matches)} keyword matches")

        if matches:
            # Send notification
            send_notification(
                brochure_id=brochure_id,
                store_name=store_name,
                matches=matches,
                metadata=metadata
            )

            # Store match records
            store_match_records(brochure_id, matches)

            # Update metadata
            update_metadata_status(brochure_id, 'COMPLETED', {
                'keywords_found': len(matches),
                'matched_keywords': ','.join(set(m['keyword'] for m in matches))
            })

            return {
                'status': 'success',
                'keywords_found': len(matches),
                'matches': matches
            }
        else:
            # No matches found
            update_metadata_status(brochure_id, 'COMPLETED', {
                'keywords_found': 0
            })

            return {
                'status': 'success',
                'keywords_found': 0
            }

    except ClientError as e:
        logger.error(f"AWS error processing {key}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing {key}: {str(e)}", exc_info=True)
        raise


def get_brochure_metadata(brochure_id: str) -> Dict:
    """Get brochure metadata from DynamoDB"""
    try:
        response = dynamodb_client.get_item(
            TableName=METADATA_TABLE,
            Key={'brochure_id': {'S': brochure_id}}
        )
        return response.get('Item', {})
    except ClientError as e:
        logger.error(f"Error getting metadata: {str(e)}")
        return {}


def get_keywords_for_store(store_id: str) -> List[str]:
    """Get keywords from configuration"""
    try:
        # Try to get keywords from config file in S3
        config_key = 'config/keyword-config.json'
        response = s3_client.get_object(Bucket=SOURCE_BUCKET, Key=config_key)
        config = json.loads(response['Body'].read().decode('utf-8'))

        for store in config.get('stores', []):
            if store.get('store_id') == store_id:
                return store.get('keywords', [])

        logger.warning(f"No keywords found for store: {store_id}")
        return []

    except ClientError as e:
        logger.error(f"Error getting keyword config: {str(e)}")
        # Return default keywords if config not found
        return ['lupilu', 'baby', 'бебе', 'бебешки', 'играчка', 'lavazza crema']
    except Exception as e:
        logger.error(f"Error parsing keyword config: {str(e)}")
        return []


def get_textract_data(bucket: str, key: str) -> Dict:
    """Download and parse Textract JSON output"""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    return json.loads(content)


def extract_text_from_textract(textract_data: Dict) -> str:
    """Extract plain text from Textract blocks"""
    text_lines = []

    for block in textract_data.get('Blocks', []):
        if block.get('BlockType') == 'LINE':
            text = block.get('Text', '')
            if text:
                text_lines.append(text)

    return '\n'.join(text_lines)


def normalize_text(text: str) -> str:
    """Normalize text for searching (lowercase, remove extra spaces)"""
    # Convert to lowercase (works for both Latin and Cyrillic)
    text = text.lower()

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    return text


def search_keywords(normalized_text: str, original_text: str, keywords: List[str], textract_data: Dict) -> List[Dict]:
    """
    Search for keywords in text with Cyrillic support

    Returns list of matches with context
    """
    matches = []

    # Build page map for getting page numbers
    page_map = build_page_map(textract_data)

    for keyword in keywords:
        keyword_lower = keyword.lower().strip()

        # Handle multi-word phrases (e.g., "lavazza crema")
        if ' ' in keyword_lower:
            # Search for exact phrase
            phrase_matches = find_phrase_matches(normalized_text, original_text, keyword_lower, page_map)
            matches.extend(phrase_matches)
        else:
            # Search for whole word (with word boundaries)
            word_matches = find_word_matches(normalized_text, original_text, keyword_lower, page_map)
            matches.extend(word_matches)

    return matches


def find_phrase_matches(normalized_text: str, original_text: str, phrase: str, page_map: Dict) -> List[Dict]:
    """Find matches for multi-word phrases"""
    matches = []

    # Create pattern for phrase with flexible whitespace
    pattern = re.escape(phrase).replace(r'\ ', r'\s+')
    pattern = r'\b' + pattern + r'\b'

    for match in re.finditer(pattern, normalized_text, re.IGNORECASE):
        start_pos = match.start()
        end_pos = match.end()

        # Get context from original text (preserve case)
        context = get_context(original_text, start_pos, end_pos)

        # Estimate page number
        page_num = estimate_page_number(start_pos, len(normalized_text), page_map)

        matches.append({
            'keyword': phrase,
            'context': context,
            'position': start_pos,
            'page': page_num
        })

    return matches


def find_word_matches(normalized_text: str, original_text: str, word: str, page_map: Dict) -> List[Dict]:
    """Find matches for single words with word boundary"""
    matches = []

    # Pattern with word boundaries (works for Cyrillic too)
    pattern = r'\b' + re.escape(word) + r'\b'

    for match in re.finditer(pattern, normalized_text, re.IGNORECASE):
        start_pos = match.start()
        end_pos = match.end()

        # Get context from original text (preserve case)
        context = get_context(original_text, start_pos, end_pos)

        # Estimate page number
        page_num = estimate_page_number(start_pos, len(normalized_text), page_map)

        matches.append({
            'keyword': word,
            'context': context,
            'position': start_pos,
            'page': page_num
        })

    return matches


def get_context(text: str, start: int, end: int, context_length: int = 50) -> str:
    """Get text context around a match"""
    # Get surrounding text
    context_start = max(0, start - context_length)
    context_end = min(len(text), end + context_length)

    context = text[context_start:context_end]

    # Add ellipsis if truncated
    if context_start > 0:
        context = '...' + context
    if context_end < len(text):
        context = context + '...'

    # Clean up whitespace
    context = ' '.join(context.split())

    return context


def build_page_map(textract_data: Dict) -> Dict:
    """Build map of character positions to page numbers"""
    page_map = {}
    current_page = 1
    char_position = 0

    for block in textract_data.get('Blocks', []):
        if block.get('BlockType') == 'PAGE':
            current_page = block.get('Page', current_page)

        elif block.get('BlockType') == 'LINE':
            text = block.get('Text', '')
            page = block.get('Page', current_page)

            # Map this range of characters to this page
            for i in range(len(text) + 1):  # +1 for newline
                page_map[char_position + i] = page

            char_position += len(text) + 1  # +1 for newline

    return page_map


def estimate_page_number(position: int, total_length: int, page_map: Dict) -> int:
    """Estimate page number from character position"""
    if position in page_map:
        return page_map[position]

    # Find closest page in map
    closest_pos = min(page_map.keys(), key=lambda k: abs(k - position), default=None)
    if closest_pos is not None:
        return page_map[closest_pos]

    # Fallback: estimate based on position
    return 1


def send_notification(brochure_id: str, store_name: str, matches: List[Dict], metadata: Dict):
    """Send email notification via SNS"""
    try:
        filename = metadata.get('filename', {}).get('S', 'unknown')
        upload_time = metadata.get('upload_time', {}).get('S', 'unknown')
        s3_key = metadata.get('s3_key', {}).get('S', '')

        # Get unique keywords that matched
        matched_keywords = sorted(set(m['keyword'] for m in matches))

        # Build match rows for HTML table
        match_rows = []
        for match in matches[:20]:  # Limit to first 20 matches
            match_rows.append(
                f"<tr>"
                f"<td>{match['keyword']}</td>"
                f"<td>{match.get('page', 'N/A')}</td>"
                f"<td>{match['context']}</td>"
                f"</tr>"
            )

        match_rows_html = '\n'.join(match_rows)

        # Build HTML email
        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
    h2 {{ color: #2c5aa0; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
    th {{ background-color: #2c5aa0; color: white; }}
    tr:nth-child(even) {{ background-color: #f2f2f2; }}
    .highlight {{ background-color: #fff3cd; padding: 2px 4px; }}
    .metadata {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 15px 0; }}
</style>
</head>
<body>
    <h2>🎯 Keyword Matches Found in {store_name} Brochure</h2>

    <div class="metadata">
        <p><strong>Brochure:</strong> {filename}</p>
        <p><strong>Upload Time:</strong> {upload_time}</p>
        <p><strong>Total Matches:</strong> {len(matches)}</p>
        <p><strong>Matched Keywords:</strong> {', '.join(matched_keywords)}</p>
    </div>

    <h3>Match Details:</h3>
    <table>
        <tr>
            <th>Keyword</th>
            <th>Page</th>
            <th>Context</th>
        </tr>
        {match_rows_html}
    </table>

    <p style="margin-top: 20px; font-size: 12px; color: #666;">
        <small>Brochure ID: {brochure_id}</small><br>
        <small>S3 Key: {s3_key}</small>
    </p>
</body>
</html>"""

        # Plain text version
        text_body = f"""Keyword Matches Found: {store_name}

Brochure: {filename}
Upload Time: {upload_time}
Total Matches: {len(matches)}
Matched Keywords: {', '.join(matched_keywords)}

Match Details:
"""
        for match in matches[:20]:
            text_body += f"\nKeyword: {match['keyword']}\n"
            text_body += f"Page: {match.get('page', 'N/A')}\n"
            text_body += f"Context: {match['context']}\n"
            text_body += "-" * 50 + "\n"

        text_body += f"\nBrochure ID: {brochure_id}\nS3 Key: {s3_key}"

        # Send notification
        subject = f"Keyword Match Found: {store_name} - {filename}"

        message = {
            'default': text_body,
            'email': html_body
        }

        sns_client.publish(
            TopicArn=KEYWORD_FOUND_TOPIC_ARN,
            Subject=subject,
            Message=json.dumps(message),
            MessageStructure='json'
        )

        logger.info(f"Sent notification for {brochure_id} with {len(matches)} matches")

    except ClientError as e:
        logger.error(f"Error sending notification: {str(e)}")
        raise


def store_match_records(brochure_id: str, matches: List[Dict]):
    """Store keyword match records in DynamoDB"""
    try:
        timestamp = datetime.utcnow().isoformat() + 'Z'

        # Store summary of matches as an attribute on the brochure record
        match_summary = {
            'match_count': len(matches),
            'keywords': list(set(m['keyword'] for m in matches)),
            'timestamp': timestamp
        }

        update_metadata_status(brochure_id, None, {
            'match_summary': json.dumps(match_summary, ensure_ascii=False)
        })

        logger.info(f"Stored match records for {brochure_id}")

    except Exception as e:
        logger.error(f"Error storing match records: {str(e)}")


def update_metadata_status(brochure_id: str, status: str = None, additional_attrs: Dict[str, Any] = None):
    """Update brochure metadata status in DynamoDB"""
    try:
        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {
            ':updated_at': {'S': datetime.utcnow().isoformat() + 'Z'}
        }

        update_expression_parts.append("updated_at = :updated_at")

        if status:
            update_expression_parts.append("#status = :status")
            expression_attribute_names['#status'] = 'status'
            expression_attribute_values[':status'] = {'S': status}

        # Add additional attributes
        if additional_attrs:
            for key, value in additional_attrs.items():
                placeholder = f":attr_{key}"
                update_expression_parts.append(f"{key} = {placeholder}")

                # Determine DynamoDB type
                if isinstance(value, str):
                    expression_attribute_values[placeholder] = {'S': value}
                elif isinstance(value, int):
                    expression_attribute_values[placeholder] = {'N': str(value)}
                elif isinstance(value, bool):
                    expression_attribute_values[placeholder] = {'BOOL': value}
                else:
                    expression_attribute_values[placeholder] = {'S': str(value)}

        update_expression = "SET " + ", ".join(update_expression_parts)

        params = {
            'TableName': METADATA_TABLE,
            'Key': {'brochure_id': {'S': brochure_id}},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_attribute_values
        }

        if expression_attribute_names:
            params['ExpressionAttributeNames'] = expression_attribute_names

        dynamodb_client.update_item(**params)

        logger.info(f"Updated metadata for {brochure_id}")

    except ClientError as e:
        logger.error(f"Error updating metadata: {str(e)}")
