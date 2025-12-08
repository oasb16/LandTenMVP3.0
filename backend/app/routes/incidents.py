"""
Tenant Incident Reporting Flow - Phase 2A

Complete backend API for tenant incident reporting:
1. POST /api/v1/incidents/ - Create new incident
2. POST /api/v1/incidents/{incident_id}/photos - Upload photos
3. POST /api/v1/incidents/{incident_id}/discovery - Submit discovery answers
4. GET /api/v1/incidents/my-incidents - Get tenant's incidents
5. GET /api/v1/incidents/{incident_id} - Get single incident details
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
import uuid
from datetime import datetime, timedelta
import logging
import os

from ..models.incident import (
    Incident,
    IncidentStatus,
    IncidentPhoto,
    IncidentCategory,
    IncidentUrgency,
    IncidentCreateRequest
)
from ..deps.auth import verify_firebase_token
from ..repos.property_repo import PropertyRepo
from ..deps.dynamo import get_dynamo_resource, table_name

# Configure router
router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

# Configure logging
logger = logging.getLogger(__name__)

# AWS Configuration
dynamodb = get_dynamo_resource()
s3_client = boto3.client('s3')
incidents_table = dynamodb.Table(table_name("incidents"))

# S3 Bucket name - configurable via environment variable
BUCKET_NAME = os.getenv('INCIDENT_PHOTOS_BUCKET', 'landten-incident-photos')

# File upload constraints
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_property(property_id: str) -> Dict[str, Any]:
    """
    Fetch property details from DynamoDB.

    Args:
        property_id: The property identifier

    Returns:
        Dictionary containing property data including landlord_id

    Raises:
        HTTPException: If property not found
    """
    try:
        property_repo = PropertyRepo()
        property_data = property_repo.get_property(property_id)

        if not property_data:
            raise HTTPException(
                status_code=404,
                detail=f"Property {property_id} not found"
            )

        return property_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[incidents] Error fetching property {property_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch property: {str(e)}"
        )


async def send_notification(user_id: str, notification_type: str, data: Dict[str, Any]):
    """
    Send notification to user (stub for now - will integrate with Pusher/Stream later).

    Args:
        user_id: User to notify
        notification_type: Type of notification (e.g., 'new_incident', 'incident_update')
        data: Notification payload data
    """
    # TODO: Integrate with Pusher or Stream Chat for real-time notifications
    logger.info(
        f"[incidents] NOTIFICATION: {notification_type} to {user_id}: {data}"
    )
    print(f"NOTIFICATION: {notification_type} to {user_id}: {data}")


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


# ============================================================================
# ENDPOINT 1: CREATE INCIDENT
# ============================================================================

@router.post("/")
async def create_incident(
    request: IncidentCreateRequest,
    current_user: str = Depends(verify_firebase_token)
):
    """
    Create a new incident report.

    Flow:
    1. Validate input data
    2. Fetch property to get landlord_id (or use default for dev)
    3. Create incident with status=CREATED
    4. Save to DynamoDB
    5. Send notification to landlord
    6. Return created incident

    Returns:
        Created incident data with incident_id
    """
    logger.info(
        f"[incidents] Creating incident | tenant={current_user} property={request.property_id} category={request.category}"
    )

    try:
        # Validate category and urgency
        try:
            incident_category = IncidentCategory(request.category)
            incident_urgency = IncidentUrgency(request.urgency)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category or urgency value: {str(e)}"
            )

        # Get tenant user ID
        tenant_id = get_current_user_from_token(current_user)

        # Fetch property to get landlord_id (or use default for dev)
        landlord_id = "default-landlord"
        if request.property_id and request.property_id != "default-property":
            try:
                property_data = await get_property(request.property_id)
                landlord_id = property_data.get('landlord_id', 'default-landlord')
            except HTTPException:
                # Property not found, use default landlord for dev mode
                logger.warning(f"[incidents] Property {request.property_id} not found, using default landlord")
                pass

        # Generate incident ID
        incident_id = f"inc_{uuid.uuid4().hex[:12]}"

        # Create incident record
        # Note: DynamoDB table uses composite key: user_id (PK) + incident_id (SK)
        now = datetime.utcnow()
        incident_data = {
            "user_id": tenant_id,  # Partition key
            "incident_id": incident_id,  # Sort key
            "property_id": request.property_id,
            "unit_id": request.unit_id,
            "tenant_id": tenant_id,
            "landlord_id": landlord_id,
            "title": request.title,
            "description": request.description,
            "category": incident_category.value,
            "urgency": incident_urgency.value,
            "status": IncidentStatus.CREATED.value,
            "photos": [],
            "discovery_data": None,
            "job_id": None,
            "estimated_cost": None,
            "notes": None,
            "created_at": now.isoformat() + "Z",
            "updated_at": now.isoformat() + "Z"
        }

        # Save to DynamoDB
        try:
            incidents_table.put_item(Item=incident_data)
            logger.info(f"[incidents] ✅ Incident created: {incident_id}")
        except ClientError as e:
            logger.error(f"[incidents] DynamoDB error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save incident to database: {e.response['Error']['Message']}"
            )

        # Send notification to landlord (async, non-blocking)
        await send_notification(
            landlord_id,
            "new_incident",
            {
                "incident_id": incident_id,
                "title": request.title,
                "category": request.category,
                "urgency": request.urgency,
                "property_id": request.property_id,
                "tenant_id": tenant_id
            }
        )

        return incident_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[incidents] ❌ Failed to create incident: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 2: UPLOAD PHOTO
# ============================================================================

@router.post("/{incident_id}/photos")
async def upload_photo(
    incident_id: str,
    file: UploadFile = File(...),
    current_user: str = Depends(verify_firebase_token)
):
    """
    Upload a photo to an incident.

    Flow:
    1. Validate file is an image
    2. Verify incident exists and user has access
    3. Generate unique photo_id and S3 key
    4. Upload to S3
    5. Generate presigned URL (7 days expiry)
    6. Update incident.photos array atomically
    7. Return photo details

    Returns:
        Photo data with photo_id and presigned URL
    """
    logger.info(
        f"[incidents] Uploading photo | incident={incident_id} filename={file.filename}"
    )

    try:
        # Validate file type
        validate_image_file(file)

        # Get tenant user ID
        tenant_id = get_current_user_from_token(current_user)

        # Verify incident exists and get current data
        # Note: We need to query by incident_id since we don't know user_id yet
        # For now, we'll scan to find the incident (in production, use a GSI)
        try:
            response = incidents_table.scan(
                FilterExpression="incident_id = :iid",
                ExpressionAttributeValues={":iid": incident_id}
            )
            items = response.get('Items', [])
            incident = items[0] if items else None

            if not incident:
                raise HTTPException(
                    status_code=404,
                    detail=f"Incident {incident_id} not found"
                )

            # Verify user owns this incident
            if incident.get('tenant_id') != tenant_id:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to upload photos to this incident"
                )

        except ClientError as e:
            logger.error(f"[incidents] DynamoDB error fetching incident: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

        # Generate unique photo ID and S3 key
        photo_id = f"photo_{uuid.uuid4().hex[:12]}"
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        s3_key = f"incidents/{incident_id}/{photo_id}.{file_extension}"

        # Read file contents
        file_contents = await file.read()

        # Validate file size
        if len(file_contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # Upload to S3
        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=file_contents,
                ContentType=file.content_type,
                Metadata={
                    'incident_id': incident_id,
                    'photo_id': photo_id,
                    'uploaded_by': tenant_id
                }
            )
            logger.info(f"[incidents] ✅ Uploaded to S3: {s3_key}")
        except ClientError as e:
            logger.error(f"[incidents] S3 upload error: {str(e)}")
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
            logger.error(f"[incidents] Failed to generate presigned URL: {str(e)}")
            presigned_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        # Create photo record
        now = datetime.utcnow()
        photo_record = {
            "photo_id": photo_id,
            "s3_url": f"s3://{BUCKET_NAME}/{s3_key}",
            "presigned_url": presigned_url,
            "thumbnail_url": None,  # TODO: Generate thumbnail in future phase
            "uploaded_at": now.isoformat() + "Z",
            "uploaded_by": tenant_id,
            "caption": None
        }

        # Update incident.photos array atomically using list_append
        # Use composite key: user_id + incident_id
        try:
            incidents_table.update_item(
                Key={
                    "user_id": incident.get('user_id'),
                    "incident_id": incident_id
                },
                UpdateExpression="SET photos = list_append(if_not_exists(photos, :empty_list), :photo), updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":photo": [photo_record],
                    ":empty_list": [],
                    ":updated_at": now.isoformat() + "Z"
                },
                ReturnValues="NONE"
            )
            logger.info(f"[incidents] ✅ Photo added to incident: {photo_id}")
        except ClientError as e:
            logger.error(f"[incidents] Failed to update incident photos: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update incident: {e.response['Error']['Message']}"
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
        logger.error(f"[incidents] ❌ Photo upload failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 3: SUBMIT DISCOVERY ANSWERS
# ============================================================================

@router.post("/{incident_id}/discovery")
async def submit_discovery(
    incident_id: str,
    answers: Dict[str, Any],
    current_user: str = Depends(verify_firebase_token)
):
    """
    Submit discovery questionnaire answers.

    Flow:
    1. Verify incident exists and user has access
    2. Update incident with discovery_data
    3. Change status to LANDLORD_REVIEW
    4. Notify landlord that incident is ready for review
    5. Return success

    Body:
        answers: Dictionary containing discovery Q&A data

    Returns:
        Success status and updated incident
    """
    logger.info(
        f"[incidents] Submitting discovery | incident={incident_id}"
    )

    try:
        # Get tenant user ID
        tenant_id = get_current_user_from_token(current_user)

        # Verify incident exists
        # Note: We need to scan by incident_id since we don't know user_id yet
        try:
            response = incidents_table.scan(
                FilterExpression="incident_id = :iid",
                ExpressionAttributeValues={":iid": incident_id}
            )
            items = response.get('Items', [])
            incident = items[0] if items else None

            if not incident:
                raise HTTPException(
                    status_code=404,
                    detail=f"Incident {incident_id} not found"
                )

            # Verify user owns this incident
            if incident.get('tenant_id') != tenant_id:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to update this incident"
                )

        except ClientError as e:
            logger.error(f"[incidents] DynamoDB error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

        # Update incident with discovery data and change status
        # Use composite key: user_id + incident_id
        now = datetime.utcnow()
        try:
            update_response = incidents_table.update_item(
                Key={
                    "user_id": incident.get('user_id'),
                    "incident_id": incident_id
                },
                UpdateExpression="SET discovery_data = :discovery, #status = :status, updated_at = :updated_at",
                ExpressionAttributeNames={
                    "#status": "status"  # 'status' is a reserved word in DynamoDB
                },
                ExpressionAttributeValues={
                    ":discovery": answers,
                    ":status": IncidentStatus.LANDLORD_REVIEW.value,
                    ":updated_at": now.isoformat() + "Z"
                },
                ReturnValues="ALL_NEW"
            )

            updated_incident = update_response.get('Attributes', {})
            logger.info(f"[incidents] ✅ Discovery submitted for incident: {incident_id}")

        except ClientError as e:
            logger.error(f"[incidents] Failed to update incident: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update incident: {e.response['Error']['Message']}"
            )

        # Notify landlord that incident is ready for review
        landlord_id = incident.get('landlord_id')
        if landlord_id:
            await send_notification(
                landlord_id,
                "incident_ready_for_review",
                {
                    "incident_id": incident_id,
                    "title": incident.get('title'),
                    "category": incident.get('category'),
                    "urgency": incident.get('urgency'),
                    "tenant_id": tenant_id,
                    "property_id": incident.get('property_id')
                }
            )

        return {
            "success": True,
            "message": "Discovery answers submitted successfully",
            "incident": updated_incident
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[incidents] ❌ Discovery submission failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 4: GET MY INCIDENTS
# ============================================================================

@router.get("/my-incidents")
async def get_my_incidents(
    current_user: str = Depends(verify_firebase_token)
):
    """
    Get all incidents for the current tenant.

    Flow:
    1. Query DynamoDB using tenant_id
    2. Sort by created_at descending
    3. Return incident list

    Returns:
        List of incidents for the current user
    """
    logger.info(f"[incidents] Fetching incidents for tenant: {current_user}")

    try:
        # Get tenant user ID
        tenant_id = get_current_user_from_token(current_user)

        # Query incidents by user_id
        # Note: Using scan with filter since table may have incident_id as primary key
        try:
            # Use scan with filter expression to find all incidents for this user
            response = incidents_table.scan(
                FilterExpression="user_id = :uid OR tenant_id = :uid",
                ExpressionAttributeValues={":uid": tenant_id}
            )

            incidents = response.get('Items', [])

            # Handle pagination if there are more items
            while 'LastEvaluatedKey' in response:
                response = incidents_table.scan(
                    FilterExpression="user_id = :uid OR tenant_id = :uid",
                    ExpressionAttributeValues={":uid": tenant_id},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                incidents.extend(response.get('Items', []))

            # Sort by created_at descending
            incidents.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )

            logger.info(f"[incidents] ✅ Found {len(incidents)} incidents for {tenant_id}")

            # Return incidents array directly (frontend expects array, not nested object)
            return incidents

        except ClientError as e:
            logger.error(f"[incidents] DynamoDB query error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[incidents] ❌ Failed to fetch incidents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ENDPOINT 5: GET SINGLE INCIDENT
# ============================================================================

@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    current_user: str = Depends(verify_firebase_token)
):
    """
    Get details for a specific incident.

    Flow:
    1. Fetch incident from DynamoDB
    2. Verify user has access (tenant or landlord)
    3. Return full incident details including photos and discovery data

    Returns:
        Complete incident data
    """
    logger.info(f"[incidents] Fetching incident: {incident_id}")

    try:
        # Get user ID
        user_id = get_current_user_from_token(current_user)

        # Fetch incident
        # Note: We need to scan by incident_id since we don't know user_id from the request
        try:
            response = incidents_table.scan(
                FilterExpression="incident_id = :iid",
                ExpressionAttributeValues={":iid": incident_id}
            )
            items = response.get('Items', [])
            incident = items[0] if items else None

            if not incident:
                raise HTTPException(
                    status_code=404,
                    detail=f"Incident {incident_id} not found"
                )

            # Verify user has access (is tenant or landlord)
            if incident.get('tenant_id') != user_id and incident.get('landlord_id') != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to view this incident"
                )

            logger.info(f"[incidents] ✅ Retrieved incident: {incident_id}")

            return {
                "success": True,
                "incident": incident
            }

        except ClientError as e:
            logger.error(f"[incidents] DynamoDB error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[incidents] ❌ Failed to fetch incident: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
