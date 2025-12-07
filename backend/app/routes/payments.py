"""
STRIPE Payment Processing Backend - Phase 2D FINAL

Complete Stripe integration with 15% platform fee:
1. POST /api/v1/payments/jobs/{job_id}/initiate - Initiate payment for completed job
2. POST /api/v1/payments/webhooks/stripe - Handle Stripe webhook events
3. GET /api/v1/payments/jobs/{job_id}/status - Get payment status for a job
4. POST /api/v1/contractors/stripe/connect - Set up Stripe Connect for contractor
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Body
from typing import List, Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
import stripe
import os
from datetime import datetime
import logging
import hmac
import hashlib

from ..models.payment import Payment, PaymentStatus, PaymentCreate
from ..models.job import JobStatus, PaymentStatus as JobPaymentStatus
from ..deps.auth import verify_firebase_token
from ..deps.dynamo import get_dynamo_resource, table_name

# Configure router
router = APIRouter(prefix="/api/v1", tags=["payments"])

# Configure logging
logger = logging.getLogger(__name__)

# AWS Configuration
dynamodb = get_dynamo_resource()
payments_table = dynamodb.Table(table_name("payments"))
jobs_table = dynamodb.Table(table_name("jobs"))
bids_table = dynamodb.Table(table_name("bids"))
contractors_table = dynamodb.Table(table_name("contractors"))
users_table = dynamodb.Table(table_name("users"))

# Stripe Configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
PLATFORM_FEE_PERCENT = 0.15  # 15% platform fee


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
    return token


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
        logger.error(f"[payments] DynamoDB error fetching job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e.response['Error']['Message']}"
        )


async def get_bid(bid_id: str) -> Dict[str, Any]:
    """
    Fetch bid from DynamoDB.

    Args:
        bid_id: The bid identifier

    Returns:
        Dictionary containing bid data

    Raises:
        HTTPException: If bid not found
    """
    try:
        response = bids_table.scan(
            FilterExpression="bid_id = :bid",
            ExpressionAttributeValues={":bid": bid_id}
        )
        items = response.get('Items', [])
        bid = items[0] if items else None

        if not bid:
            raise HTTPException(
                status_code=404,
                detail=f"Bid {bid_id} not found"
            )

        return bid
    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"[payments] DynamoDB error fetching bid: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e.response['Error']['Message']}"
        )


async def get_contractor(contractor_id: str) -> Dict[str, Any]:
    """
    Fetch contractor from DynamoDB.

    Args:
        contractor_id: The contractor identifier

    Returns:
        Dictionary containing contractor data

    Raises:
        HTTPException: If contractor not found
    """
    try:
        response = contractors_table.scan(
            FilterExpression="contractor_id = :cid",
            ExpressionAttributeValues={":cid": contractor_id}
        )
        items = response.get('Items', [])
        contractor = items[0] if items else None

        if not contractor:
            raise HTTPException(
                status_code=404,
                detail=f"Contractor {contractor_id} not found"
            )

        return contractor
    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"[payments] DynamoDB error fetching contractor: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e.response['Error']['Message']}"
        )


async def get_landlord_stripe_customer(user_id: str) -> str:
    """
    Get or create Stripe customer for landlord.

    Args:
        user_id: The landlord's user ID

    Returns:
        Stripe customer ID
    """
    try:
        # Try to get existing customer from users table
        response = users_table.scan(
            FilterExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        items = response.get('Items', [])
        user = items[0] if items else None

        if user and user.get('stripe_customer_id'):
            return user['stripe_customer_id']

        # Create new Stripe customer
        customer = stripe.Customer.create(
            metadata={'user_id': user_id}
        )

        # Store customer ID in users table
        if user:
            users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="SET stripe_customer_id = :cid",
                ExpressionAttributeValues={':cid': customer.id}
            )
        else:
            # Create user record if it doesn't exist
            users_table.put_item(
                Item={
                    'user_id': user_id,
                    'stripe_customer_id': customer.id,
                    'created_at': datetime.utcnow().isoformat()
                }
            )

        logger.info(f"[payments] Created Stripe customer {customer.id} for user {user_id}")
        return customer.id

    except stripe.error.StripeError as e:
        logger.error(f"[payments] Stripe error creating customer: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Stripe error: {str(e)}"
        )
    except ClientError as e:
        logger.error(f"[payments] DynamoDB error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e.response['Error']['Message']}"
        )


async def update_contractor_stats(contractor_id: str):
    """
    Update contractor statistics after successful payment.

    Args:
        contractor_id: The contractor's ID
    """
    try:
        # Increment completed_jobs count
        contractors_table.update_item(
            Key={'contractor_id': contractor_id},
            UpdateExpression="SET completed_jobs = if_not_exists(completed_jobs, :zero) + :inc, updated_at = :now",
            ExpressionAttributeValues={
                ':inc': 1,
                ':zero': 0,
                ':now': datetime.utcnow().isoformat()
            }
        )
        logger.info(f"[payments] Updated stats for contractor {contractor_id}")

    except ClientError as e:
        logger.error(f"[payments] Error updating contractor stats: {str(e)}")
        # Don't raise - this is a non-critical operation


async def get_payment_by_stripe_intent(stripe_payment_intent_id: str) -> Optional[Dict[str, Any]]:
    """
    Find payment by Stripe PaymentIntent ID.

    Args:
        stripe_payment_intent_id: The Stripe PaymentIntent ID

    Returns:
        Payment record or None
    """
    try:
        response = payments_table.scan(
            FilterExpression="stripe_payment_intent_id = :sid",
            ExpressionAttributeValues={":sid": stripe_payment_intent_id}
        )
        items = response.get('Items', [])
        return items[0] if items else None

    except ClientError as e:
        logger.error(f"[payments] Error fetching payment by intent ID: {str(e)}")
        return None


# ============================================================================
# PAYMENT ENDPOINTS
# ============================================================================

@router.post("/payments/jobs/{job_id}/initiate")
async def initiate_payment(
    job_id: str,
    token: str = Depends(verify_firebase_token)
):
    """
    Initiate payment for a completed job.

    Flow:
    1. Get job and verify landlord owns it
    2. Verify job status is COMPLETED
    3. Get awarded bid amount
    4. Get contractor Stripe account
    5. Calculate platform fee (15%) and contractor payout (85%)
    6. Create Stripe PaymentIntent with transfer to contractor
    7. Create Payment record in DynamoDB
    8. Update job with payment_status and stripe_payment_intent_id
    9. Return payment details and client_secret for frontend

    Args:
        job_id: The job ID to initiate payment for
        token: Auth token (landlord)

    Returns:
        Payment initiation details with client_secret
    """
    try:
        user_id = get_current_user_from_token(token)

        # 1. Get job and verify ownership
        job = await get_job(job_id)

        if job['landlord_id'] != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only the landlord can initiate payment for this job"
            )

        # 2. Verify job status is COMPLETED
        if job['status'] != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job must be COMPLETED to initiate payment. Current status: {job['status']}"
            )

        # Check if payment already initiated
        if job.get('payment_status') in [JobPaymentStatus.PROCESSING, JobPaymentStatus.COMPLETED]:
            raise HTTPException(
                status_code=409,
                detail=f"Payment already {job['payment_status']}"
            )

        # 3. Get awarded bid amount
        awarded_bid_id = job.get('awarded_bid_id')
        if not awarded_bid_id:
            raise HTTPException(
                status_code=400,
                detail="Job has no awarded bid"
            )

        bid = await get_bid(awarded_bid_id)
        gross_amount = float(bid['amount'])

        # 4. Get contractor and verify Stripe account
        contractor_id = job.get('awarded_contractor_id')
        if not contractor_id:
            raise HTTPException(
                status_code=400,
                detail="Job has no assigned contractor"
            )

        contractor = await get_contractor(contractor_id)

        if not contractor.get('stripe_account_id'):
            raise HTTPException(
                status_code=400,
                detail="Contractor has not completed Stripe Connect onboarding"
            )

        if not contractor.get('stripe_onboarding_complete'):
            raise HTTPException(
                status_code=400,
                detail="Contractor Stripe onboarding is incomplete"
            )

        # 5. Calculate amounts
        platform_fee = round(gross_amount * PLATFORM_FEE_PERCENT, 2)
        contractor_payout = round(gross_amount * (1 - PLATFORM_FEE_PERCENT), 2)

        # 6. Get or create Stripe customer for landlord
        landlord_customer_id = await get_landlord_stripe_customer(user_id)

        # 7. Create Stripe PaymentIntent with destination charge
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(gross_amount * 100),  # Convert to cents
                currency='usd',
                customer=landlord_customer_id,
                transfer_data={
                    'destination': contractor['stripe_account_id'],
                    'amount': int(contractor_payout * 100)
                },
                application_fee_amount=int(platform_fee * 100),
                metadata={
                    'job_id': job_id,
                    'bid_id': awarded_bid_id,
                    'contractor_id': contractor_id,
                    'landlord_id': user_id
                },
                description=f"Payment for job: {job.get('title', job_id)}"
            )

            logger.info(f"[payments] Created PaymentIntent {payment_intent.id} for job {job_id}")

        except stripe.error.StripeError as e:
            logger.error(f"[payments] Stripe error creating PaymentIntent: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Stripe error: {str(e)}"
            )

        # 8. Create Payment record
        payment = Payment(
            job_id=job_id,
            bid_id=awarded_bid_id,
            landlord_id=user_id,
            contractor_id=contractor_id,
            gross_amount=gross_amount,
            platform_fee=platform_fee,
            contractor_payout=contractor_payout,
            stripe_payment_intent_id=payment_intent.id,
            status=PaymentStatus.PROCESSING
        )

        try:
            payments_table.put_item(Item=payment.model_dump(mode='json'))
            logger.info(f"[payments] Created payment record {payment.payment_id}")

        except ClientError as e:
            logger.error(f"[payments] Error creating payment record: {str(e)}")
            # Try to cancel the PaymentIntent if DB write fails
            try:
                stripe.PaymentIntent.cancel(payment_intent.id)
            except:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {e.response['Error']['Message']}"
            )

        # 9. Update job status
        try:
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression="SET payment_status = :ps, stripe_payment_intent_id = :sid, updated_at = :now",
                ExpressionAttributeValues={
                    ':ps': JobPaymentStatus.PROCESSING,
                    ':sid': payment_intent.id,
                    ':now': datetime.utcnow().isoformat()
                }
            )

        except ClientError as e:
            logger.error(f"[payments] Error updating job: {str(e)}")
            # Continue - payment is created, just job status update failed

        # 10. Return payment details
        return {
            "success": True,
            "payment_id": payment.payment_id,
            "client_secret": payment_intent.client_secret,
            "amounts": {
                "gross_amount": gross_amount,
                "platform_fee": platform_fee,
                "contractor_payout": contractor_payout
            },
            "status": "processing",
            "stripe_payment_intent_id": payment_intent.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[payments] Unexpected error initiating payment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/payments/webhooks/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.

    Primary event: payment_intent.succeeded

    Flow:
    1. Verify webhook signature
    2. Parse event
    3. Handle payment_intent.succeeded:
       - Get payment by stripe_payment_intent_id
       - Update payment status to COMPLETED
       - Update job status to PAID
       - Update contractor stats
       - (Transfer is automatic via transfer_data in PaymentIntent)
    4. Return 200 OK

    Args:
        request: FastAPI request with webhook payload

    Returns:
        Success response
    """
    try:
        # 1. Get payload and signature
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')

        if not sig_header:
            raise HTTPException(
                status_code=400,
                detail="Missing stripe-signature header"
            )

        # 2. Verify signature and construct event
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"[payments] Invalid webhook payload: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"[payments] Invalid webhook signature: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid signature")

        logger.info(f"[payments] Received webhook event: {event['type']}")

        # 3. Handle payment_intent.succeeded
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            stripe_payment_intent_id = payment_intent['id']

            # Get payment record
            payment = await get_payment_by_stripe_intent(stripe_payment_intent_id)

            if not payment:
                logger.error(f"[payments] Payment not found for intent {stripe_payment_intent_id}")
                # Return 200 to acknowledge webhook even if payment not found
                return {"success": True, "message": "Payment not found but webhook acknowledged"}

            # Check idempotency - if already processed, return success
            if payment.get('status') == PaymentStatus.COMPLETED:
                logger.info(f"[payments] Payment {payment['payment_id']} already completed (idempotent)")
                return {"success": True, "message": "Payment already processed"}

            # Update payment status
            try:
                payments_table.update_item(
                    Key={'payment_id': payment['payment_id']},
                    UpdateExpression="SET #status = :status, completed_at = :now, updated_at = :now",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': PaymentStatus.COMPLETED,
                        ':now': datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"[payments] Updated payment {payment['payment_id']} to COMPLETED")

            except ClientError as e:
                logger.error(f"[payments] Error updating payment status: {str(e)}")
                raise HTTPException(status_code=500, detail="Database error")

            # Update job status to PAID
            job_id = payment.get('job_id')
            if job_id:
                try:
                    jobs_table.update_item(
                        Key={'job_id': job_id},
                        UpdateExpression="SET #status = :status, payment_status = :pstatus, updated_at = :now",
                        ExpressionAttributeNames={'#status': 'status'},
                        ExpressionAttributeValues={
                            ':status': JobStatus.PAID,
                            ':pstatus': JobPaymentStatus.COMPLETED,
                            ':now': datetime.utcnow().isoformat()
                        }
                    )
                    logger.info(f"[payments] Updated job {job_id} to PAID")

                except ClientError as e:
                    logger.error(f"[payments] Error updating job status: {str(e)}")
                    # Don't raise - payment is processed, job update is secondary

            # Update contractor stats
            contractor_id = payment.get('contractor_id')
            if contractor_id:
                await update_contractor_stats(contractor_id)

            logger.info(f"[payments] Successfully processed payment_intent.succeeded for {stripe_payment_intent_id}")

        # Handle other event types (for future expansion)
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            stripe_payment_intent_id = payment_intent['id']

            payment = await get_payment_by_stripe_intent(stripe_payment_intent_id)

            if payment:
                try:
                    payments_table.update_item(
                        Key={'payment_id': payment['payment_id']},
                        UpdateExpression="SET #status = :status, error_message = :error, updated_at = :now",
                        ExpressionAttributeNames={'#status': 'status'},
                        ExpressionAttributeValues={
                            ':status': PaymentStatus.FAILED,
                            ':error': payment_intent.get('last_payment_error', {}).get('message', 'Payment failed'),
                            ':now': datetime.utcnow().isoformat()
                        }
                    )
                    logger.info(f"[payments] Updated payment {payment['payment_id']} to FAILED")

                except ClientError as e:
                    logger.error(f"[payments] Error updating failed payment: {str(e)}")

        # Return success
        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[payments] Webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/jobs/{job_id}/status")
async def get_payment_status(
    job_id: str,
    token: str = Depends(verify_firebase_token)
):
    """
    Get payment status for a job.

    Args:
        job_id: The job ID
        token: Auth token

    Returns:
        Payment status information
    """
    try:
        user_id = get_current_user_from_token(token)

        # Get job to verify access
        job = await get_job(job_id)

        # Verify user is landlord or contractor
        if user_id not in [job['landlord_id'], job.get('awarded_contractor_id')]:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        # Query payments by job_id
        response = payments_table.scan(
            FilterExpression="job_id = :jid",
            ExpressionAttributeValues={":jid": job_id}
        )

        payments = response.get('Items', [])

        if not payments:
            return {
                "status": "not_initiated",
                "job_id": job_id,
                "payment_status": job.get('payment_status', 'pending')
            }

        # Get most recent payment
        payment = sorted(payments, key=lambda x: x.get('created_at', ''), reverse=True)[0]

        return {
            "status": payment.get('status'),
            "payment_id": payment.get('payment_id'),
            "job_id": job_id,
            "gross_amount": payment.get('gross_amount'),
            "platform_fee": payment.get('platform_fee'),
            "contractor_payout": payment.get('contractor_payout'),
            "stripe_payment_intent_id": payment.get('stripe_payment_intent_id'),
            "created_at": payment.get('created_at'),
            "completed_at": payment.get('completed_at'),
            "error_message": payment.get('error_message')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[payments] Error getting payment status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


# ============================================================================
# STRIPE CONNECT ENDPOINTS
# ============================================================================

@router.post("/contractors/stripe/connect")
async def create_stripe_connect_account(
    contractor_id: str = Body(..., embed=True),
    token: str = Depends(verify_firebase_token)
):
    """
    Create Stripe Connect Express account for contractor.

    Flow:
    1. Verify contractor exists
    2. Check if already has Stripe account
    3. Create Stripe Connect Express account
    4. Generate account onboarding link
    5. Update contractor record with stripe_account_id
    6. Return onboarding URL

    Args:
        contractor_id: The contractor's ID
        token: Auth token

    Returns:
        Onboarding URL for contractor to complete Stripe setup
    """
    try:
        user_id = get_current_user_from_token(token)

        # Get contractor
        contractor = await get_contractor(contractor_id)

        # Verify user owns this contractor account
        if contractor['user_id'] != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        # Check if already has Stripe account
        if contractor.get('stripe_account_id') and contractor.get('stripe_onboarding_complete'):
            # Generate login link for existing account
            try:
                login_link = stripe.Account.create_login_link(
                    contractor['stripe_account_id']
                )
                return {
                    "success": True,
                    "onboarding_complete": True,
                    "url": login_link.url,
                    "stripe_account_id": contractor['stripe_account_id']
                }
            except stripe.error.StripeError as e:
                logger.error(f"[payments] Error creating login link: {str(e)}")
                # Continue to create new account if login link fails

        # Create new Stripe Connect Express account
        try:
            account = stripe.Account.create(
                type='express',
                country='US',
                email=contractor.get('email'),
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
                business_type='individual',
                metadata={
                    'contractor_id': contractor_id,
                    'user_id': user_id
                }
            )

            logger.info(f"[payments] Created Stripe Connect account {account.id} for contractor {contractor_id}")

        except stripe.error.StripeError as e:
            logger.error(f"[payments] Stripe error creating account: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Stripe error: {str(e)}"
            )

        # Generate onboarding link
        try:
            # Get return URL from environment or use default
            return_url = os.getenv('STRIPE_RETURN_URL', 'https://landten.app/contractor/dashboard')
            refresh_url = os.getenv('STRIPE_REFRESH_URL', 'https://landten.app/contractor/stripe-connect')

            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )

            logger.info(f"[payments] Generated onboarding link for {account.id}")

        except stripe.error.StripeError as e:
            logger.error(f"[payments] Error creating account link: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Stripe error: {str(e)}"
            )

        # Update contractor record
        try:
            contractors_table.update_item(
                Key={'contractor_id': contractor_id},
                UpdateExpression="SET stripe_account_id = :sid, updated_at = :now",
                ExpressionAttributeValues={
                    ':sid': account.id,
                    ':now': datetime.utcnow().isoformat()
                }
            )

        except ClientError as e:
            logger.error(f"[payments] Error updating contractor: {str(e)}")
            # Don't raise - account is created, just DB update failed

        return {
            "success": True,
            "onboarding_complete": False,
            "url": account_link.url,
            "stripe_account_id": account.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[payments] Error setting up Stripe Connect: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/contractors/stripe/webhook")
async def stripe_connect_webhook(request: Request):
    """
    Handle Stripe Connect webhook events (account.updated, etc.).

    This endpoint can be used to track when contractors complete onboarding.

    Args:
        request: FastAPI request with webhook payload

    Returns:
        Success response
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')

        if not sig_header:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")

        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            logger.error(f"[payments] Webhook verification failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

        # Handle account.updated event
        if event['type'] == 'account.updated':
            account = event['data']['object']
            account_id = account['id']

            # Check if charges are enabled (onboarding complete)
            charges_enabled = account.get('charges_enabled', False)

            if charges_enabled:
                # Find contractor by stripe_account_id and update
                try:
                    response = contractors_table.scan(
                        FilterExpression="stripe_account_id = :sid",
                        ExpressionAttributeValues={":sid": account_id}
                    )

                    contractors = response.get('Items', [])

                    if contractors:
                        contractor = contractors[0]
                        contractors_table.update_item(
                            Key={'contractor_id': contractor['contractor_id']},
                            UpdateExpression="SET stripe_onboarding_complete = :complete, updated_at = :now",
                            ExpressionAttributeValues={
                                ':complete': True,
                                ':now': datetime.utcnow().isoformat()
                            }
                        )
                        logger.info(f"[payments] Contractor {contractor['contractor_id']} completed Stripe onboarding")

                except ClientError as e:
                    logger.error(f"[payments] Error updating contractor onboarding status: {str(e)}")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[payments] Connect webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
