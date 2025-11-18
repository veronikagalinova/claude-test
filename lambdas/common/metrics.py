"""
CloudWatch custom metrics utilities.

Provides helper functions for publishing custom metrics to CloudWatch.
"""

import boto3
from typing import Dict, List, Optional
from datetime import datetime


class MetricsPublisher:
    """
    CloudWatch metrics publisher for custom application metrics.
    """

    def __init__(self, namespace: str = "BrochureScanner"):
        """
        Initialize metrics publisher.

        Args:
            namespace: CloudWatch namespace for metrics
        """
        self.namespace = namespace
        self.cloudwatch = boto3.client('cloudwatch')
        self._metric_buffer: List[Dict] = []

    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = 'Count',
        dimensions: Optional[Dict[str, str]] = None
    ):
        """
        Add a metric to the buffer.

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (Count, Seconds, Milliseconds, Bytes, etc.)
            dimensions: Optional dimensions for filtering (e.g., {'StoreId': 'walmart'})
        """
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        }

        if dimensions:
            metric_data['Dimensions'] = [
                {'Name': key, 'Value': value}
                for key, value in dimensions.items()
            ]

        self._metric_buffer.append(metric_data)

        # Flush if buffer reaches 20 metrics (CloudWatch limit per API call)
        if len(self._metric_buffer) >= 20:
            self.flush()

    def increment_counter(
        self,
        metric_name: str,
        dimensions: Optional[Dict[str, str]] = None
    ):
        """
        Increment a counter metric by 1.

        Args:
            metric_name: Name of the counter metric
            dimensions: Optional dimensions
        """
        self.put_metric(metric_name, 1.0, 'Count', dimensions)

    def record_duration(
        self,
        metric_name: str,
        milliseconds: float,
        dimensions: Optional[Dict[str, str]] = None
    ):
        """
        Record a duration metric.

        Args:
            metric_name: Name of the duration metric
            milliseconds: Duration in milliseconds
            dimensions: Optional dimensions
        """
        self.put_metric(metric_name, milliseconds, 'Milliseconds', dimensions)

    def flush(self):
        """
        Flush buffered metrics to CloudWatch.

        This is automatically called when buffer reaches 20 metrics,
        but should also be called at the end of Lambda execution.
        """
        if not self._metric_buffer:
            return

        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=self._metric_buffer
            )
            self._metric_buffer = []
        except Exception as e:
            # Log error but don't fail Lambda execution due to metrics
            print(f"Error publishing metrics: {str(e)}")


# Global metrics publisher instance
_metrics_publisher: Optional[MetricsPublisher] = None


def get_metrics_publisher(namespace: str = "BrochureScanner") -> MetricsPublisher:
    """
    Get or create global metrics publisher instance.

    Args:
        namespace: CloudWatch namespace

    Returns:
        MetricsPublisher instance
    """
    global _metrics_publisher
    if _metrics_publisher is None:
        _metrics_publisher = MetricsPublisher(namespace)
    return _metrics_publisher
