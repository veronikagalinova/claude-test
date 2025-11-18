"""
File hashing utilities for deduplication.

Computes SHA-256 hashes of file content for duplicate detection.
"""

import hashlib

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.logger import get_logger

logger = get_logger(__name__)


def compute_file_hash(file_bytes: bytes) -> str:
    """
    Compute SHA-256 hash of file content.

    Args:
        file_bytes: File content as bytes

    Returns:
        Hexadecimal SHA-256 hash string
    """
    logger.debug(
        "Computing file hash",
        file_size_bytes=len(file_bytes)
    )

    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_bytes)
    hash_hex = sha256_hash.hexdigest()

    logger.debug(
        "File hash computed",
        hash=hash_hex,
        file_size_bytes=len(file_bytes)
    )

    return hash_hex


def compute_hash_chunked(file_bytes: bytes, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of file content using chunked processing.

    More memory-efficient for large files.

    Args:
        file_bytes: File content as bytes
        chunk_size: Size of chunks to process

    Returns:
        Hexadecimal SHA-256 hash string
    """
    logger.debug(
        "Computing file hash (chunked)",
        file_size_bytes=len(file_bytes),
        chunk_size=chunk_size
    )

    sha256_hash = hashlib.sha256()

    # Process in chunks
    for i in range(0, len(file_bytes), chunk_size):
        chunk = file_bytes[i:i + chunk_size]
        sha256_hash.update(chunk)

    hash_hex = sha256_hash.hexdigest()

    logger.debug(
        "File hash computed (chunked)",
        hash=hash_hex,
        file_size_bytes=len(file_bytes)
    )

    return hash_hex
