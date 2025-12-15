"""
S3 Uploader Service

Handles downloading images from URLs (e.g., Stream Chat CDN) and uploading them to S3.
Used for attaching photos to incidents with permanent storage.
"""

import logging
import httpx
import boto3
from typing import Optional
from datetime import datetime
from uuid import uuid4
import os

logger = logging.getLogger(__name__)


class S3Uploader:
    """Service for uploading images to S3 with automatic naming and organization."""

    def __init__(self):
        """Initialize S3 client from environment variables."""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'landten-incidents')
        logger.info(f"S3Uploader initialized for bucket: {self.bucket_name}")

    async def download_image(self, url: str, timeout: int = 30) -> Optional[bytes]:
        """
        Download an image from a URL.

        Args:
            url: Image URL (e.g., Stream Chat CDN URL)
            timeout: Request timeout in seconds

        Returns:
            Image bytes if successful, None if failed
        """
        try:
            logger.info(f"Downloading image from: {url[:80]}...")

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"URL returned non-image content-type: {content_type}")
                    return None

                image_bytes = response.content
                logger.info(f"✅ Downloaded {len(image_bytes)} bytes")
                return image_bytes

        except httpx.HTTPError as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image: {e}")
            return None

    def upload_to_s3(
        self,
        image_bytes: bytes,
        incident_id: str,
        content_type: str = 'image/jpeg',
        metadata: Optional[dict] = None
    ) -> Optional[str]:
        """
        Upload image bytes to S3.

        Args:
            image_bytes: Image data
            incident_id: Incident ID for organizing files
            content_type: MIME type (default: image/jpeg)
            metadata: Optional metadata dict

        Returns:
            S3 URL if successful, None if failed
        """
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            unique_id = str(uuid4())[:8]
            extension = self._get_extension_from_content_type(content_type)

            # Organize by incident: incidents/{incident_id}/photos/{timestamp}-{uuid}.jpg
            s3_key = f"incidents/{incident_id}/photos/{timestamp}-{unique_id}{extension}"

            logger.info(f"Uploading to S3: {s3_key}")

            # Upload to S3
            extra_args = {
                'ContentType': content_type,
                'ACL': 'private'  # Private by default, use presigned URLs for access
            }

            if metadata:
                extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_bytes,
                **extra_args
            )

            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            logger.info(f"✅ Uploaded to S3: {s3_url}")

            return s3_url

        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return None

    async def download_and_upload(
        self,
        source_url: str,
        incident_id: str,
        content_type: str = 'image/jpeg',
        ai_analysis: Optional[str] = None
    ) -> Optional[dict]:
        """
        Download image from URL and upload to S3.

        Args:
            source_url: Source image URL (e.g., Stream Chat CDN)
            incident_id: Incident ID for organization
            content_type: MIME type
            ai_analysis: Optional AI analysis text

        Returns:
            Dict with S3 URL and metadata, or None if failed
        """
        # Download from source
        image_bytes = await self.download_image(source_url)
        if not image_bytes:
            return None

        # Prepare metadata
        metadata = {
            'source_url': source_url[:500],  # Limit metadata size
            'incident_id': incident_id,
            'uploaded_at': datetime.utcnow().isoformat()
        }

        # Upload to S3
        s3_url = self.upload_to_s3(
            image_bytes=image_bytes,
            incident_id=incident_id,
            content_type=content_type,
            metadata=metadata
        )

        if not s3_url:
            return None

        # Return photo record
        return {
            'url': s3_url,
            'source_url': source_url,
            'uploaded_at': datetime.utcnow().isoformat(),
            'file_size': len(image_bytes),
            'content_type': content_type,
            'ai_analysis': ai_analysis,
            'ai_analysis_error': None
        }

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Map MIME type to file extension."""
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/heic': '.heic',
        }
        return mime_to_ext.get(content_type.lower(), '.jpg')


# Singleton instance
_uploader_instance: Optional[S3Uploader] = None


def get_s3_uploader() -> S3Uploader:
    """Get or create S3 uploader singleton instance."""
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = S3Uploader()
    return _uploader_instance
