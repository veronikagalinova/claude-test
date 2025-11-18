"""
Custom exception classes for Brochure Scanner.

Provides domain-specific exceptions for better error handling and logging.
"""


class BrochureScannerException(Exception):
    """Base exception for all brochure scanner errors."""

    def __init__(self, message: str, **context):
        """
        Initialize exception with message and context.

        Args:
            message: Error message
            **context: Additional context fields for logging
        """
        super().__init__(message)
        self.message = message
        self.context = context


class DuplicateBrochureError(BrochureScannerException):
    """Raised when a duplicate brochure is detected."""

    pass


class UnsupportedFileFormatError(BrochureScannerException):
    """Raised when file format is not supported."""

    pass


class InvalidFileError(BrochureScannerException):
    """Raised when file is corrupted or cannot be processed."""

    pass


class TextractThrottlingError(BrochureScannerException):
    """Raised when Textract API is throttled."""

    pass


class TextractProcessingError(BrochureScannerException):
    """Raised when Textract processing fails."""

    pass


class DynamoDBError(BrochureScannerException):
    """Raised when DynamoDB operation fails."""

    pass


class S3Error(BrochureScannerException):
    """Raised when S3 operation fails."""

    pass


class ConfigurationError(BrochureScannerException):
    """Raised when configuration is invalid or missing."""

    pass


class KeywordConfigError(BrochureScannerException):
    """Raised when keyword configuration is invalid."""

    pass


class NotificationError(BrochureScannerException):
    """Raised when notification publishing fails."""

    pass
