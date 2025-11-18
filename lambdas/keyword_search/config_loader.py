"""
Configuration loader for keyword lists and store settings.

Loads keyword configuration from S3 or DynamoDB.
"""

import json
from typing import List, Dict
from botocore.exceptions import ClientError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.aws_clients import get_s3_client
from common.exceptions import KeywordConfigError, ConfigurationError
from common.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """
    Loads and caches keyword configuration.
    """

    def __init__(self, config_bucket: str = None, config_key: str = None):
        """
        Initialize config loader.

        Args:
            config_bucket: S3 bucket containing keyword-config.json
            config_key: S3 key for keyword-config.json
        """
        self.config_bucket = config_bucket
        self.config_key = config_key or 'config/keyword-config.json'
        self.s3_client = get_s3_client()
        self._config_cache = None

    def load_config(self) -> Dict:
        """
        Load complete configuration from S3.

        Returns:
            Configuration dictionary with stores and keywords

        Raises:
            ConfigurationError: If config cannot be loaded or is invalid
        """
        if self._config_cache:
            logger.debug("Using cached configuration")
            return self._config_cache

        if not self.config_bucket:
            raise ConfigurationError(
                "Configuration bucket not specified",
                config_bucket=self.config_bucket
            )

        logger.info(
            "Loading configuration from S3",
            bucket=self.config_bucket,
            key=self.config_key
        )

        try:
            response = self.s3_client.get_object(
                Bucket=self.config_bucket,
                Key=self.config_key
            )

            config_json = response['Body'].read().decode('utf-8')
            config = json.loads(config_json)

            # Validate configuration structure
            self._validate_config(config)

            self._config_cache = config

            logger.info(
                "Configuration loaded successfully",
                stores_count=len(config.get('stores', []))
            )

            return config

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')

            if error_code == 'NoSuchKey':
                raise ConfigurationError(
                    f"Configuration file not found: {self.config_key}",
                    config_bucket=self.config_bucket,
                    config_key=self.config_key
                )

            raise ConfigurationError(
                f"Failed to load configuration: {str(e)}",
                config_bucket=self.config_bucket,
                config_key=self.config_key,
                error_code=error_code
            )

        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in configuration file: {str(e)}",
                config_bucket=self.config_bucket,
                config_key=self.config_key
            )

        except Exception as e:
            raise ConfigurationError(
                f"Unexpected error loading configuration: {str(e)}",
                config_bucket=self.config_bucket,
                config_key=self.config_key
            )

    def get_keywords_for_store(self, store_id: str) -> List[str]:
        """
        Get keyword list for a specific store.

        Args:
            store_id: Store identifier

        Returns:
            List of keywords for the store

        Raises:
            KeywordConfigError: If store not found or has no keywords
        """
        config = self.load_config()

        stores = config.get('stores', [])
        for store in stores:
            if store.get('store_id') == store_id:
                keywords = store.get('keywords', [])

                if not keywords:
                    logger.warning(
                        "Store has no keywords configured",
                        store_id=store_id
                    )
                    return []

                logger.info(
                    "Loaded keywords for store",
                    store_id=store_id,
                    keyword_count=len(keywords)
                )

                return keywords

        # Store not found in config
        logger.warning(
            "Store not found in configuration",
            store_id=store_id
        )

        # Return empty list instead of raising error (graceful degradation)
        return []

    def get_store_info(self, store_id: str) -> Dict:
        """
        Get complete store configuration.

        Args:
            store_id: Store identifier

        Returns:
            Store configuration dictionary

        Raises:
            KeywordConfigError: If store not found
        """
        config = self.load_config()

        stores = config.get('stores', [])
        for store in stores:
            if store.get('store_id') == store_id:
                return store

        raise KeywordConfigError(
            f"Store not found in configuration: {store_id}",
            store_id=store_id
        )

    def _validate_config(self, config: Dict):
        """
        Validate configuration structure.

        Args:
            config: Configuration dictionary

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if 'stores' not in config:
            raise ConfigurationError(
                "Configuration missing 'stores' field",
                config_keys=list(config.keys())
            )

        if not isinstance(config['stores'], list):
            raise ConfigurationError(
                "'stores' must be a list",
                stores_type=type(config['stores']).__name__
            )

        # Validate each store
        for idx, store in enumerate(config['stores']):
            if not isinstance(store, dict):
                raise ConfigurationError(
                    f"Store at index {idx} is not a dictionary",
                    store_index=idx
                )

            required_fields = ['store_id', 'store_name', 'keywords']
            for field in required_fields:
                if field not in store:
                    raise ConfigurationError(
                        f"Store missing required field '{field}'",
                        store_index=idx,
                        store_id=store.get('store_id', 'unknown')
                    )

            if not isinstance(store['keywords'], list):
                raise ConfigurationError(
                    f"Store keywords must be a list",
                    store_id=store.get('store_id'),
                    keywords_type=type(store['keywords']).__name__
                )

        logger.debug("Configuration validation passed")
