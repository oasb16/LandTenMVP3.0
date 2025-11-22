"""
❌ DEPRECATED - V2 AI Webhooks (DISABLED)

This file has been replaced by ai_webhooks_v3.py.

All V2 logic including:
- ai_reasoning_v2
- intent_classifier
- flow_engine
- flow_stage_mapper

Has been removed and replaced with the V3 LLM-Driven Orchestrator.

DO NOT USE THIS FILE.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/ai/stream-webhook-v2-deprecated")
async def deprecated_webhook():
    """This endpoint is deprecated and disabled."""
    raise HTTPException(
        status_code=410,
        detail={
            "error": "V2 AI Webhooks Deprecated",
            "message": "This endpoint has been replaced by /ai/stream-webhook (V3 Orchestrator)",
            "action": "Please use the V3 endpoint at /ai/stream-webhook",
        }
    )


# All other V2 endpoints removed
# Use ai_webhooks_v3.py instead
