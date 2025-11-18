"""
AWS SDK client singletons with retry configuration.

Provides reusable boto3 clients with proper retry logic and timeouts.
"""

import boto3
from botocore.config import Config
from typing import Optional


# Retry configuration for AWS SDK clients
# Implements exponential backoff with jitter
RETRY_CONFIG = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'  # Uses adaptive retry mode with exponential backoff
    },
    connect_timeout=10,
    read_timeout=60
)


class AWSClients:
    """
    Singleton container for AWS SDK clients.

    Clients are lazily initialized and reused across Lambda invocations
    to improve cold start performance.
    """

    _s3_client = None
    _dynamodb_client = None
    _textract_client = None
    _sns_client = None
    _ses_client = None

    @classmethod
    def s3(cls):
        """Get S3 client with retry configuration."""
        if cls._s3_client is None:
            cls._s3_client = boto3.client('s3', config=RETRY_CONFIG)
        return cls._s3_client

    @classmethod
    def dynamodb(cls):
        """Get DynamoDB client with retry configuration."""
        if cls._dynamodb_client is None:
            cls._dynamodb_client = boto3.client('dynamodb', config=RETRY_CONFIG)
        return cls._dynamodb_client

    @classmethod
    def textract(cls):
        """Get Textract client with retry configuration."""
        if cls._textract_client is None:
            cls._textract_client = boto3.client('textract', config=RETRY_CONFIG)
        return cls._textract_client

    @classmethod
    def sns(cls):
        """Get SNS client with retry configuration."""
        if cls._sns_client is None:
            cls._sns_client = boto3.client('sns', config=RETRY_CONFIG)
        return cls._sns_client

    @classmethod
    def ses(cls):
        """Get SES client with retry configuration."""
        if cls._ses_client is None:
            cls._ses_client = boto3.client('ses', config=RETRY_CONFIG)
        return cls._ses_client

    @classmethod
    def reset_clients(cls):
        """
        Reset all clients.

        Useful for testing to ensure clean state.
        """
        cls._s3_client = None
        cls._dynamodb_client = None
        cls._textract_client = None
        cls._sns_client = None
        cls._ses_client = None


def get_s3_client():
    """Get S3 client."""
    return AWSClients.s3()


def get_dynamodb_client():
    """Get DynamoDB client."""
    return AWSClients.dynamodb()


def get_textract_client():
    """Get Textract client."""
    return AWSClients.textract()


def get_sns_client():
    """Get SNS client."""
    return AWSClients.sns()


def get_ses_client():
    """Get SES client."""
    return AWSClients.ses()
