from fastapi import APIRouter, Depends, HTTPException, Query
from app.deps.auth import verify_firebase_token
import os
import boto3


router = APIRouter()


@router.get("/media/upload_url")
def get_upload_url(
    filename: str = Query(..., description="Original filename"),
    content_type: str = Query(..., description="MIME type"),
    token: str = Depends(verify_firebase_token),
):
    bucket = os.getenv("MEDIA_BUCKET") or os.getenv("S3_BUCKET")
    if not bucket:
        raise HTTPException(status_code=501, detail="MEDIA_BUCKET env not configured")

    s3 = boto3.client("s3")
    key = f"uploads/{filename}"
    try:
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=3600,
        )
        asset_url = f"https://{bucket}.s3.amazonaws.com/{key}"
        return {"upload_url": upload_url, "asset_url": asset_url}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create upload URL: {exc}")
