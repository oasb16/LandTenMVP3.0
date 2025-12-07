"""
LANDLORD Job Creation and Bid Management Backend - Phase 2B

Complete backend API for landlord job posting and contractor bidding:
1. POST /api/v1/jobs/ - Create job from incident
2. GET /api/v1/jobs/{job_id}/bids - Get all bids for a job
3. POST /api/v1/jobs/{job_id}/award/{bid_id} - Award job to contractor
4. GET /api/v1/jobs/landlord/my-jobs - Get all landlord's jobs
5. GET /api/v1/jobs/available - Get available jobs for contractors
6. POST /api/v1/jobs/{job_id}/bid - Submit bid on a job
7. GET /api/v1/jobs/contractor/my-bids - Get all contractor's bids
8. GET /api/v1/jobs/contractor/active-jobs - Get active jobs for contractor
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
import uuid
from datetime import datetime
import logging
import os

from ..models.job import Job, JobStatus, JobCreate
from ..models.bid import Bid, BidStatus, BidCreate
from ..models.incident import IncidentStatus
from ..deps.auth import verify_firebase_token
from ..deps.dynamo import get_dynamo_resource, table_name

# Configure router
router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

# Configure logging
logger = logging.getLogger(__name__)

# AWS Configuration
dynamodb = get_dynamo_resource()
jobs_table = dynamodb.Table(table_name("jobs"))
bids_table = dynamodb.Table(table_name("bids"))
contractors_table = dynamodb.Table(table_name("contractors"))
incidents_table = dynamodb.Table(table_name("incidents"))


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


async def get_incident(incident_id: str) -> Dict[str, Any]:
    """
    Fetch incident from DynamoDB.

    Args:
        incident_id: The incident identifier

    Returns:
        Dictionary containing incident data

    Raises:
        HTTPException: If incident not found
    """
    try:
        # Scan to find incident by incident_id (in production, use GSI)
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

        return incident
    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"[jobs] DynamoDB error fetching incident: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e.response['Error']['Message']}"
        )


async def get_job(job_id: str) -> Dict[str, Any]:
    """
    Fetch job from DynamoDB.

    Args:
        job_id: The job identifier

    Returns:
        Dictionary containing job data

    Raises:
        HTTPException: If job not found
    """
    try:
        # Scan to find job by job_id (in production, use GSI)
        response = jobs_table.scan(
            FilterExpression="job_id = :jid",
            ExpressionAttributeValues={":jid": job_id}
        )
        items = response.get('Items', [])
        job = items[0] if items else None

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        return job
    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"[jobs] DynamoDB error fetching job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e.response['Error']['Message']}"
        )


async def get_contractor_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetch contractor profile from DynamoDB.

    Args:
        user_id: The user identifier

    Returns:
        Dictionary containing contractor profile

    Raises:
        HTTPException: If contractor not found
    """
    try:
        # Scan to find contractor by user_id (in production, use GSI)
        response = contractors_table.scan(
            FilterExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        items = response.get('Items', [])
        contractor = items[0] if items else None

        if not contractor:
            raise HTTPException(
                status_code=404,
                detail=f"Contractor profile not found for user {user_id}"
            )

        return contractor
    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"[jobs] DynamoDB error fetching contractor: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e.response['Error']['Message']}"
        )


async def notify_matching_contractors(job: Dict[str, Any]):
    """
    Find and notify contractors matching job category.

    Args:
        job: Job dictionary with category and location
    """
    try:
        job_category = job.get('category')

        # Scan contractors table to find matches
        # TODO: Add GSI for efficient category lookups
        # TODO: Filter by service_zip_codes matching property location
        response = contractors_table.scan()
        contractors = response.get('Items', [])

        matching_contractors = []
        for contractor in contractors:
            categories = contractor.get('categories', [])
            # Check if contractor handles this category
            if job_category in categories:
                # Check if contractor is active
                if contractor.get('status') == 'active':
                    matching_contractors.append(contractor)

        logger.info(f"[jobs] Found {len(matching_contractors)} matching contractors for job {job.get('job_id')}")

        # Send notification to each matching contractor
        for contractor in matching_contractors:
            await send_notification(
                contractor.get('user_id'),
                "new_job_available",
                {
                    "job_id": job.get('job_id'),
                    "title": job.get('title'),
                    "category": job.get('category'),
                    "urgency": job.get('urgency'),
                    "budget_min": job.get('budget_min'),
                    "budget_max": job.get('budget_max')
                }
            )

    except Exception as e:
        # Don't fail the job creation if notifications fail
        logger.error(f"[jobs] Error notifying contractors: {str(e)}")


async def create_job_chat_channel(job_id: str, landlord_id: str, tenant_id: str, contractor_id: str):
    """
    Create Stream Chat channel for job communication.

    Args:
        job_id: Job identifier
        landlord_id: Landlord user ID
        tenant_id: Tenant user ID
        contractor_id: Contractor user ID
    """
    # TODO: Integrate with Stream Chat
    # For now, just log the intent
    logger.info(
        f"[jobs] STUB: Create chat channel for job {job_id} with "
        f"landlord={landlord_id}, tenant={tenant_id}, contractor={contractor_id}"
    )
    print(
        f"CHAT CHANNEL STUB: job={job_id} members=[{landlord_id}, {tenant_id}, {contractor_id}]"
    )


async def send_notification(user_id: str, notification_type: str, data: Dict[str, Any]):
    """
    Send notification to user (stub for now - will integrate with Pusher/Stream later).

    Args:
        user_id: User to notify
        notification_type: Type of notification
        data: Notification payload data
    """
    # TODO: Integrate with Pusher or Stream Chat for real-time notifications
    logger.info(
        f"[jobs] NOTIFICATION: {notification_type} to {user_id}: {data}"
    )
    print(f"NOTIFICATION: {notification_type} to {user_id}: {data}")


# ============================================================================
# LANDLORD ENDPOINT 1: CREATE JOB FROM INCIDENT
# ============================================================================

@router.post("/")
async def create_job(
    incident_id: str = Body(...),
    budget_min: Optional[float] = Body(None),
    budget_max: Optional[float] = Body(None),
    additional_notes: Optional[str] = Body(None),
    current_user: str = Depends(verify_firebase_token)
):
    """
    Create a job from an incident.

    Flow:
    1. Get incident from DynamoDB, verify landlord_id matches current_user
    2. Create Job from incident data
    3. Combine incident description + discovery_data + additional_notes
    4. Set status = POSTED
    5. Save job to DynamoDB
    6. Update incident: job_id = new_job_id, status = job_created
    7. Find matching contractors
    8. Notify all matching contractors
    9. Return created job

    Returns:
        Created job data
    """
    logger.info(f"[jobs] Creating job from incident | incident_id={incident_id}")

    try:
        # Get current user ID
        landlord_id = get_current_user_from_token(current_user)

        # Fetch incident
        incident = await get_incident(incident_id)

        # Verify landlord owns this incident
        if incident.get('landlord_id') != landlord_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to create a job from this incident"
            )

        # Check if job already created for this incident
        if incident.get('job_id'):
            raise HTTPException(
                status_code=409,
                detail=f"Job already created for this incident: {incident.get('job_id')}"
            )

        # Generate job ID
        job_id = f"job_{uuid.uuid4().hex[:12]}"

        # Build comprehensive description
        description_parts = [incident.get('description', '')]

        # Add discovery data if available
        discovery_data = incident.get('discovery_data')
        if discovery_data:
            description_parts.append("\n\n--- ADDITIONAL DETAILS ---")
            for key, value in discovery_data.items():
                description_parts.append(f"{key}: {value}")

        # Add landlord's additional notes
        if additional_notes:
            description_parts.append(f"\n\n--- LANDLORD NOTES ---\n{additional_notes}")

        full_description = "\n".join(description_parts)

        # Create job record
        now = datetime.utcnow()
        job_data = {
            # Identifiers
            "user_id": landlord_id,  # Partition key for landlord queries
            "job_id": job_id,
            "incident_id": incident_id,
            "property_id": incident.get('property_id'),
            "landlord_id": landlord_id,
            "tenant_id": incident.get('tenant_id'),

            # Job details
            "title": incident.get('title'),
            "description": full_description,
            "category": incident.get('category'),
            "urgency": incident.get('urgency'),

            # Budget
            "budget_min": budget_min,
            "budget_max": budget_max,

            # Status
            "status": JobStatus.POSTED.value,

            # Contractor assignment (none yet)
            "awarded_contractor_id": None,
            "awarded_bid_id": None,

            # Scheduling
            "scheduled_date": None,
            "completion_date": None,

            # Completion
            "completion_photos": [],
            "completion_notes": None,

            # Payment
            "payment_status": "pending",
            "stripe_payment_intent_id": None,
            "final_amount": None,

            # Timestamps
            "created_at": now.isoformat() + "Z",
            "updated_at": now.isoformat() + "Z",
            "awarded_at": None,

            # Metadata
            "bid_count": 0,
            "notes": additional_notes
        }

        # Save job to DynamoDB
        try:
            jobs_table.put_item(Item=job_data)
            logger.info(f"[jobs] ✅ Job created: {job_id}")
        except ClientError as e:
            logger.error(f"[jobs] DynamoDB error creating job: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save job to database: {e.response['Error']['Message']}"
            )

        # Update incident with job_id and status
        try:
            incidents_table.update_item(
                Key={
                    "user_id": incident.get('user_id'),
                    "incident_id": incident_id
                },
                UpdateExpression="SET job_id = :job_id, #status = :status, updated_at = :updated_at",
                ExpressionAttributeNames={
                    "#status": "status"  # 'status' is a reserved word in DynamoDB
                },
                ExpressionAttributeValues={
                    ":job_id": job_id,
                    ":status": "job_created",
                    ":updated_at": now.isoformat() + "Z"
                }
            )
            logger.info(f"[jobs] ✅ Incident updated with job_id: {incident_id}")
        except ClientError as e:
            logger.error(f"[jobs] Failed to update incident: {str(e)}")
            # Don't fail the job creation if incident update fails

        # Notify matching contractors (async, non-blocking)
        await notify_matching_contractors(job_data)

        return {
            "success": True,
            "job": job_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[jobs] ❌ Failed to create job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# LANDLORD ENDPOINT 2: GET BIDS FOR JOB
# ============================================================================

@router.get("/{job_id}/bids")
async def get_job_bids(
    job_id: str,
    current_user: str = Depends(verify_firebase_token)
):
    """
    Get all bids for a specific job.

    Flow:
    1. Get job, verify landlord owns it
    2. Query bids table with job_id
    3. Sort by: amount (ascending), contractor_rating (descending)
    4. Return sorted bids array

    Returns:
        List of bids sorted by amount and rating
    """
    logger.info(f"[jobs] Fetching bids for job: {job_id}")

    try:
        # Get current user ID
        landlord_id = get_current_user_from_token(current_user)

        # Fetch job
        job = await get_job(job_id)

        # Verify landlord owns this job
        if job.get('landlord_id') != landlord_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view bids for this job"
            )

        # Query bids by job_id
        # Note: In production, use GSI on job_id for efficient queries
        try:
            response = bids_table.scan(
                FilterExpression="job_id = :jid",
                ExpressionAttributeValues={":jid": job_id}
            )
            bids = response.get('Items', [])

            # Handle pagination if there are more items
            while 'LastEvaluatedKey' in response:
                response = bids_table.scan(
                    FilterExpression="job_id = :jid",
                    ExpressionAttributeValues={":jid": job_id},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                bids.extend(response.get('Items', []))

            # Sort by amount (ascending), then by contractor rating (descending)
            bids.sort(
                key=lambda x: (
                    float(x.get('amount', float('inf'))),
                    -float(x.get('contractor_rating', 0))
                )
            )

            logger.info(f"[jobs] ✅ Found {len(bids)} bids for job {job_id}")

            return {
                "success": True,
                "count": len(bids),
                "bids": bids
            }

        except ClientError as e:
            logger.error(f"[jobs] DynamoDB error fetching bids: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[jobs] ❌ Failed to fetch bids: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# LANDLORD ENDPOINT 3: AWARD JOB TO CONTRACTOR
# ============================================================================

@router.post("/{job_id}/award/{bid_id}")
async def award_job(
    job_id: str,
    bid_id: str,
    current_user: str = Depends(verify_firebase_token)
):
    """
    Award a job to a contractor by accepting their bid.

    Flow:
    1. Get job and bid, verify ownership
    2. Update job: status = AWARDED, awarded_contractor_id, awarded_bid_id
    3. Update winning bid: status = ACCEPTED
    4. Update all other bids: status = REJECTED
    5. Create Stream Chat channel for job (landlord + tenant + contractor)
    6. Notify contractor they won
    7. Return success with contractor_id

    Returns:
        Success status with awarded contractor info
    """
    logger.info(f"[jobs] Awarding job {job_id} to bid {bid_id}")

    try:
        # Get current user ID
        landlord_id = get_current_user_from_token(current_user)

        # Fetch job
        job = await get_job(job_id)

        # Verify landlord owns this job
        if job.get('landlord_id') != landlord_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to award this job"
            )

        # Check if job is already awarded
        if job.get('status') == JobStatus.AWARDED.value:
            raise HTTPException(
                status_code=409,
                detail=f"Job already awarded to contractor {job.get('awarded_contractor_id')}"
            )

        # Fetch the winning bid
        try:
            response = bids_table.scan(
                FilterExpression="bid_id = :bid",
                ExpressionAttributeValues={":bid": bid_id}
            )
            items = response.get('Items', [])
            winning_bid = items[0] if items else None

            if not winning_bid:
                raise HTTPException(
                    status_code=404,
                    detail=f"Bid {bid_id} not found"
                )

            # Verify bid is for this job
            if winning_bid.get('job_id') != job_id:
                raise HTTPException(
                    status_code=400,
                    detail="Bid does not belong to this job"
                )

        except HTTPException:
            raise
        except ClientError as e:
            logger.error(f"[jobs] DynamoDB error fetching bid: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

        contractor_id = winning_bid.get('contractor_id')
        final_amount = winning_bid.get('amount')
        now = datetime.utcnow()

        # Update job with award details
        try:
            jobs_table.update_item(
                Key={
                    "user_id": job.get('user_id'),
                    "job_id": job_id
                },
                UpdateExpression=(
                    "SET #status = :status, "
                    "awarded_contractor_id = :contractor_id, "
                    "awarded_bid_id = :bid_id, "
                    "awarded_at = :awarded_at, "
                    "final_amount = :final_amount, "
                    "updated_at = :updated_at"
                ),
                ExpressionAttributeNames={
                    "#status": "status"
                },
                ExpressionAttributeValues={
                    ":status": JobStatus.AWARDED.value,
                    ":contractor_id": contractor_id,
                    ":bid_id": bid_id,
                    ":awarded_at": now.isoformat() + "Z",
                    ":final_amount": final_amount,
                    ":updated_at": now.isoformat() + "Z"
                }
            )
            logger.info(f"[jobs] ✅ Job awarded: {job_id} → contractor {contractor_id}")
        except ClientError as e:
            logger.error(f"[jobs] Failed to update job: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to award job: {e.response['Error']['Message']}"
            )

        # Update winning bid status
        try:
            bids_table.update_item(
                Key={
                    "user_id": winning_bid.get('user_id'),
                    "bid_id": bid_id
                },
                UpdateExpression="SET #status = :status, reviewed_at = :reviewed_at, updated_at = :updated_at",
                ExpressionAttributeNames={
                    "#status": "status"
                },
                ExpressionAttributeValues={
                    ":status": BidStatus.ACCEPTED.value,
                    ":reviewed_at": now.isoformat() + "Z",
                    ":updated_at": now.isoformat() + "Z"
                }
            )
            logger.info(f"[jobs] ✅ Bid accepted: {bid_id}")
        except ClientError as e:
            logger.error(f"[jobs] Failed to update winning bid: {str(e)}")
            # Don't fail the entire operation if this fails

        # Reject all other bids for this job
        try:
            # Fetch all bids for this job
            response = bids_table.scan(
                FilterExpression="job_id = :jid",
                ExpressionAttributeValues={":jid": job_id}
            )
            all_bids = response.get('Items', [])

            # Update all non-winning bids to REJECTED
            for bid in all_bids:
                if bid.get('bid_id') != bid_id:
                    try:
                        bids_table.update_item(
                            Key={
                                "user_id": bid.get('user_id'),
                                "bid_id": bid.get('bid_id')
                            },
                            UpdateExpression=(
                                "SET #status = :status, "
                                "reviewed_at = :reviewed_at, "
                                "status_reason = :reason, "
                                "updated_at = :updated_at"
                            ),
                            ExpressionAttributeNames={
                                "#status": "status"
                            },
                            ExpressionAttributeValues={
                                ":status": BidStatus.REJECTED.value,
                                ":reviewed_at": now.isoformat() + "Z",
                                ":reason": "Another contractor was selected",
                                ":updated_at": now.isoformat() + "Z"
                            }
                        )
                    except ClientError as e:
                        logger.error(f"[jobs] Failed to reject bid {bid.get('bid_id')}: {str(e)}")
                        # Continue processing other bids

            logger.info(f"[jobs] ✅ Rejected {len(all_bids) - 1} losing bids")

        except ClientError as e:
            logger.error(f"[jobs] Error rejecting losing bids: {str(e)}")
            # Don't fail the entire operation if this fails

        # Create chat channel (stub for now)
        await create_job_chat_channel(
            job_id=job_id,
            landlord_id=landlord_id,
            tenant_id=job.get('tenant_id'),
            contractor_id=contractor_id
        )

        # Notify contractor they won
        await send_notification(
            contractor_id,
            "bid_accepted",
            {
                "job_id": job_id,
                "bid_id": bid_id,
                "title": job.get('title'),
                "final_amount": final_amount,
                "landlord_id": landlord_id
            }
        )

        return {
            "success": True,
            "message": "Job awarded successfully",
            "job_id": job_id,
            "contractor_id": contractor_id,
            "bid_id": bid_id,
            "final_amount": final_amount
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[jobs] ❌ Failed to award job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# LANDLORD ENDPOINT 4: GET MY JOBS
# ============================================================================

@router.get("/landlord/my-jobs")
async def get_my_jobs(
    current_user: str = Depends(verify_firebase_token)
):
    """
    Get all jobs for the current landlord.

    Flow:
    1. Query jobs table with landlord_id
    2. Return all jobs sorted by created_at descending

    Returns:
        List of jobs for the landlord
    """
    logger.info(f"[jobs] Fetching jobs for landlord: {current_user}")

    try:
        # Get landlord user ID
        landlord_id = get_current_user_from_token(current_user)

        # Query jobs by user_id (partition key for landlord queries)
        try:
            response = jobs_table.query(
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": landlord_id}
            )

            jobs = response.get('Items', [])

            # Handle pagination if there are more items
            while 'LastEvaluatedKey' in response:
                response = jobs_table.query(
                    KeyConditionExpression="user_id = :uid",
                    ExpressionAttributeValues={":uid": landlord_id},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                jobs.extend(response.get('Items', []))

            # Sort by created_at descending
            jobs.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )

            logger.info(f"[jobs] ✅ Found {len(jobs)} jobs for landlord {landlord_id}")

            return {
                "success": True,
                "count": len(jobs),
                "jobs": jobs
            }

        except ClientError as e:
            logger.error(f"[jobs] DynamoDB query error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[jobs] ❌ Failed to fetch jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# CONTRACTOR ENDPOINT 5: GET AVAILABLE JOBS
# ============================================================================

@router.get("/available")
async def get_available_jobs(
    current_user: str = Depends(verify_firebase_token)
):
    """
    Get available jobs matching contractor's categories.

    Flow:
    1. Get current user's contractor profile
    2. Scan jobs table where status IN (POSTED, BIDDING)
    3. Filter by contractor's categories
    4. TODO: Add geospatial filtering by zip codes
    5. Return matching jobs

    Returns:
        List of available jobs matching contractor's skills
    """
    logger.info(f"[jobs] Fetching available jobs for contractor: {current_user}")

    try:
        # Get contractor user ID
        user_id = get_current_user_from_token(current_user)

        # Fetch contractor profile
        contractor = await get_contractor_profile(user_id)
        contractor_categories = contractor.get('categories', [])

        if not contractor_categories:
            logger.warning(f"[jobs] Contractor {user_id} has no categories configured")
            return {
                "success": True,
                "count": 0,
                "jobs": []
            }

        # Scan jobs table for POSTED or BIDDING jobs
        # TODO: Use GSI for efficient status queries
        try:
            response = jobs_table.scan()
            all_jobs = response.get('Items', [])

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = jobs_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                all_jobs.extend(response.get('Items', []))

            # Filter jobs
            available_jobs = []
            for job in all_jobs:
                # Check status
                job_status = job.get('status')
                if job_status not in [JobStatus.POSTED.value, JobStatus.BIDDING.value]:
                    continue

                # Check category match
                job_category = job.get('category')
                if job_category not in contractor_categories:
                    continue

                # TODO: Filter by service_zip_codes
                # For now, include all category-matched jobs
                available_jobs.append(job)

            # Sort by created_at descending (newest first)
            available_jobs.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )

            logger.info(
                f"[jobs] ✅ Found {len(available_jobs)} available jobs for contractor {user_id} "
                f"(categories: {contractor_categories})"
            )

            return {
                "success": True,
                "count": len(available_jobs),
                "jobs": available_jobs
            }

        except ClientError as e:
            logger.error(f"[jobs] DynamoDB scan error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[jobs] ❌ Failed to fetch available jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# CONTRACTOR ENDPOINT 6: SUBMIT BID
# ============================================================================

@router.post("/{job_id}/bid")
async def submit_bid(
    job_id: str,
    amount: float = Body(..., gt=0),
    estimated_hours: Optional[float] = Body(None, gt=0),
    proposed_start_date: Optional[str] = Body(None),
    materials_cost: Optional[float] = Body(None, ge=0),
    labor_cost: Optional[float] = Body(None, ge=0),
    description: str = Body(...),
    notes: Optional[str] = Body(None),
    estimated_completion_days: Optional[int] = Body(None, gt=0),
    current_user: str = Depends(verify_firebase_token)
):
    """
    Submit a bid on a job.

    Flow:
    1. Get contractor profile from user_id
    2. Verify job exists and is accepting bids
    3. Create Bid with contractor details
    4. Save bid to DynamoDB
    5. Update job status to BIDDING (if was POSTED)
    6. Notify landlord of new bid
    7. Return created bid

    Returns:
        Created bid data
    """
    logger.info(f"[jobs] Contractor submitting bid on job {job_id}")

    try:
        # Get contractor user ID
        user_id = get_current_user_from_token(current_user)

        # Fetch contractor profile
        contractor = await get_contractor_profile(user_id)
        contractor_id = contractor.get('contractor_id')

        # Fetch job
        job = await get_job(job_id)

        # Verify job is accepting bids
        job_status = job.get('status')
        if job_status not in [JobStatus.POSTED.value, JobStatus.BIDDING.value]:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not accepting bids (current status: {job_status})"
            )

        # Check if job is already awarded
        if job_status == JobStatus.AWARDED.value:
            raise HTTPException(
                status_code=409,
                detail="Job has already been awarded to another contractor"
            )

        # Check if contractor already bid on this job
        try:
            response = bids_table.scan(
                FilterExpression="job_id = :jid AND contractor_id = :cid",
                ExpressionAttributeValues={
                    ":jid": job_id,
                    ":cid": contractor_id
                }
            )
            existing_bids = response.get('Items', [])
            if existing_bids:
                raise HTTPException(
                    status_code=409,
                    detail="You have already submitted a bid for this job"
                )
        except HTTPException:
            raise
        except ClientError as e:
            logger.error(f"[jobs] Error checking existing bids: {str(e)}")
            # Continue anyway

        # Generate bid ID
        bid_id = f"bid_{uuid.uuid4().hex[:12]}"

        # Parse proposed_start_date if provided
        proposed_start_datetime = None
        if proposed_start_date:
            try:
                proposed_start_datetime = datetime.fromisoformat(proposed_start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid proposed_start_date format. Use ISO 8601 format."
                )

        # Create bid record
        now = datetime.utcnow()
        bid_data = {
            # Identifiers
            "user_id": contractor_id,  # Partition key for contractor queries
            "bid_id": bid_id,
            "job_id": job_id,
            "contractor_id": contractor_id,

            # Contractor info (denormalized)
            "contractor_name": contractor.get('business_name'),
            "contractor_rating": contractor.get('rating'),
            "contractor_jobs_completed": contractor.get('completed_jobs', 0),

            # Pricing breakdown
            "amount": amount,
            "materials_cost": materials_cost,
            "labor_cost": labor_cost,

            # Timeline
            "estimated_hours": estimated_hours,
            "proposed_start_date": proposed_start_datetime.isoformat() + "Z" if proposed_start_datetime else None,
            "estimated_completion_days": estimated_completion_days,

            # Proposal details
            "description": description,
            "notes": notes,

            # Status
            "status": BidStatus.SUBMITTED.value,

            # Timestamps
            "created_at": now.isoformat() + "Z",
            "updated_at": now.isoformat() + "Z",
            "reviewed_at": None,

            # Rejection/withdrawal reason
            "status_reason": None
        }

        # Save bid to DynamoDB
        try:
            bids_table.put_item(Item=bid_data)
            logger.info(f"[jobs] ✅ Bid created: {bid_id}")
        except ClientError as e:
            logger.error(f"[jobs] DynamoDB error creating bid: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save bid to database: {e.response['Error']['Message']}"
            )

        # Update job status to BIDDING and increment bid_count
        try:
            jobs_table.update_item(
                Key={
                    "user_id": job.get('user_id'),
                    "job_id": job_id
                },
                UpdateExpression=(
                    "SET #status = :status, "
                    "bid_count = if_not_exists(bid_count, :zero) + :one, "
                    "updated_at = :updated_at"
                ),
                ExpressionAttributeNames={
                    "#status": "status"
                },
                ExpressionAttributeValues={
                    ":status": JobStatus.BIDDING.value,
                    ":zero": 0,
                    ":one": 1,
                    ":updated_at": now.isoformat() + "Z"
                }
            )
            logger.info(f"[jobs] ✅ Job updated to BIDDING status: {job_id}")
        except ClientError as e:
            logger.error(f"[jobs] Failed to update job: {str(e)}")
            # Don't fail the bid creation if job update fails

        # Notify landlord of new bid
        landlord_id = job.get('landlord_id')
        if landlord_id:
            await send_notification(
                landlord_id,
                "new_bid_received",
                {
                    "job_id": job_id,
                    "bid_id": bid_id,
                    "contractor_name": contractor.get('business_name'),
                    "amount": amount,
                    "contractor_rating": contractor.get('rating')
                }
            )

        return {
            "success": True,
            "bid": bid_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[jobs] ❌ Failed to submit bid: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# CONTRACTOR ENDPOINT 7: GET MY BIDS
# ============================================================================

@router.get("/contractor/my-bids")
async def get_my_bids(
    current_user: str = Depends(verify_firebase_token)
):
    """
    Get all bids for the current contractor.

    Flow:
    1. Get contractor_id from user
    2. Query bids table with contractor_id
    3. Return all bids

    Returns:
        List of bids submitted by the contractor
    """
    logger.info(f"[jobs] Fetching bids for contractor: {current_user}")

    try:
        # Get contractor user ID
        user_id = get_current_user_from_token(current_user)

        # Fetch contractor profile to get contractor_id
        contractor = await get_contractor_profile(user_id)
        contractor_id = contractor.get('contractor_id')

        # Query bids by user_id (partition key for contractor queries)
        try:
            response = bids_table.query(
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": contractor_id}
            )

            bids = response.get('Items', [])

            # Handle pagination if there are more items
            while 'LastEvaluatedKey' in response:
                response = bids_table.query(
                    KeyConditionExpression="user_id = :uid",
                    ExpressionAttributeValues={":uid": contractor_id},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                bids.extend(response.get('Items', []))

            # Sort by created_at descending
            bids.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )

            logger.info(f"[jobs] ✅ Found {len(bids)} bids for contractor {contractor_id}")

            return {
                "success": True,
                "count": len(bids),
                "bids": bids
            }

        except ClientError as e:
            logger.error(f"[jobs] DynamoDB query error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[jobs] ❌ Failed to fetch bids: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# CONTRACTOR ENDPOINT 8: GET ACTIVE JOBS
# ============================================================================

@router.get("/contractor/active-jobs")
async def get_active_jobs(
    current_user: str = Depends(verify_firebase_token)
):
    """
    Get active jobs awarded to the current contractor.

    Flow:
    1. Get contractor_id from user
    2. Scan jobs table where awarded_contractor_id = contractor_id
    3. Return active jobs

    Returns:
        List of jobs awarded to the contractor
    """
    logger.info(f"[jobs] Fetching active jobs for contractor: {current_user}")

    try:
        # Get contractor user ID
        user_id = get_current_user_from_token(current_user)

        # Fetch contractor profile to get contractor_id
        contractor = await get_contractor_profile(user_id)
        contractor_id = contractor.get('contractor_id')

        # Scan jobs table for jobs awarded to this contractor
        # TODO: Use GSI on awarded_contractor_id for efficient queries
        try:
            response = jobs_table.scan(
                FilterExpression="awarded_contractor_id = :cid",
                ExpressionAttributeValues={":cid": contractor_id}
            )

            jobs = response.get('Items', [])

            # Handle pagination if there are more items
            while 'LastEvaluatedKey' in response:
                response = jobs_table.scan(
                    FilterExpression="awarded_contractor_id = :cid",
                    ExpressionAttributeValues={":cid": contractor_id},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                jobs.extend(response.get('Items', []))

            # Sort by awarded_at descending (most recent first)
            jobs.sort(
                key=lambda x: x.get('awarded_at', ''),
                reverse=True
            )

            logger.info(f"[jobs] ✅ Found {len(jobs)} active jobs for contractor {contractor_id}")

            return {
                "success": True,
                "count": len(jobs),
                "jobs": jobs
            }

        except ClientError as e:
            logger.error(f"[jobs] DynamoDB scan error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[jobs] ❌ Failed to fetch active jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
