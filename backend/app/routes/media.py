from fastapi import APIRouter, Depends, HTTPException, Query
from ..deps.auth import verify_firebase_token
import os
import boto3
import logging


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/media/upload_url")
def get_upload_url(
    filename: str = Query(..., description="Original filename"),
    content_type: str = Query(..., description="MIME type"),
    token: str = Depends(verify_firebase_token),
):
    logger.info(f"📤 [MEDIA/UPLOAD] Request for presigned URL - filename={filename}, content_type={content_type}")

    bucket = os.getenv("MEDIA_BUCKET") or os.getenv("S3_BUCKET")
    if not bucket:
        logger.error(f"❌ [MEDIA/UPLOAD] MEDIA_BUCKET env not configured")
        raise HTTPException(status_code=501, detail="MEDIA_BUCKET env not configured")

    logger.info(f"📦 [MEDIA/UPLOAD] Using S3 bucket: {bucket}")

    s3 = boto3.client("s3")
    key = f"uploads/{filename}"

    logger.info(f"🔑 [MEDIA/UPLOAD] Generating presigned URL for key={key}")

    try:
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=3600,
        )
        asset_url = f"https://{bucket}.s3.amazonaws.com/{key}"

        logger.info(f"✅ [MEDIA/UPLOAD] Successfully generated presigned URL")
        logger.info(f"🌐 [MEDIA/UPLOAD] Asset URL: {asset_url}")

        return {"upload_url": upload_url, "asset_url": asset_url}
    except Exception as exc:
        logger.error(f"❌ [MEDIA/UPLOAD] Failed to create upload URL: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create upload URL: {exc}")
