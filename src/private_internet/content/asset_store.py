"""S3/CloudFront asset storage for generated content (Phase 3, Task 4)."""

import os
import logging

import boto3

from private_internet.config import get_settings

logger = logging.getLogger(__name__)


class AssetStore:
    def __init__(self):
        self.bucket = os.getenv("S3_CONTENT_BUCKET")
        self.cdn_base = (os.getenv("CLOUDFRONT_BASE_URL") or "").rstrip("/")
        if not self.bucket:
            raise RuntimeError("S3_CONTENT_BUCKET env var is not configured")
        if not self.cdn_base:
            raise RuntimeError("CLOUDFRONT_BASE_URL env var is not configured")
        settings = get_settings()
        self._s3 = boto3.client("s3", region_name=settings.aws_region)

    def _upload(self, key: str, body, content_type: str) -> str:
        self._s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            CacheControl="max-age=31536000",
        )
        return f"{self.cdn_base}/{key}"

    def upload_post_image(self, image_bytes: bytes, post_id: str) -> str:
        # Nova Canvas outputs PNG, so store as .png (plan said .jpg, but a
        # mismatched ContentType would break browser rendering assumptions).
        key = f"content/posts/{post_id}/image.png"
        return self._upload(key, image_bytes, "image/png")

    def upload_video(self, video_path: str, video_id: str) -> str:
        """Used in Phase 4."""
        key = f"content/videos/{video_id}/video.mp4"
        with open(video_path, "rb") as f:
            return self._upload(key, f, "video/mp4")

    def upload_thumbnail(self, image_bytes: bytes, video_id: str) -> str:
        """Used in Phase 4."""
        key = f"content/videos/{video_id}/thumbnail.png"
        return self._upload(key, image_bytes, "image/png")
