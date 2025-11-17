from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ..deps.auth import verify_firebase_token
from ..repos.contractor_repo import ContractorRepo
from ..repos.job_bid_repo import JobBidRepo
from ..repos.schedule_repo import ScheduleRepo
from ..services.stripe_service import StripeService

router = APIRouter()


class ContractorProfile(BaseModel):
    contractor_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    skills: List[str] = []
    documents: List[Dict[str, Any]] = []
    biography: Optional[str] = None
    stripe_account_id: Optional[str] = None
    bank_account_last4: Optional[str] = None
    bank_account_status: Optional[str] = None
    payment_enabled: bool = False


class AvailabilityEntry(BaseModel):
    contractor_id: str
    start: str
    end: str
    note: Optional[str] = None


class BankAccountDetails(BaseModel):
    contractor_id: str
    account_number: str
    routing_number: str
    account_holder_name: str
    account_holder_type: str = "individual"


class PaymentRequest(BaseModel):
    contractor_id: str
    amount: float  # Amount in dollars
    description: str
    job_id: Optional[str] = None
    incident_id: Optional[str] = None


@router.get("/contractor/profile/{contractor_id}")
def get_contractor_profile(contractor_id: str, token: str = Depends(verify_firebase_token)):
    item = ContractorRepo().get_profile(contractor_id)
    if not item:
        return {"contractor_id": contractor_id, "profile": None}
    return {"contractor_id": contractor_id, "profile": item}


@router.post("/contractor/profile")
def upsert_contractor_profile(profile: ContractorProfile, token: str = Depends(verify_firebase_token)):
    ContractorRepo().upsert_profile(profile.model_dump())
    return {"status": "saved", "profile": profile}


@router.get("/contractor/bids/{contractor_id}")
def list_contractor_bids(contractor_id: str, token: str = Depends(verify_firebase_token)):
    bids = JobBidRepo().list_for_contractor(contractor_id)
    return {"contractor_id": contractor_id, "bids": bids}


@router.post("/contractor/availability")
def add_availability(entry: AvailabilityEntry, token: str = Depends(verify_firebase_token)):
    schedule_id = f"slot-{uuid4().hex[:8]}"
    ScheduleRepo().add_entry(
        entry.contractor_id,
        schedule_id,
        {"start": entry.start, "end": entry.end, "note": entry.note or ""},
    )
    return {"status": "saved", "schedule_id": schedule_id}


@router.get("/contractor/availability/{contractor_id}")
def list_availability(contractor_id: str, token: str = Depends(verify_firebase_token)):
    slots = ScheduleRepo().list_entries(contractor_id)
    return {"contractor_id": contractor_id, "availability": slots}


@router.post("/contractor/bank-account")
def add_bank_account(details: BankAccountDetails, token: str = Depends(verify_firebase_token)):
    """
    Add or update bank account details for a contractor.
    Creates a Stripe Connect account if needed and adds the bank account.
    """
    try:
        repo = ContractorRepo()
        profile = repo.get_profile(details.contractor_id)

        if not profile:
            raise HTTPException(status_code=404, detail="Contractor profile not found")

        stripe_service = StripeService()

        # Create Stripe account if it doesn't exist
        if not profile.get("stripe_account_id"):
            email = profile.get("email")
            name = profile.get("name")

            if not email:
                raise HTTPException(status_code=400, detail="Contractor email is required")

            account_result = stripe_service.create_express_account(
                email=email,
                contractor_id=details.contractor_id,
                name=name
            )

            profile["stripe_account_id"] = account_result["account_id"]

        # Add bank account to Stripe
        bank_result = stripe_service.add_external_bank_account(
            account_id=profile["stripe_account_id"],
            account_number=details.account_number,
            routing_number=details.routing_number,
            account_holder_name=details.account_holder_name,
            account_holder_type=details.account_holder_type
        )

        # Update profile with bank account info
        profile["bank_account_last4"] = bank_result["last4"]
        profile["bank_account_status"] = bank_result["status"]
        profile["payment_enabled"] = True

        repo.upsert_profile(profile)

        return {
            "status": "success",
            "contractor_id": details.contractor_id,
            "bank_account_last4": bank_result["last4"],
            "bank_name": bank_result.get("bank_name"),
            "payment_enabled": True
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add bank account: {str(e)}")


@router.get("/contractor/payment-info/{contractor_id}")
def get_payment_info(contractor_id: str, token: str = Depends(verify_firebase_token)):
    """
    Get payment information for a contractor (without sensitive details).
    """
    profile = ContractorRepo().get_profile(contractor_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Contractor profile not found")

    return {
        "contractor_id": contractor_id,
        "payment_enabled": profile.get("payment_enabled", False),
        "bank_account_last4": profile.get("bank_account_last4"),
        "bank_account_status": profile.get("bank_account_status"),
        "has_stripe_account": bool(profile.get("stripe_account_id"))
    }


@router.post("/contractor/payment/initiate")
def initiate_payment(payment: PaymentRequest, token: str = Depends(verify_firebase_token)):
    """
    Initiate a payment from landlord to contractor.
    This endpoint should be called by landlords to pay contractors for completed work.
    """
    try:
        # Get contractor profile
        profile = ContractorRepo().get_profile(payment.contractor_id)

        if not profile:
            raise HTTPException(status_code=404, detail="Contractor not found")

        if not profile.get("payment_enabled"):
            raise HTTPException(
                status_code=400,
                detail="Contractor has not set up payment information"
            )

        stripe_account_id = profile.get("stripe_account_id")
        if not stripe_account_id:
            raise HTTPException(
                status_code=400,
                detail="Contractor Stripe account not found"
            )

        # Convert amount to cents
        amount_cents = int(payment.amount * 100)

        if amount_cents <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")

        # Create metadata
        metadata = {
            "contractor_id": payment.contractor_id,
            "contractor_name": profile.get("name", "Unknown")
        }

        if payment.job_id:
            metadata["job_id"] = payment.job_id

        if payment.incident_id:
            metadata["incident_id"] = payment.incident_id

        # Create transfer via Stripe
        stripe_service = StripeService()
        transfer_result = stripe_service.create_payout(
            destination_account_id=stripe_account_id,
            amount_cents=amount_cents,
            description=payment.description,
            metadata=metadata
        )

        return {
            "status": "success",
            "transfer_id": transfer_result["transfer_id"],
            "amount": payment.amount,
            "contractor_id": payment.contractor_id,
            "contractor_name": profile.get("name"),
            "description": payment.description,
            "transfer_status": transfer_result["status"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payment failed: {str(e)}")
