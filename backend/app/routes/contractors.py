"""
Contractor Work Scheduling and Completion Flow - Phase 2C

Complete backend API for contractor work management:
1. POST /api/v1/contractors/register - Register as contractor
2. POST /api/v1/contractors/jobs/{job_id}/schedule - Schedule work
3. POST /api/v1/contractors/jobs/{job_id}/start - Start work
4. POST /api/v1/contractors/jobs/{job_id}/complete - Complete work
5. POST /api/v1/contractors/jobs/{job_id}/completion-photos - Upload completion photos
6. GET /api/v1/contractors/profile - Get contractor profile
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import List, Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
import uuid
from datetime import datetime, timedelta
import logging
import os

from ..models.contractor import Contractor, ContractorCreate, ContractorStatus
from ..models.job import Job, JobStatus, JobPhoto
from ..deps.auth import verify_firebase_token
from ..deps.dynamo import get_dynamo_resource, table_name
from ..services.notification_service import get_notification_service

# Configure router
router = APIRouter(prefix="/api/v1/contractors", tags=["contractors"])

# Configure logging
logger = logging.getLogger(__name__)

# AWS Configuration
dynamodb = get_dynamo_resource()
s3_client = boto3.client('s3')
contractors_table = dynamodb.Table(table_name("contractors"))
jobs_table = dynamodb.Table(table_name("jobs"))

# S3 Bucket for completion photos
BUCKET_NAME = os.getenv('JOB_COMPLETION_PHOTOS_BUCKET', 'landten-job-completion-photos')

# File upload constraints
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_user_from_token(token: str) -> str:
    """
    Extract user ID from auth token.

    Args:
        token: The Firebase auth token

    Returns:
        User ID string
    """
    # For now, return the token as user_id (dev mode)
    # In production with Firebase, this would extract the UID from the decoded token
    return token


async def verify_contractor_owns_job(job_id: str, contractor_id: str) -> Dict[str, Any]:
    """
    Verify that a contractor is assigned to a job.

    Args:
        job_id: The job identifier
        contractor_id: The contractor identifier

    Returns:
        The job data if verification passes

    Raises:
        HTTPException: 404 if job not found, 403 if contractor not assigned
    """
    try:
        # Get job from DynamoDB
        # Note: We need to scan by job_id since we don't know the partition key
        response = jobs_table.scan(
            FilterExpression="job_id = :jid",
            ExpressionAttributeValues={":jid": job_id}
        )
        items = response.get('Items', [])
        job = items[0] if items else None

        if not job:
            logger.error(f"[contractors] Job not found: {job_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        # Verify contractor is assigned to this job
        if job.get('awarded_contractor_id') != contractor_id:
            logger.error(
                f"[contractors] Contractor {contractor_id} not assigned to job {job_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this job"
            )

        return job

    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"[contractors] DynamoDB error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e.response['Error']['Message']}"
        )


async def update_contractor_stats(contractor_id: str):
    """
    Update contractor statistics after job completion.

    This increments total_jobs and recalculates ratings.
    In Phase 3 (payment), this will be called after payment completion.

    Args:
        contractor_id: The contractor identifier
    """
    try:
        # Get current contractor profile
        response = contractors_table.get_item(Key={"contractor_id": contractor_id})
        contractor = response.get('Item', {})

        if not contractor:
            logger.warning(f"[contractors] Contractor not found for stats update: {contractor_id}")
            return

        # Increment completed jobs count
        completed_jobs = contractor.get('completed_jobs', 0) + 1
        total_jobs = contractor.get('total_jobs', 0)

        # Update contractor stats
        contractors_table.update_item(
            Key={"contractor_id": contractor_id},
            UpdateExpression="SET completed_jobs = :completed, updated_at = :updated",
            ExpressionAttributeValues={
                ":completed": completed_jobs,
                ":updated": datetime.utcnow().isoformat() + "Z"
            }
        )

        logger.info(
            f"[contractors] ✅ Updated stats for contractor {contractor_id}: "
            f"{completed_jobs} completed jobs"
        )

    except Exception as e:
        logger.error(f"[contractors] Failed to update contractor stats: {str(e)}")
        # Don't raise - this is a non-critical operation


def validate_image_file(upload_file: UploadFile) -> None:
    """
    Validate uploaded file is an allowed image type.

    Args:
        upload_file: The uploaded file

    Raises:
        HTTPException: If file is not a valid image type
    """
    if upload_file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )


def validate_status_transition(current_status: str, new_status: str) -> None:
    """
    Validate that a job status transition is allowed.

    Allowed transitions for contractors:
    - AWARDED → SCHEDULED
    - SCHEDULED → IN_PROGRESS
    - IN_PROGRESS → COMPLETED

    Args:
        current_status: Current job status
        new_status: Desired new status

    Raises:
        HTTPException: If transition is not allowed
    """
    allowed_transitions = {
        JobStatus.AWARDED: [JobStatus.SCHEDULED],
        JobStatus.SCHEDULED: [JobStatus.IN_PROGRESS],
        JobStatus.IN_PROGRESS: [JobStatus.COMPLETED]
    }

    if current_status not in allowed_transitions:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from status '{current_status}'"
        )

    if new_status not in allowed_transitions[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{current_status}' to '{new_status}'. "
                   f"Allowed: {', '.join(allowed_transitions[current_status])}"
        )


async def send_notification(user_id: str, notification_type: str, data: Dict[str, Any]):
    """
    Send notification to user.

    Args:
        user_id: User to notify
        notification_type: Type of notification
        data: Notification payload data
    """
    # TODO: Integrate with notification service
    logger.info(
        f"[contractors] NOTIFICATION: {notification_type} to {user_id}: {data}"
    )


# ============================================================================
# ENDPOINT 1: REGISTER AS CONTRACTOR
# ============================================================================

@router.post("/register")
async def register_contractor(
    business_name: str,
    email: str,
    phone: str,
    categories: List[str],
    service_zip_codes: List[str],
    license_number: Optional[str] = None,
    current_user: str = Depends(verify_firebase_token)
):
    """
    Register as a contractor.

    Flow:
    1. Get user_id from token
    2. Create Contractor model with initial stats (rating=0, jobs=0)
    3. Save to DynamoDB contractors table
    4. Return contractor profile

    Returns:
        Created contractor profile
    """
    logger.info(
        f"[contractors] Registering contractor | user={current_user} business={business_name}"
    )

    try:
        # Get user ID
        user_id = get_current_user_from_token(current_user)

        # Generate contractor ID
        contractor_id = f"cont_{uuid.uuid4().hex[:12]}"

        # Create contractor record
        now = datetime.utcnow()
        contractor_data = {
            "contractor_id": contractor_id,
            "user_id": user_id,
            "business_name": business_name,
            "email": email,
            "phone": phone,
            "categories": categories,
            "service_zip_codes": service_zip_codes,
            "license_number": license_number,
            "rating": None,  # No rating yet
            "total_jobs": 0,
            "completed_jobs": 0,
            "status": ContractorStatus.PENDING.value,
            "insurance_verified": "not_verified",
            "stripe_onboarding_complete": False,
            "total_earnings": 0.0,
            "created_at": now.isoformat() + "Z",
            "updated_at": now.isoformat() + "Z"
        }

        # Save to DynamoDB
        try:
            contractors_table.put_item(Item=contractor_data)
            logger.info(f"[contractors] ✅ Contractor registered: {contractor_id}")
        except ClientError as e:
            logger.error(f"[contractors] DynamoDB error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save contractor to database: {e.response['Error']['Message']}"
            )

        return {
            "success": True,
            "contractor": contractor_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[contractors] ❌ Failed to register contractor: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 2: SCHEDULE JOB
# ============================================================================

@router.post("/jobs/{job_id}/schedule")
async def schedule_job(
    job_id: str,
    scheduled_date: str,
    current_user: str = Depends(verify_firebase_token)
):
    """
    Schedule a job with a specific date/time.

    Flow:
    1. Get contractor_id from user token
    2. Verify contractor is awarded contractor for this job
    3. Validate status transition (AWARDED → SCHEDULED)
    4. Update job with scheduled_date and status=SCHEDULED
    5. Notify landlord and tenant
    6. Return success

    Args:
        job_id: The job identifier
        scheduled_date: ISO datetime string for scheduled work

    Returns:
        Success status and updated job
    """
    logger.info(
        f"[contractors] Scheduling job | job={job_id} date={scheduled_date}"
    )

    try:
        # Get user ID and find contractor profile
        user_id = get_current_user_from_token(current_user)

        # Find contractor_id for this user
        # Note: In production, use a GSI on user_id
        response = contractors_table.scan(
            FilterExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        contractors = response.get('Items', [])

        if not contractors:
            raise HTTPException(
                status_code=404,
                detail="Contractor profile not found. Please register first."
            )

        contractor_id = contractors[0]['contractor_id']

        # Verify contractor owns this job
        job = await verify_contractor_owns_job(job_id, contractor_id)

        # Validate status transition
        current_status = job.get('status', '')
        validate_status_transition(current_status, JobStatus.SCHEDULED)

        # Parse and validate scheduled date
        try:
            scheduled_datetime = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use ISO 8601 format (e.g., '2025-12-15T14:30:00Z')"
            )

        # Update job in DynamoDB
        now = datetime.utcnow()
        try:
            update_response = jobs_table.update_item(
                Key={
                    "user_id": job.get('user_id'),
                    "job_id": job_id
                },
                UpdateExpression="SET scheduled_date = :scheduled, #status = :status, updated_at = :updated",
                ExpressionAttributeNames={
                    "#status": "status"  # 'status' is a reserved word
                },
                ExpressionAttributeValues={
                    ":scheduled": scheduled_date,
                    ":status": JobStatus.SCHEDULED.value,
                    ":updated": now.isoformat() + "Z"
                },
                ReturnValues="ALL_NEW"
            )

            updated_job = update_response.get('Attributes', {})
            logger.info(f"[contractors] ✅ Job scheduled: {job_id} for {scheduled_date}")

        except ClientError as e:
            logger.error(f"[contractors] Failed to update job: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update job: {e.response['Error']['Message']}"
            )

        # Notify landlord and tenant
        landlord_id = job.get('landlord_id')
        tenant_id = job.get('tenant_id')

        if landlord_id:
            await send_notification(
                landlord_id,
                "job_scheduled",
                {
                    "job_id": job_id,
                    "scheduled_date": scheduled_date,
                    "contractor_id": contractor_id
                }
            )

        if tenant_id:
            await send_notification(
                tenant_id,
                "job_scheduled",
                {
                    "job_id": job_id,
                    "scheduled_date": scheduled_date,
                    "contractor_id": contractor_id
                }
            )

        return {
            "success": True,
            "message": f"Job scheduled for {scheduled_date}",
            "job": updated_job
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[contractors] ❌ Failed to schedule job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 3: START JOB
# ============================================================================

@router.post("/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    current_user: str = Depends(verify_firebase_token)
):
    """
    Mark job as in progress.

    Flow:
    1. Verify contractor ownership
    2. Validate status transition (SCHEDULED → IN_PROGRESS)
    3. Update job status to IN_PROGRESS
    4. Notify landlord
    5. Return success

    Args:
        job_id: The job identifier

    Returns:
        Success status and updated job
    """
    logger.info(f"[contractors] Starting job | job={job_id}")

    try:
        # Get user ID and find contractor profile
        user_id = get_current_user_from_token(current_user)

        # Find contractor_id for this user
        response = contractors_table.scan(
            FilterExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        contractors = response.get('Items', [])

        if not contractors:
            raise HTTPException(
                status_code=404,
                detail="Contractor profile not found. Please register first."
            )

        contractor_id = contractors[0]['contractor_id']

        # Verify contractor owns this job
        job = await verify_contractor_owns_job(job_id, contractor_id)

        # Validate status transition
        current_status = job.get('status', '')
        validate_status_transition(current_status, JobStatus.IN_PROGRESS)

        # Update job in DynamoDB
        now = datetime.utcnow()
        try:
            update_response = jobs_table.update_item(
                Key={
                    "user_id": job.get('user_id'),
                    "job_id": job_id
                },
                UpdateExpression="SET #status = :status, updated_at = :updated",
                ExpressionAttributeNames={
                    "#status": "status"
                },
                ExpressionAttributeValues={
                    ":status": JobStatus.IN_PROGRESS.value,
                    ":updated": now.isoformat() + "Z"
                },
                ReturnValues="ALL_NEW"
            )

            updated_job = update_response.get('Attributes', {})
            logger.info(f"[contractors] ✅ Job started: {job_id}")

        except ClientError as e:
            logger.error(f"[contractors] Failed to update job: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update job: {e.response['Error']['Message']}"
            )

        # Notify landlord
        landlord_id = job.get('landlord_id')
        if landlord_id:
            await send_notification(
                landlord_id,
                "job_started",
                {
                    "job_id": job_id,
                    "contractor_id": contractor_id
                }
            )

        return {
            "success": True,
            "message": "Job started",
            "job": updated_job
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[contractors] ❌ Failed to start job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 4: COMPLETE JOB
# ============================================================================

@router.post("/jobs/{job_id}/complete")
async def complete_job(
    job_id: str,
    completion_notes: str,
    current_user: str = Depends(verify_firebase_token)
):
    """
    Mark job as completed.

    Flow:
    1. Verify contractor ownership
    2. Validate status transition (IN_PROGRESS → COMPLETED)
    3. Update job status to COMPLETED and set completion_date
    4. Update contractor stats (increment completed_jobs)
    5. Notify landlord that work is complete
    6. Return success

    Note: Photos are uploaded separately via /completion-photos endpoint

    Args:
        job_id: The job identifier
        completion_notes: Contractor's notes about the completed work

    Returns:
        Success status and updated job
    """
    logger.info(f"[contractors] Completing job | job={job_id}")

    try:
        # Get user ID and find contractor profile
        user_id = get_current_user_from_token(current_user)

        # Find contractor_id for this user
        response = contractors_table.scan(
            FilterExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        contractors = response.get('Items', [])

        if not contractors:
            raise HTTPException(
                status_code=404,
                detail="Contractor profile not found. Please register first."
            )

        contractor_id = contractors[0]['contractor_id']

        # Verify contractor owns this job
        job = await verify_contractor_owns_job(job_id, contractor_id)

        # Validate status transition
        current_status = job.get('status', '')
        validate_status_transition(current_status, JobStatus.COMPLETED)

        # Update job in DynamoDB
        now = datetime.utcnow()
        try:
            update_response = jobs_table.update_item(
                Key={
                    "user_id": job.get('user_id'),
                    "job_id": job_id
                },
                UpdateExpression="SET #status = :status, completion_date = :completion_date, "
                                "completion_notes = :notes, updated_at = :updated",
                ExpressionAttributeNames={
                    "#status": "status"
                },
                ExpressionAttributeValues={
                    ":status": JobStatus.COMPLETED.value,
                    ":completion_date": now.isoformat() + "Z",
                    ":notes": completion_notes,
                    ":updated": now.isoformat() + "Z"
                },
                ReturnValues="ALL_NEW"
            )

            updated_job = update_response.get('Attributes', {})
            logger.info(f"[contractors] ✅ Job completed: {job_id}")

        except ClientError as e:
            logger.error(f"[contractors] Failed to update job: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update job: {e.response['Error']['Message']}"
            )

        # Update contractor stats
        await update_contractor_stats(contractor_id)

        # Notify landlord that work is complete
        landlord_id = job.get('landlord_id')
        if landlord_id:
            await send_notification(
                landlord_id,
                "job_completed",
                {
                    "job_id": job_id,
                    "contractor_id": contractor_id,
                    "completion_notes": completion_notes,
                    "completion_date": now.isoformat() + "Z"
                }
            )

        return {
            "success": True,
            "message": "Job completed successfully",
            "job": updated_job
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[contractors] ❌ Failed to complete job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 5: UPLOAD COMPLETION PHOTOS
# ============================================================================

@router.post("/jobs/{job_id}/completion-photos")
async def upload_completion_photo(
    job_id: str,
    file: UploadFile = File(...),
    current_user: str = Depends(verify_firebase_token)
):
    """
    Upload a completion photo for a job.

    Multiple photos can be uploaded by calling this endpoint multiple times.

    Flow:
    1. Verify contractor ownership
    2. Validate file is an image
    3. Generate unique photo_id
    4. Upload to S3: jobs/{job_id}/completion/{photo_id}.{ext}
    5. Generate presigned URL (7 days)
    6. Update job.completion_photos array using list_append
    7. Return photo_id and URL

    Args:
        job_id: The job identifier
        file: The image file to upload

    Returns:
        Photo data with photo_id and presigned URL
    """
    logger.info(
        f"[contractors] Uploading completion photo | job={job_id} filename={file.filename}"
    )

    try:
        # Validate file type
        validate_image_file(file)

        # Get user ID and find contractor profile
        user_id = get_current_user_from_token(current_user)

        # Find contractor_id for this user
        response = contractors_table.scan(
            FilterExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        contractors = response.get('Items', [])

        if not contractors:
            raise HTTPException(
                status_code=404,
                detail="Contractor profile not found. Please register first."
            )

        contractor_id = contractors[0]['contractor_id']

        # Verify contractor owns this job
        job = await verify_contractor_owns_job(job_id, contractor_id)

        # Generate unique photo ID and S3 key
        photo_id = f"photo_{uuid.uuid4().hex[:12]}"
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        s3_key = f"jobs/{job_id}/completion/{photo_id}.{file_extension}"

        # Read file contents
        file_contents = await file.read()

        # Validate file size
        if len(file_contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # Upload to S3
        # Debug: List all available S3 buckets
        try:
            buckets = s3_client.list_buckets()
            bucket_names = [b['Name'] for b in buckets.get('Buckets', [])]
            logger.info(f"[contractors] 🪣 Available S3 buckets: {bucket_names}")
        except ClientError as e:
            logger.error(f"[contractors] ⚠️ Failed to list buckets: {e}")

        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=file_contents,
                ContentType=file.content_type,
                Metadata={
                    'job_id': job_id,
                    'photo_id': photo_id,
                    'uploaded_by': contractor_id
                }
            )
            logger.info(f"[contractors] ✅ Uploaded to S3: {s3_key}")
        except ClientError as e:
            logger.error(f"[contractors] S3 upload error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to S3: {e.response['Error']['Message']}"
            )

        # Generate presigned URL (7 days expiry)
        try:
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': BUCKET_NAME,
                    'Key': s3_key
                },
                ExpiresIn=7 * 24 * 60 * 60  # 7 days in seconds
            )
        except ClientError as e:
            logger.error(f"[contractors] Failed to generate presigned URL: {str(e)}")
            presigned_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        # Create photo record
        now = datetime.utcnow()
        photo_record = {
            "photo_id": photo_id,
            "s3_url": f"s3://{BUCKET_NAME}/{s3_key}",
            "thumbnail_url": None,  # TODO: Generate thumbnail in future phase
            "uploaded_at": now.isoformat() + "Z",
            "uploaded_by": contractor_id,
            "caption": None
        }

        # Update job.completion_photos array atomically using list_append
        try:
            jobs_table.update_item(
                Key={
                    "user_id": job.get('user_id'),
                    "job_id": job_id
                },
                UpdateExpression="SET completion_photos = list_append(if_not_exists(completion_photos, :empty_list), :photo), updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":photo": [photo_record],
                    ":empty_list": [],
                    ":updated_at": now.isoformat() + "Z"
                },
                ReturnValues="NONE"
            )
            logger.info(f"[contractors] ✅ Photo added to job: {photo_id}")
        except ClientError as e:
            logger.error(f"[contractors] Failed to update job photos: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update job: {e.response['Error']['Message']}"
            )

        return {
            "success": True,
            "photo_id": photo_id,
            "url": presigned_url,
            "s3_key": s3_key,
            "uploaded_at": photo_record["uploaded_at"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[contractors] ❌ Photo upload failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 6: GET CONTRACTOR PROFILE
# ============================================================================

@router.get("/profile")
async def get_contractor_profile(
    current_user: str = Depends(verify_firebase_token)
):
    """
    Get contractor profile for current user.

    Flow:
    1. Get user_id from token
    2. Find contractor profile by user_id
    3. Return contractor details with stats

    Returns:
        Contractor profile data including ratings and job statistics
    """
    logger.info(f"[contractors] Getting profile for user: {current_user}")

    try:
        # Get user ID
        user_id = get_current_user_from_token(current_user)

        # Find contractor by user_id
        # Note: In production, use a GSI on user_id for efficient lookup
        try:
            response = contractors_table.scan(
                FilterExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id}
            )

            contractors = response.get('Items', [])

            if not contractors:
                raise HTTPException(
                    status_code=404,
                    detail="Contractor profile not found. Please register first."
                )

            contractor = contractors[0]
            logger.info(f"[contractors] ✅ Retrieved profile: {contractor['contractor_id']}")

            return {
                "success": True,
                "contractor": contractor
            }

        except ClientError as e:
            logger.error(f"[contractors] DynamoDB error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[contractors] ❌ Failed to fetch profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
