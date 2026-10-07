"""S3-backed call recording storage with local file fallback.

Wraps Amazon S3 for call recording storage. Falls back to local file
storage when AWS credentials are not available.

S3 Bucket Structure:
    Bucket: sage-recordings
    ├── recordings/
    │   ├── 2024/
    │   │   ├── 01/
    │   │   │   ├── call_<id>.mp3
    │   │   │   └── call_<id>.json (metadata)
    │   │   └── 02/
    │   └── ...
    └── transcripts/
        ├── call_<id>.txt
        └── call_<id>.json (extracted data)

Environment Variables:
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_REGION: AWS region (default: us-east-1)
    S3_BUCKET_NAME: S3 bucket name (default: sage-recordings)
"""

import os
import tempfile

from aws.base import BaseAWSAdapter


class S3Storage(BaseAWSAdapter):
    """S3-backed storage for call recordings with local file fallback.

    Stores audio recordings and transcript files in S3 when AWS credentials
    are available, otherwise falls back to local filesystem storage.
    """

    def __init__(
        self,
        bucket: str | None = None,
        region: str | None = None,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
        local_dir: str | None = None,
    ):
        super().__init__(
            region=region,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
        )
        self.bucket = bucket or os.environ.get("S3_BUCKET_NAME", "sage-recordings")

        # Local fallback directory (always set for error fallback)
        self._local_dir = local_dir or os.path.join(tempfile.gettempdir(), "sage_s3_fallback")
        os.makedirs(self._local_dir, exist_ok=True)

    def _s3_key_to_local_path(self, key: str) -> str:
        """Convert an S3 key to a local file path."""
        # Sanitize key for filesystem
        safe_key = key.replace("..", "_").replace("//", "/")
        return os.path.join(self._local_dir, safe_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload_recording(self, key: str, data: bytes) -> str:
        """Upload a call recording to S3.

        Args:
            key: S3 object key (e.g., "recordings/2024/01/call_123.mp3").
            data: Binary audio data.

        Returns:
            The S3 URL of the uploaded object.
        """
        if self._use_fallback:
            return self._fallback_upload(key, data)

        try:
            client = self._get_client("s3")
            client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType="audio/mpeg",
            )
            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
        except Exception:
            # Fall back to local storage on error
            return self._fallback_upload(key, data)

    def get_recording(self, key: str) -> bytes:
        """Download a call recording from S3.

        Args:
            key: S3 object key.

        Returns:
            Binary audio data, or empty bytes if not found.
        """
        if self._use_fallback:
            return self._fallback_get(key)

        try:
            client = self._get_client("s3")
            response = client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception:
            return b""

    def list_recordings(self, prefix: str) -> list:
        """List recordings under a given prefix.

        Args:
            prefix: S3 key prefix (e.g., "recordings/2024/01/").

        Returns:
            List of S3 URIs matching the prefix.
        """
        if self._use_fallback:
            return self._fallback_list(prefix)

        try:
            client = self._get_client("s3")
            response = client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
            )
            items = response.get("Contents", [])
            return [
                f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{item['Key']}"
                for item in items
            ]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Local File Fallback
    # ------------------------------------------------------------------

    def _fallback_upload(self, key: str, data: bytes) -> str:
        """Store recording in local filesystem."""
        local_path = self._s3_key_to_local_path(key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, "wb") as f:
            f.write(data)

        return f"file://{local_path}"

    def _fallback_get(self, key: str) -> bytes:
        """Retrieve recording from local filesystem."""
        local_path = self._s3_key_to_local_path(key)

        if not os.path.exists(local_path):
            return b""

        with open(local_path, "rb") as f:
            return f.read()

    def _fallback_list(self, prefix: str) -> list:
        """List recordings in local filesystem matching prefix."""
        local_prefix = self._s3_key_to_local_path(prefix)
        results = []

        if not os.path.exists(local_prefix):
            return results

        for root, _dirs, files in os.walk(local_prefix):
            for filename in files:
                full_path = os.path.join(root, filename)
                # Convert back to S3-style key
                relative = os.path.relpath(full_path, self._local_dir)
                results.append(f"file://{full_path}")

        return results
