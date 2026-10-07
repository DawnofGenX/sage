"""Base class for AWS service adapters with fallback support.

Provides common patterns for AWS credential detection, lazy boto3 client/resource
initialization, and fallback response handling.
"""

import os


class BaseAWSAdapter:
    """Base class for AWS service adapters with fallback support.

    Handles AWS credential detection from parameters or environment variables,
    lazy boto3 client/resource initialization with error handling, and
    provides a standard fallback response helper.

    Subclasses must implement their specific API call methods and may override
    fallback behavior as needed.
    """

    def __init__(
        self,
        region: str | None = None,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
    ):
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.aws_access_key = aws_access_key or os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self._use_fallback = not (self.aws_access_key and self.aws_secret_key)
        self._client = None
        self._resource = None

    @property
    def is_fallback(self) -> bool:
        """Return True if using fallback mode (no AWS credentials)."""
        return self._use_fallback

    def _get_client(self, service_name: str):
        """Lazy-initialize a boto3 client for the given service.

        Args:
            service_name: AWS service name (e.g., 's3', 'events', 'dynamodb').

        Returns:
            A boto3 client instance.

        Raises:
            RuntimeError: If boto3 is not installed.
        """
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    service_name,
                    region_name=self.region,
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                )
            except ImportError:
                raise RuntimeError(
                    f"boto3 is required for {service_name} integration. "
                    "Install with: pip install boto3"
                )
        return self._client

    def _get_resource(self, service_name: str):
        """Lazy-initialize a boto3 resource for the given service.

        Args:
            service_name: AWS service name (e.g., 'dynamodb').

        Returns:
            A boto3 resource instance.

        Raises:
            RuntimeError: If boto3 is not installed.
        """
        if self._resource is None:
            try:
                import boto3
                self._resource = boto3.resource(
                    service_name,
                    region_name=self.region,
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                )
            except ImportError:
                raise RuntimeError(
                    f"boto3 is required for {service_name} integration. "
                    "Install with: pip install boto3"
                )
        return self._resource

    def _fallback_response(self, message: str = "fallback") -> dict:
        """Return a standard fallback response.

        Args:
            message: Optional message describing the fallback reason.

        Returns:
            A dictionary with fallback status information.
        """
        return {"status": "fallback", "message": message}
