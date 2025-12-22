import os, json
import re
import time
from uuid import uuid4
from typing import List, Dict, Any, Optional, Tuple
from collections import OrderedDict
from threading import Lock

from openai import OpenAI
from difflib import SequenceMatcher
import math

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..deps.auth import verify_firebase_token
from ..deps.stream_signing import verify_stream_signature
from ..services.ai_service import get_ai_response
from ..services.chatbot import (
    ensure_agent_user as bot_ensure_agent_user,
    build_context,
    agent_reply,
    agent_reply_async,
    post_agent_message,
    get_simple_conversational_response_async,
)
from ..services.context_manager import get_context_manager
from ..services.dynamo_service import save_channel_snapshot
from ..services.dynamo_service import IncidentDB
from ..services.incident_flow import (
    classify_issue,
    diy_suggestions,
    create_incident_record,
    summarize_for_landlord,
    threshold_decision,
    generate_contractor_bids,
)
from ..services.ai_reasoning_v2 import get_ai_reasoning_v2 as get_ai_reasoning
from ..services.dynamo_service import record_mttr_event, record_ai_feedback, get_aggregated_metrics
from ..services.incident_flow import create_work_order

try:
    from stream_chat import StreamChat
    from stream_chat.base.exceptions import StreamAPIException
except ImportError:  # pragma: no cover
    StreamChat = None  # type: ignore
    StreamAPIException = Exception  # type: ignore


router = APIRouter()

# Token caching with LRU eviction
class TokenCache:
    """Simple LRU cache for Stream tokens with TTL."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()
        self.lock = Lock()

    def get(self, user_id: str, persona: str) -> Optional[str]:
        """Get cached token if valid."""
        key = f"{user_id}:{persona}"
        with self.lock:
            if key in self.cache:
                token, expires_at = self.cache[key]
                if time.time() < expires_at:
                    # Move to end (mark as recently used)
                    self.cache.move_to_end(key)
                    print(f"[token-cache] HIT for {user_id}")
                    return token
                else:
                    # Expired, remove
                    del self.cache[key]
                    print(f"[token-cache] EXPIRED for {user_id}")
        return None

    def set(self, user_id: str, persona: str, token: str) -> None:
        """Cache a token with TTL."""
        key = f"{user_id}:{persona}"
        with self.lock:
            # Remove if exists (to update position)
            if key in self.cache:
                del self.cache[key]
            # Add with expiry
            self.cache[key] = (token, time.time() + self.ttl_seconds)
            # Evict oldest if over max size
            if len(self.cache) > self.max_size:
                oldest = next(iter(self.cache))
                del self.cache[oldest]
                print(f"[token-cache] EVICTED {oldest}")
            print(f"[token-cache] CACHED for {user_id} (TTL: {self.ttl_seconds}s)")


# Rate limiting for token requests
class RateLimiter:
    """Simple per-user rate limiter with sliding window."""

    def __init__(self, min_interval_seconds: float = 5.0):
        self.min_interval = min_interval_seconds
        self.last_requests: Dict[str, float] = {}
        self.lock = Lock()

    def check_and_update(self, user_id: str) -> bool:
        """Check if request is allowed, update timestamp if so."""
        with self.lock:
            now = time.time()
            last_request = self.last_requests.get(user_id, 0)
            elapsed = now - last_request

            if elapsed < self.min_interval:
                remaining = self.min_interval - elapsed
                print(f"[rate-limit] BLOCKED {user_id} - {remaining:.1f}s remaining")
                return False

            self.last_requests[user_id] = now
            print(f"[rate-limit] ALLOWED {user_id}")
            return True


# Global instances
_token_cache = TokenCache(max_size=1000, ttl_seconds=300)  # 5 minutes
# FIXED: Reduce rate limit interval for development (was 5.0s, now 1.0s)
# Production systems can override via environment variable if needed
import os
_rate_limit_interval = float(os.getenv("TOKEN_RATE_LIMIT_SECONDS", "1.0"))
_rate_limiter = RateLimiter(min_interval_seconds=_rate_limit_interval)


def _slugify(value: str, allow_at: bool = False) -> str:
    pattern = r"[^a-z0-9@_-]" if allow_at else r"[^a-z0-9_-]"
    slug = re.sub(pattern, "-", value.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


DEFAULT_CHANNEL_ID = _slugify(os.getenv("STREAM_DEFAULT_CHANNEL", "landten-default"))
if not DEFAULT_CHANNEL_ID:
    DEFAULT_CHANNEL_ID = "landten-default"


_AGENT_BASE_ID = os.getenv("STREAM_AGENT_USER_ID", "landten-agent")
AGENT_USER_ID = _slugify(_AGENT_BASE_ID) or "landten-agent"
AGENT_DISPLAY_NAME = os.getenv("STREAM_AGENT_NAME", "LandTen Agent")
AGENT_ROLE = os.getenv("STREAM_AGENT_ROLE", "admin")
AGENT_PERSONA = os.getenv("STREAM_AGENT_PERSONA", "assistant")
AUTOJOIN_AGENT = os.getenv("STREAM_AGENT_AUTOJOIN", "true").lower() not in {"false", "0", "no"}
WEBHOOK_SECRET = os.getenv("STREAM_WEBHOOK_SECRET", "")

DISCOVERY_QUESTIONS = [
    {"key": "location", "prompt": "Where exactly is the issue located?"},
    {"key": "severity", "prompt": "How severe is the issue right now (drip, steady leak, flooding, etc.)?"},
    {"key": "noticed", "prompt": "When did you first notice the problem?"},
    {"key": "media", "prompt": "Can you upload a photo or short video so I can see what you're seeing?"},
]


def _channel_identifier(channel, channel_state: Dict[str, Any]) -> str:
    cid = getattr(channel, "id", None)
    if cid:
        return cid
    return (
        channel_state.get("channel", {}).get("id")
        or channel_state.get("channel", {}).get("cid")
        or channel_state.get("channel_id")
        or "unknown"
    )


def _persist_discovery(channel, discovery: Dict[str, Any]) -> None:
    try:
        channel.update({"discovery": discovery})
    except (KeyError, StreamAPIException) as exc:  # pragma: no cover - logging only
        print(f"[stream] failed to persist discovery state: {exc}")

def _handle_discovery_message(
    client: Any,
    channel,
    channel_state: Dict[str, Any],
    message: Dict[str, Any],
    persona: Optional[str] = None,
) -> None:
    channel_data = channel_state.get("channel", {}).get("data", {}) or {}
    discovery = channel_data.get("discovery") or {}
    lower_text = (message.get("text") or "").lower()
    context = build_context(channel_state.get("messages", []))
    channel_id = _channel_identifier(channel, channel_state)        

    print(f"[discovery] Current discovery state: {discovery} for channel_data : {channel_data} for message: {lower_text} for persona: {persona}")

    def ask_question(index: int, acknowledgement: Optional[str] = None):
        question = DISCOVERY_QUESTIONS[index]["prompt"]
        prompt = (
            f"You are assisting a tenant with a maintenance issue. "
            f"{acknowledgement or ''} Ask them: {question}. Keep it short and friendly."
        )
        reply = agent_reply(prompt, context, persona)
        print(f"[discovery] Asking question {index}: {question}"
              f"Reply: {reply}")
        # Sanitize reply to plain text before posting
        reply_text = reply if isinstance(reply, str) else (json.dumps(reply, ensure_ascii=False) if isinstance(reply, (dict, list)) else str(reply))
        post_agent_message(client, channel_id, reply_text)

    if not discovery or discovery.get("stage") in {None, "complete"} or "start discovery" in lower_text:
        discovery = {
            "stage": "questions",
            "question_index": 0,
            "answers": {},
            "history": [],
        }
        _persist_discovery(channel, discovery)
        print(f"\n\n[discovery] Starting new discovery flow ... \n\n")
        prompt = (
            "A tenant requested help with a maintenance issue. "
            f"Let them know you'll gather a few details and ask the first question: {DISCOVERY_QUESTIONS[0]['prompt']}"
            f" Keep it short and friendly." 
        )
        reply = agent_reply(prompt, context, persona)
        reply_text = reply if isinstance(reply, str) else (json.dumps(reply, ensure_ascii=False) if isinstance(reply, (dict, list)) else str(reply))
        print("[discovery] Initiating discovery with first question.")
        post_agent_message(client, channel_id, reply_text)
        return

    if discovery.get("stage") == "questions":
        idx = discovery.get("question_index", 0)
        print(f"\n\n[discovery] Handling question {idx} response.\n\n")
        if idx < len(DISCOVERY_QUESTIONS):
            key = DISCOVERY_QUESTIONS[idx]["key"]
            discovery.setdefault("answers", {})[key] = message.get("text")
            discovery.setdefault("history", []).append({"key": key, "value": message.get("text")})
            discovery["question_index"] = idx + 1
            _persist_discovery(channel, discovery)
        idx = discovery.get("question_index", 0)
        if idx < len(DISCOVERY_QUESTIONS):
            prev_key = DISCOVERY_QUESTIONS[idx - 1]["key"] if idx > 0 else None
            ack = f"Thank them for the info about {prev_key}." if prev_key else None
            ask_question(idx, ack)
        else:
            answers = discovery.get("answers", {})
            summary = "; ".join(f"{k}: {v}" for k, v in answers.items())
            category, severity, urgency = classify_issue(summary)
            suggestions = diy_suggestions(category)
            discovery["stage"] = "diy"
            discovery["summary"] = summary
            discovery["classification"] = {
                "category": category,
                "severity": severity,
                "urgency": urgency,
            }
            _persist_discovery(channel, discovery)
            prompt = (
                f"Summarize the tenant issue: {summary}. "
                f"Provide DIY suggestions ({'; '.join(suggestions)}). "
                "Ask them to reply 'Resolved' if it works or 'Not resolved' if it still needs help."
            )
            reply = agent_reply(prompt, context, persona)
            reply_text = reply if isinstance(reply, str) else (json.dumps(reply, ensure_ascii=False) if isinstance(reply, (dict, list)) else str(reply))
            post_agent_message(client, channel_id, reply_text)
        return

    if discovery.get("stage") == "diy":
        lowered = lower_text
        if "resolve" in lowered and "not" not in lowered:
            discovery["stage"] = "complete"
            discovery["diy_result"] = "Resolved via DIY"
            _persist_discovery(channel, discovery)
            prompt = (
                "The tenant says the issue is resolved. Congratulate them, remind them to reach out if it recurs, "
                "and close the conversation without escalating."
            )
            reply = agent_reply(prompt, context, persona)
            reply_text = reply if isinstance(reply, str) else (json.dumps(reply, ensure_ascii=False) if isinstance(reply, (dict, list)) else str(reply))
            post_agent_message(client, channel_id, reply_text)
            return

        discovery["stage"] = "incident"
        discovery["diy_result"] = "Unresolved"
        _persist_discovery(channel, discovery)
        classification = discovery.get("classification", {})
        summary = discovery.get("summary", message.get("text"))
        tenant_email = message.get("user", {}).get("id", "tenant")
        # === Context check before discovery-based incident creation ===
        try:
            cm = get_context_manager()
            analysis = smart_incident_context_analyzer(tenant_email, channel_id, summary)
            decision = analysis.get("decision")
            reuse_incident = analysis.get("incident_id")
            similarity = analysis.get("similarity", 0.0)
        except Exception as exc:
            print(f"[context-analyzer-error] {exc}")
            decision, reuse_incident, similarity = ("create", None, 0.0)

        if decision == "reuse" and reuse_incident:
            print(f"[context-analyzer] Reusing incident {reuse_incident} (sim={similarity:.2f}) from discovery flow")
            return

        elif decision == "close" and reuse_incident:
            try:
                IncidentDB.update_incident_status(reuse_incident, "stale", user_id=user_id)
                cm = get_context_manager()
                cm.update_context(tenant_email, channel_id, {"active_incident": None})
                print(f"[context-analyzer] Closed old incident {reuse_incident} (sim={similarity:.2f}) before discovery create")
            except Exception as e:
                print(f"[context-analyzer-error] Failed to close old incident {reuse_incident}: {e}")
            # continue to create new

        elif decision == "ignore":
            print(f"[context-analyzer] Ignored general message during discovery; skipping incident creation.")
            return
        # ==============================================================

        # Create canonical incident record (create_incident_record uses UTC ISO for created_at)
        try:
            incident = create_incident_record(
                thread_id=channel_id,
                tenant_email=tenant_email,
                payload={
                    "category": classification.get("category", "general"),
                    "severity": classification.get("severity", "medium"),
                    "urgency": classification.get("urgency", "routine"),
                    "summary": summary,
                    "diy_attempted": True,
                    "diy_result": "Unresolved",
                    "media": discovery.get("media", []),
                },
            )
            print(f"[incident-flow] Created incident via discovery: {incident.get('incident_id')}")
        except Exception as e:
            print(f"[error][incident-flow] create_incident_record failed: {e}")
            return
        # Persist incident into channel data and context manager so future messages are aware
        try:
            channel.update({
                "active_incident": incident["incident_id"],
                "incident_details": incident,
                "flow_state": {"stage": "incident.active", "incident_id": incident["incident_id"]},
            })
            print(f"[incident-flow] \ud83d\udcbe Persisted incident {incident['incident_id']} into channel data")
        except Exception as e:
            print(f"[incident-flow] failed to persist incident into channel: {e}")

        try:
            context_manager = get_context_manager()
            user_id = tenant_email
            context_manager.set_active_incident(user_id, channel_id, incident["incident_id"])
            print(f"[context-update] Set active incident {incident['incident_id']} for user {user_id} in channel {channel_id}")
            context_manager.advance_flow_state(user_id, channel_id, "incident", {"incident_id": incident["incident_id"], "stage": "active"})
            print(f"[context-update] Set active incident {incident['incident_id']} for user {user_id} in channel {channel_id}")
            try:
                # Persist a convenient incident summary in context to aid later similarity checks
                context_manager.update_context(user_id, channel_id, {"active_incident": incident["incident_id"], "incident_summary": (summary or "").strip()})
            except Exception:
                pass
        except Exception as e:
            print(f"[incident-flow] failed to update context manager: {e}")
        bids = generate_contractor_bids(classification.get("category", "general"))
        decision = threshold_decision(bids[0]["quote"])
        # Create a work order for the incident
        try:
            work_order = create_work_order(incident)
            print(f"[workorder-flow] Created work order {work_order.get('job_id')} for incident {incident.get('incident_id')}")
        except Exception as e:
            print(f"[workorder-flow] failed to create work order: {e}")
        landlord_summary = summarize_for_landlord(incident)
        prompt = (
            f"Inform the tenant that Incident {incident['incident_id']} has been created and will be shared with the landlord. "
            f"Summarize the findings:\n{landlord_summary}\n"
            f"Explain that approval recommendation is '{decision}'. "
            "Let them know they'll receive updates about contractor scheduling."
        )
        reply = agent_reply(prompt, context, persona)
        post_agent_message(client, channel_id, reply)
        bids_text = "\n".join(f"- {b['name']}: ${b['quote']} ({b['eta']})" for b in bids)
        post_agent_message(
            client,
            channel_id,
            f"Sample contractor options:\n{bids_text}\nWe'll finalize once the landlord approves.",
        )
        # Auto-assign best contractor if SLA is close / decision recommends auto-approve
        try:
            mttr_target = channel_state.get("metadata", {}).get("mttr_target_hours") or incident.get("mttr_target_hours")
            if (mttr_target and mttr_target <= 12) or decision == "auto-approve":
                best = bids[0]
                assigned = best.get("name")
                # Update incident assignment
                try:
                    channel.update({"active_incident": incident["incident_id"], "assigned_contractor": assigned})
                except Exception:
                    pass
                try:
                    # Record assignment in context
                    cm = get_context_manager()
                    cm.update_context(tenant_email, channel_id, {"active_job": work_order.get("job_id"), "assigned_contractor": assigned})
                except Exception:
                    pass
                print(f"[workorder-flow] Auto-assigned contractor {assigned} for incident {incident.get('incident_id')}")
        except Exception as e:
            print(f"[workorder-flow] auto-assign logic failed: {e}")

        # Record an MTTR event for incident creation
        try:
            record_mttr_event(incident.get("incident_id"), {"created_at": incident.get("created_at")})
        except Exception as e:
            print(f"[sla-metrics] failed to record mttr event: {e}")
        # Optionally persist a snapshot for analytics / debugging
        try:
            try:
                summary_snapshot = summarize_channel_state(channel.query(state=True, watch=False))
            except Exception:
                summary_snapshot = summarize_channel_state(channel_state)
            save_channel_snapshot(channel_id, summary_snapshot)
        except Exception as e:
            print(f"[snapshot] failed to save channel snapshot: {e}")


def _get_stream_client() -> Any:
    if StreamChat is None:
        raise HTTPException(status_code=500, detail="stream-chat SDK not installed on backend")
    api_key = os.getenv("STREAM_CHAT_API_KEY")
    api_secret = os.getenv("STREAM_CHAT_API_SECRET")
    if not api_key or not api_secret:
        raise HTTPException(status_code=501, detail="Stream Chat credentials not configured")
    return StreamChat(api_key, api_secret)


def _sanitize_members(members: List[str]) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    sanitized: List[str] = []
    meta: Dict[str, Dict[str, str]] = {}
    for member in members:
        s_id = _slugify(member, allow_at=True)
        if not s_id:
            s_id = f"user-{uuid4().hex[:8]}"
        sanitized.append(s_id)
        meta[s_id] = {"sanitized_id": s_id, "display": member}
    return sanitized, meta


@router.get("/chat/stream/token")
def get_stream_token(user_id: str, persona: str, contractor_id: Optional[str] = None, token: str = Depends(verify_firebase_token)):
    api_key = os.getenv("STREAM_CHAT_API_KEY")
    allowed_roles = {
        role.strip() for role in os.getenv("STREAM_ALLOWED_ROLES", "user,admin,guest").split(",") if role.strip()
    }
    allowed_roles.add(AGENT_ROLE)

    # Rate limiting
    if not _rate_limiter.check_and_update(user_id):
        raise HTTPException(
            status_code=429,
            detail="Too many token requests. Please wait a few seconds before retrying."
        )

    try:
        client = _get_stream_client()
        bot_ensure_agent_user(client)

        sanitized_user_id = _slugify(user_id, allow_at=True)
        if not sanitized_user_id:
            sanitized_user_id = f"user-{uuid4().hex[:8]}"
            print(f"[stream] sanitized user_id empty; generated {sanitized_user_id}")

        # Determine channel ID based on persona and contractor_id
        # For contractor onboarding, create unique channel per contractor
        if persona == "contractor_onboarding" and contractor_id:
            channel_id = f"contractor-{_slugify(contractor_id)}"
            channel_name = f"Contractor Onboarding - {contractor_id}"
            print(f"[stream] Creating unique contractor channel: {channel_id}")
        else:
            channel_id = DEFAULT_CHANNEL_ID
            channel_name = "LandTen Conversations"

        # Check token cache first
        cached_token = _token_cache.get(sanitized_user_id, persona)
        if cached_token:
            print(f"[stream] Returning cached token for {sanitized_user_id} with channel {channel_id}")
            return {
                "api_key": api_key,
                "token": cached_token,
                "channel_id": channel_id,
                "user_id": sanitized_user_id,
                "display_user_id": user_id,
                "persona": persona,
            }

        # Ensure user exists
        role = persona if persona in allowed_roles else "user"
        user_payload = {
            "id": sanitized_user_id,
            "role": role,
            "email": user_id,
            "persona": persona,
        }
        client.upsert_user(user_payload)

        # Ensure channel exists and has member
        channel = client.channel("messaging", channel_id, {"name": channel_name})
        try:
            channel.create(user_id=sanitized_user_id)
        except (KeyError, StreamAPIException) as exc:
            # Likely already created; log and continue
            print(f"[stream] channel.create skipped: {exc}")

        try:
            channel.add_members(
                [sanitized_user_id],
                message={
                    "text": f"{sanitized_user_id} joined",
                    "user_id": sanitized_user_id,
                },
                hide_history=False,
            )
        except (KeyError, StreamAPIException) as exc:
            print(f"[stream] add_members skipped for {sanitized_user_id}: {exc}")

        if AUTOJOIN_AGENT and AGENT_USER_ID:
            try:
                channel.add_members(
                    [AGENT_USER_ID],
                    message={
                        "text": f"{AGENT_DISPLAY_NAME} is here to help.",
                        "user_id": sanitized_user_id,
                    },
                    hide_history=False,
                )
            except (KeyError, StreamAPIException) as exc:
                print(f"[stream] agent add_members skipped: {exc}")

        # Generate new token
        print(f"[stream] Generating new token for {sanitized_user_id} with channel {channel_id}")
        token_value = client.create_token(sanitized_user_id)

        # Cache the token
        _token_cache.set(sanitized_user_id, persona, token_value)

        return {
            "api_key": api_key,
            "token": token_value,
            "channel_id": channel_id,
            "user_id": sanitized_user_id,
            "display_user_id": user_id,
            "persona": persona,
        }
    except (KeyError, StreamAPIException) as exc:
        print(f"[stream] token endpoint error for {user_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Stream error: {exc}")


class StreamThreadCreate(BaseModel):
    creator: str
    participants: List[str]
    channel_id: Optional[str] = None
    name: Optional[str] = None
    persona: Optional[str] = None
    include_agent: bool = True
    extra_data: Dict[str, Any] = {}


class StreamThread(BaseModel):
    channel_id: str
    name: Optional[str]
    members: List[Dict[str, Any]]
    unread_count: int = 0
    last_message: Optional[Dict[str, Any]] = None


class AgentMessageRequest(BaseModel):
    channel_id: str
    prompt: str
    persona: Optional[str] = None
    context: Optional[str] = None
    requesting_user: Optional[str] = None


@router.post("/chat/stream/thread", response_model=StreamThread)
def create_stream_thread(req: StreamThreadCreate, token: str = Depends(verify_firebase_token)):
    if not req.participants:
        raise HTTPException(status_code=400, detail="At least one participant is required")

    client = _get_stream_client()
    bot_ensure_agent_user(client)

    # Ensure creator is part of participants
    all_participants = list(dict.fromkeys([req.creator, *req.participants]))
    sanitized_members, member_meta = _sanitize_members(all_participants)

    # Upsert all users so they exist in Stream
    for original, sanitized_id in zip(all_participants, sanitized_members):
        payload = {
            "id": sanitized_id,
            "email": original,
            "persona": req.persona,
        }
        try:
            client.upsert_user(payload)
        except (KeyError, StreamAPIException) as exc:
            print(f"[stream] upsert_user failed for {original}: {exc}")

    if req.include_agent and AGENT_USER_ID:
        sanitized_members.append(AGENT_USER_ID)
        member_meta[AGENT_USER_ID] = {"sanitized_id": AGENT_USER_ID, "display": AGENT_DISPLAY_NAME}

    base_channel_id = req.channel_id or "-".join(sorted(member_meta))
    channel_id = _slugify(base_channel_id) or f"thread-{uuid4().hex[:8]}"

    name = req.name or ", ".join(
        meta.get("display", "")
        for sid, meta in member_meta.items()
        if sid != AGENT_USER_ID and meta.get("display")
    )
    channel_data: Dict[str, Any] = {
        "name": name or "Conversation",
        "members_meta": member_meta,
    }
    if req.persona:
        channel_data["persona"] = req.persona
    if req.extra_data:
        channel_data.update(req.extra_data)

    channel = client.channel("messaging", channel_id, channel_data)
    creator_sanitized = _slugify(req.creator, allow_at=True) or sanitized_members[0]

    try:
        print("[stream] creating channel:", channel_id, "with members:", sanitized_members)
        # Convert list to dict (object)
        members_payload = {mid: {} for mid in sanitized_members}
        print("[stream] members payload:", members_payload)

        channel.create(
            user_id=creator_sanitized,
            data={
                "created_by_id": AGENT_USER_ID,
                "name": name or "Conversation",
                "members_meta": member_meta,
                **({"persona": req.persona} if req.persona else {}),
                **req.extra_data,
            },
            members=members_payload,
        )
    except (KeyError, StreamAPIException) as exc:
        print(f"[stream] channel.create skipped: {exc}")
        if "already exists" not in str(exc).lower():
            raise HTTPException(status_code=500, detail=f"Stream error creating channel: {exc}")

    try:
        channel.add_members(
            sanitized_members,
            message={
                "text": f"Conversation synced by {creator_sanitized}",
                "user_id": creator_sanitized,
            },
            hide_history=False,
        )
    except (KeyError, StreamAPIException) as exc:
        print(f"[stream] add_members during create skipped: {exc}")

    last_message = None
    try:
        state = channel.query(watch=False, state=True)
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
    except (KeyError, StreamAPIException) as exc:
        print(f"[stream] channel state fetch failed: {exc}")

    return StreamThread(
        channel_id=channel_id,
        name=channel_data.get("name"),
        members=list(member_meta.values()),
        unread_count=0,
        last_message=last_message,
    )


@router.get("/chat/stream/threads/{user_id}", response_model=List[StreamThread])
def list_stream_threads(user_id: str, token: str = Depends(verify_firebase_token)):
    client = _get_stream_client()
    sanitized_user = _slugify(user_id, allow_at=True)
    if not sanitized_user:
        raise HTTPException(status_code=400, detail="Invalid user id")

    try:
        channels = client.query_channels(
            filters={"members": {"$in": [sanitized_user]}},
            sort=[{"last_message_at": -1}],
            state=True,
            watch=False,
        )
    except (KeyError, StreamAPIException) as exc:
        raise HTTPException(status_code=500, detail=f"Stream error listing threads: {exc}")

    summaries: List[StreamThread] = []
    for ch in channels:
        cid = getattr(ch, "id", None) or getattr(ch, "channel_id", None)
        if not cid:
            continue
        data = getattr(ch, "data", {}) or {}
        members_meta = data.get("members_meta", {})
        members_list = list(members_meta.values()) if isinstance(members_meta, dict) else []
        last_message = None
        try:
            state_payload = ch.query(state=True, watch=False)
            messages = state_payload.get("messages", [])
            if messages:
                last_message = messages[-1]
        except (KeyError, StreamAPIException) as exc:  # pragma: no cover - logging only
            print(f"[stream] channel state fetch during list failed: {exc}")
        summaries.append(
            StreamThread(
                channel_id=cid,
                name=data.get("name"),
                members=members_list,
                unread_count=getattr(ch, "unread_count", 0) or 0,
                last_message=last_message,
            )
        )
    return summaries


@router.post("/chat/stream/agent_reply")
def post_agent_reply(req: AgentMessageRequest, token: str = Depends(verify_firebase_token)):
    """
    Agent reply endpoint that:
    1. Generates AI response via get_ai_response()
    2. Posts response to Stream Chat
    3. Triggers PropertyAIBot incident detection pipeline
    """
    if not req.channel_id:
        raise HTTPException(status_code=400, detail="channel_id required")

    client = _get_stream_client()
    agent_id = bot_ensure_agent_user(client)
    if not agent_id:
        raise HTTPException(status_code=500, detail="Agent user not configured")

    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    print(f"[agent_reply] Processing request for channel: {req.channel_id}")
    print(f"[agent_reply] Prompt: {req.prompt[:100]}{'...' if len(req.prompt) > 100 else ''}")

    context_lines = []
    if req.context:
        context_lines.append(req.context)
    if req.requesting_user:
        context_lines.append(f"Request from {req.requesting_user}")
    conversation = "\n".join(context_lines) if context_lines else None

    # Generate AI response
    smart_reply = get_ai_response(
        req.prompt,
        persona=req.persona,
        context=conversation,
        n_refine=3
    )

    # Post AI response to Stream Chat
    channel = client.channel("messaging", req.channel_id)
    try:
        channel.send_message(
            {"text": smart_reply or "(no reply generated)", "type": "regular"},
            user_id=agent_id,
        )
        print(f"[agent_reply] AI response posted to channel {req.channel_id}")
    except (KeyError, StreamAPIException) as exc:
        print(f"[agent_reply] ❌ ERROR: failed to post agent reply: {exc}")
        raise HTTPException(status_code=500, detail=f"Stream error posting agent reply: {exc}")

    # Trigger PropertyAIBot incident detection
    # This handles incident detection, card creation, and DynamoDB persistence
    try:
        from ..services.stream_bot import get_bot

        print(f"[agent_reply] Triggering PropertyAIBot incident detection...")

        # Construct webhook-like payload for PropertyAIBot
        webhook_payload = {
            "type": "message.new",
            "channel_id": req.channel_id,
            "user": {
                "id": req.requesting_user or "user-unknown",
                "name": req.requesting_user or "Unknown User",
                "is_bot": False,
                "persona": req.persona or "tenant"
            },
            "message": {
                "id": f"msg-{hash(req.prompt) % 100000}",
                "text": req.prompt,
                "type": "regular",
                "attachments": []
            }
        }

        property_ai_bot = get_bot()
        result = property_ai_bot.handle_message_event(webhook_payload)

        if result:
            print(f"[agent_reply] PropertyAIBot processed message - incident detection completed")
        else:
            print(f"[agent_reply] PropertyAIBot ignored message (no incident detected or bot message)")

    except Exception as exc:
        # Don't fail the entire request if incident detection fails
        # Log the error and continue
        print(f"[agent_reply] WARNING: PropertyAIBot incident detection failed: {exc}")
        import traceback
        traceback.print_exc()

    return {
        "status": "sent",
        "agent_id": agent_id,
        "message": smart_reply,
        "incident_detection": "processed"
    }

def _handle_intelligent_message(
    client: Any,
    channel,
    channel_state: Dict[str, Any],
    message: Dict[str, Any],
    persona: Optional[str] = None,
) -> None:
    """
    Intelligent message handler that uses AI reasoning to:
    1. Understand context from recent conversation (last 3-5 messages)
    2. Decide whether to continue conversation or escalate to structured flow
    3. Generate contextually appropriate responses
    4. Dynamically switch modes (general → incident → discovery → job)
    """
    from ..services.ai_reasoning_v2 import AIReasoningV2 as AIReasoning

    channel_id = _channel_identifier(channel, channel_state)
    channel_data = channel_state.get("channel", {}).get("data", {}) or {}
    discovery = channel_data.get("discovery") or {}

    # Build context from last 5 messages for continuity
    messages = channel_state.get("messages", [])
    recent_messages = messages[-5:] if len(messages) > 5 else messages
    context_lines = []
    for msg in recent_messages:
        user_id = msg.get("user", {}).get("id", "unknown")
        text = msg.get("text", "")
        context_lines.append(f"{user_id}: {text}")
    context = "\n".join(context_lines)

    # Extract current message
    message_text = message.get("text", "").strip()
    if not message_text:
        return

    # Check if we're in an active discovery flow
    if discovery and discovery.get("stage") in {"questions", "diy"}:
        # Continue existing discovery flow
        _handle_discovery_message(client, channel, channel_state, message, persona)
        return

    # Use AI reasoning to infer intent and decide next action
    reasoning_engine = AIReasoning()
    reasoning_context = {
        "recent_conversation": context,
        "persona": persona or "tenant",
        "channel_id": channel_id,
        "discovery_state": discovery.get("stage") if discovery else None,
    }

    intent_result = reasoning_engine.infer_intent(
        message=message_text,
        context=reasoning_context,
        persona=persona or "tenant"
    )

    intent = intent_result.get("intent", "general.chat")
    entities = intent_result.get("entities", {})
    confidence = intent_result.get("confidence", 0.0)

    print(f"[intelligent-handler] Intent: {intent}, Confidence: {confidence:.2f}")

        # Auto-engage discovery flow for high-confidence incident reports
    if intent in {"incident.report", "maintenance"} and confidence > 0.6:
        print("[intelligent-handler] 🚨 High confidence incident detected")
        preliminary_incident = {
            "summary": message_text,
            "persona": persona,
            "entities": entities,
            "confidence": confidence,
            "timestamp": time.time(),
        }
        channel_state.setdefault("incident_candidate", preliminary_incident)
        # Before starting discovery, create a preliminary incident record and persist it
        try:
            from ..services.incident_flow import create_incident_record
            from ..services.stream_bot import get_bot

            tenant_email = (message.get("user") or {}).get("email") or (message.get("user") or {}).get("id") or "unknown"
            user_id = (message.get("user") or {}).get("id") or tenant_email

            # === Context check before creating new incident ===
            try:
                cm = get_context_manager()
                analysis = smart_incident_context_analyzer(user_id, channel_id, message_text)
                decision = analysis.get("decision")
                reuse_incident = analysis.get("incident_id")
                similarity = analysis.get("similarity", 0.0)
            except Exception as exc:
                print(f"[context-analyzer-error] {exc}")
                decision, reuse_incident, similarity = ("create", None, 0.0)

            if decision == "reuse" and reuse_incident:
                print(f"[context-analyzer] Reusing existing incident {reuse_incident} (sim={similarity:.2f})")
                reply = f"Noted. Continuing with existing incident {reuse_incident}."
                cm.update_context(user_id, channel_id, {"active_incident": reuse_incident})
                post_agent_message(client, channel_id, reply)                
                return

            elif decision == "close" and reuse_incident:
                try:
                    IncidentDB.update_incident_status(reuse_incident, "stale", user_id=user_id)
                    cm = get_context_manager()
                    cm.update_context(user_id, channel_id, {"active_incident": None})
                    print(f"[context-analyzer] Closed old incident {reuse_incident} (sim={similarity:.2f})")
                except Exception as e:
                    print(f"[context-analyzer-error] ❌ Error closing old incident {reuse_incident}: {e}")
                # continue to create a new one

            elif decision == "ignore":
                print(f"[context-analyzer] Ignored trivial message; skipping incident creation.")
                return
            # ==================================================

            # Create preliminary incident (only if not reused/ignored)
            try:
                incident = create_incident_record(
                    thread_id=channel_id,
                    tenant_email=tenant_email,
                    payload={
                        "category": entities.get("category", "general"),
                        "severity": entities.get("severity", "medium"),
                        "urgency": entities.get("urgency", "routine"),
                        "summary": message_text,
                        "status": "detected",
                    },
                )
                print(f"[incident-flow] Created preliminary incident {incident}")
                cm.update_context(user_id, channel_id, {"active_incident": incident.get("incident_id")})
                print(f"[context-update] Set active incident {incident.get('incident_id')} for user {user_id} in channel {channel_id}")
            except Exception as e:
                print(f"[error][incident-flow] ❌ Incident creation failed in discovery path: {e}")
                return

            # Update context and flow state
            try:
                cm = get_context_manager()
                cm.set_active_incident(user_id, channel_id, incident.get("incident_id"))
                cm.advance_flow_state(user_id, channel_id, "incident", {"incident_id": incident.get("incident_id")})
                print(f"[context-update] Active incident set for {user_id} on {channel_id}: {incident.get('incident_id')}")
            except Exception as e:
                print(f"[context-update] failed to update context: {e}")
            try:
                # Store the incident summary into context for future analyzer checks
                cm.update_context(user_id, channel_id, {"active_incident": incident.get("incident_id"), "incident_summary": (message_text or "").strip()})
            except Exception:
                pass

            # Send incident card to the channel via stream bot for visibility
            try:
                bot = get_bot()
                bot.send_incident_card(
                    channel_id=channel_id,
                    persona=persona or "tenant",
                    incident_data={
                        **incident,
                        "user_id": user_id,
                        "tenant_name": (message.get("user") or {}).get("name"),
                        "description": message_text,
                    },
                )
            except Exception as e:
                print(f"[stream-bot] failed to send incident card: {e}")

        except Exception as e:
            print(f"[error][incident-flow] ❌ Incident creation failed in discovery path: {e}")

        # Start discovery automatically
        _handle_discovery_message(client, channel, channel_state, {"text": "start discovery"}, persona)
        return

    # Decide how to respond based on intent
    if intent == "incident.report" and confidence > 0.6:
        # Escalate to discovery flow
        print("[intelligent-handler] Escalating to discovery flow")
        # Simulate "start discovery" to trigger structured flow
        modified_message = {**message, "text": "start discovery"}
        _handle_discovery_message(client, channel, channel_state, modified_message, persona)

    elif intent in {"discovery.response", "discovery.continue"}:
        # Continue discovery if active
        if discovery:
            _handle_discovery_message(client, channel, channel_state, message, persona)
        else:
            # Free-form empathy response
            _send_conversational_response(client, channel_id, message_text, context, persona, intent_result)

    else:
        # General conversation, help, greeting, or unclear
        # Provide intelligent free-form response
        _send_conversational_response(client, channel_id, message_text, context, persona, intent_result)





client = OpenAI()

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors (pure Python, no numpy)."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    return dot / (mag1 * mag2) if mag1 and mag2 else 0.0


def get_embedding_safe(text):
    """Get text embedding with safe fallback."""
    try:
        return client.embeddings.create(input=text, model="text-embedding-3-small").data[0].embedding
    except Exception as e:
        print(f"[context-analyzer-error] embedding failed: {e}")
        return []


def smart_incident_context_analyzer(user_id: str, channel_id: str, message_text: str):
    """
    Semantic analyzer to decide whether to reuse, close, or create an incident.
    Uses embeddings for meaning-based comparison and lexical ratio as fallback.
    """
    from ..services.context_manager import get_context_manager
    from ..services.dynamo_service import IncidentDB

    cm = get_context_manager()
    context = cm.get_context(user_id, channel_id, create_if_missing=True) or {}
    from pathlib import Path; Path("my_file.json").write_text("JSON_channel_data : "+json.dumps(context))
    print(f"[context-analyzer] Context for user {user_id} on channel {channel_id}: {context}")
    active_incident = context.get("active_incident")

    if not active_incident:
        print("[context-analyzer] no active incident; decision=create")
        return {"decision": "create", "incident_id": None, "similarity": 0.0}

    # Try to fetch existing summary
    summary = (
        context.get("incident_summary")
        or context.get("summary")
        or context.get("last_incident_summary")
        or ""
    )

    if not summary:
        try:
            # Match your DynamoDB schema: both user_id + incident_id
            incident_data = IncidentDB.get_incident(active_incident, user_id=user_id)
            if incident_data and isinstance(incident_data, dict):
                summary = incident_data.get("summary") or incident_data.get("description") or ""
        except Exception as e:
            print(f"[context-analyzer-warning] failed to fetch incident {active_incident}: {e}")

    summary = summary.strip()
    message_text = (message_text or "").strip()

    if not summary or not message_text:
        print("[context-analyzer] missing baseline text; decision=create")
        return {"decision": "create", "incident_id": None, "similarity": 0.0}

    # Compute semantic + lexical similarity
    emb1, emb2 = get_embedding_safe(summary), get_embedding_safe(message_text)
    sem_sim = cosine_similarity(emb1, emb2) if emb1 and emb2 else 0.0
    lex_sim = SequenceMatcher(None, summary.lower(), message_text.lower()).ratio()
    similarity = max(sem_sim, lex_sim)

    # Apply thresholds
    if similarity >= 0.80:
        decision = "reuse"
    elif similarity >= 0.60:
        decision = "close"
    else:
        decision = "create"

    print(f"[context-analyzer] active_incident={active_incident} "
          f"semantic={sem_sim:.2f} lexical={lex_sim:.2f} "
          f"→ similarity={similarity:.2f} decision={decision}")

    # If reused, refresh context summary for next comparisons
    if decision == "reuse":
        try:
            cm.update_context(user_id, channel_id, {"incident_summary": message_text})
        except Exception as e:
            print(f"[context-analyzer-warning] failed to update summary: {e}")

    return {"decision": decision, "incident_id": active_incident, "similarity": similarity}


def _send_conversational_response(
    client: Any,
    channel_id: str,
    message_text: str,
    context: str,
    persona: Optional[str],
    intent_result: Dict[str, Any],
) -> None:
    """
    Send a natural conversational response based on AI reasoning.
    This restores free-flow chat capability.
    """
    intent = intent_result.get("intent", "general.chat")
    entities = intent_result.get("entities", {})
    next_actions = intent_result.get("next_actions", [])
    reasoning = intent_result.get("reasoning", "")

    # Build prompt for conversational response
    if intent == "greeting":
        prompt = (
            f"A {persona or 'user'} said: {message_text}. "
            "Respond warmly and professionally. Offer to help with property management or maintenance needs. "
            "Keep it brief and friendly."
        )
    elif intent == "help":
        prompt = (
            f"A {persona or 'user'} asked: {message_text}. "
            "Explain that you can help with: reporting maintenance issues, tracking repairs, "
            "answering property questions, and coordinating with landlords/contractors. "
            "Ask what they need help with."
        )
    elif intent == "unclear":
        prompt = (
            f"A {persona or 'user'} said: {message_text}. "
            "Politely clarify what they need. Are they reporting a maintenance issue, "
            "asking a question, or just chatting? Be helpful and empathetic."
        )
    else:
        # General chat or follow-up
        prompt = (
            f"Continue this conversation naturally:\n{context}\n"
            f"User just said: {message_text}\n"
            f"Intent: {intent}\n"
            f"Context: {reasoning if reasoning else 'General conversation'}\n"
            "Respond empathetically. If this seems related to property issues, "
            "gently offer to help formally document it. Otherwise, engage naturally."
        )

    reply = agent_reply(prompt, context, persona)
    # Adaptive escalation: if user indicates unresolved issue, trigger discovery
    lowered = message_text = message_text if 'message_text' in locals() else ''
    if isinstance(lowered, str):
        lowered = lowered.lower()
        if any(word in lowered for word in ["still leaking", "not fixed", "unresolved"]):
            print("[intelligent-handler] ⚠️ User indicates unresolved issue — escalating to incident.")
            modified_message = {"text": "start discovery", "user": {"id": "unknown"}}
            try:
                _handle_discovery_message(client, client.channel("messaging", channel_id), {}, modified_message, persona)
            except Exception as e:
                print(f"[intelligent-handler] failed to escalate to discovery: {e}")
            return

    post_agent_message(client, channel_id, reply)


def _handle_action_message(
    client: Any,
    channel,
    channel_state: Dict[str, Any],
    message: Dict[str, Any],
    persona: Optional[str] = None,
) -> None:
    """
    Handle action button clicks from the UI by routing to PropertyAIBot.
    Actions are sent as messages with format: "action:action_name:incident_id"

    Examples:
    - "action:start_discovery"
    - "action:start_discovery:INC-123"
    - "action:dismiss"
    - "action:approve:INC-456"
    """
    from ..services.stream_bot import get_bot

    message_text = message.get("text", "")
    channel_id = _channel_identifier(channel, channel_state)
    user_id = message.get("user", {}).get("id", "unknown")

    print(f"[🎯 ACTION] Routing action to PropertyAIBot: {message_text}")
    print(f"[🎯 ACTION] User: {user_id}, Channel: {channel_id}, Persona: {persona}")

    # Route to PropertyAIBot which has comprehensive action handlers
    try:
        bot = get_bot()
        result = bot.handle_action(
            action_value=message_text,
            user_id=user_id,
            channel_id=channel_id,
            persona=persona or "tenant"
        )

        if result:
            print(f"[✅ ACTION] PropertyAIBot handled action successfully: {result}")
        else:
            print(f"[⚠️  ACTION] PropertyAIBot returned None - action may not be fully implemented")

    except Exception as e:
        print(f"[❌ ACTION] Error routing to PropertyAIBot: {e}")
        import traceback
        traceback.print_exc()

        # Fallback: send error message
        post_agent_message(
            client,
            channel_id,
            "I encountered an error processing your action. Please try again or contact support if the issue persists."
        )


async def _handle_contractor_message(
    client: Any,
    channel,
    channel_state: Dict[str, Any],
    message: Dict[str, Any],
    persona: Optional[str] = None,
) -> None:
    """
    Handle contractor onboarding messages with contractor-specific AI responses.
    No tenant discovery flows, no incident creation - just onboarding assistance.
    Automatically spawns interactive card micro-flows based on onboarding stage.
    """
    print(f"\n{'🔧'*40}")
    print(f"[🔧 CONTRACTOR HANDLER] CALLED - This is the CONTRACTOR-SPECIFIC handler")
    print(f"[🔧 CONTRACTOR HANDLER] Persona: {persona}")
    print(f"{'🔧'*40}\n")

    channel_id = _channel_identifier(channel, channel_state)
    message_text = message.get("text", "").strip()

    print(f"[🔧 CONTRACTOR HANDLER] Channel ID: {channel_id}")
    print(f"[🔧 CONTRACTOR HANDLER] Message text: {message_text}")

    if not message_text:
        print(f"[🔧 CONTRACTOR HANDLER] Empty message, returning")
        return

    # Build context from recent messages
    messages = channel_state.get("messages", [])
    recent_messages = messages[-5:] if len(messages) > 5 else messages
    context_lines = []
    for msg in recent_messages:
        user_id = msg.get("user", {}).get("id", "unknown")
        text = msg.get("text", "")
        context_lines.append(f"{user_id}: {text}")
    context = "\n".join(context_lines)

    print(f"[🔧 CONTRACTOR HANDLER] Built context from {len(recent_messages)} recent messages")

    # Check for card-specific responses
    metadata = message.get("metadata", {})
    card_action = metadata.get("cardAction")
    print(f"[🔧 CONTRACTOR HANDLER] Card action: {card_action}")

    # Determine response and next card to spawn
    card_to_spawn = None
    card_metadata = {}

    if card_action == "license_submit":
        license_number = metadata.get("licenseNumber", "")
        business_address = metadata.get("businessAddress", "")
        prompt = (
            f"A contractor just submitted their license information:\n"
            f"License: {license_number}\n"
            f"Address: {business_address}\n\n"
            f"Respond warmly in 1-2 sentences, confirm you received it, and let them know you're verifying it. "
            f"Then mention the next step is identity verification."
        )
        card_to_spawn = "identity_verification"

    elif card_action == "identity_start":
        prompt = (
            "A contractor just started the identity verification process. "
            "Acknowledge in 1-2 sentences that they're going through Jumio verification, "
            "and let them know it usually takes 1-2 minutes. "
            "Mention that once approved, they can set up payment info."
        )
        card_to_spawn = "bank_setup"

    elif card_action == "bank_submit":
        account_name = metadata.get("accountName", "")
        prompt = (
            f"A contractor just linked their bank account ({account_name}). "
            f"Congratulate them in 1-2 sentences on completing onboarding! "
            f"Let them know they'll start receiving job opportunities soon. "
            f"Keep it warm and encouraging."
        )
        card_to_spawn = "success"
        card_metadata = {
            "title": "🎉 Onboarding Complete!",
            "message": "You're all set to start receiving jobs on HomeAI Pro. Welcome aboard!",
            "icon": "payment"
        }

    else:
        # AGGRESSIVE DEBUGGING: Print ALL messages and their metadata
        print(f"\n{'🔍'*40}")
        print(f"[🔍 CARD DEBUG] Checking {len(messages)} messages for license card:")
        for i, msg in enumerate(messages):
            msg_user = msg.get("user", {}).get("id", "unknown")
            msg_text = (msg.get("text", "") or "")[:50]
            msg_metadata = msg.get("metadata", {})
            card_type = msg_metadata.get("card_type")
            print(f"  [{i}] User: {msg_user}, Text: '{msg_text}', card_type: {card_type}, Metadata: {msg_metadata}")
        print(f"{'🔍'*40}\n")

        # Check if we've already sent a license verification card
        has_sent_license_card = any(
            msg.get("metadata", {}).get("card_type") == "license_verification"
            for msg in messages
        )

        # Count contractor messages (not AI messages)
        contractor_message_count = sum(
            1 for msg in messages
            if not (msg.get("user", {}).get("id", "").startswith("ai-") or
                   msg.get("user", {}).get("name", "").lower().startswith("ai-") or
                   msg.get("user", {}).get("name", "").lower().startswith("homeai"))
        )

        print(f"[🔍 CARD DEBUG] has_sent_license_card: {has_sent_license_card}")
        print(f"[🔍 CARD DEBUG] contractor_message_count: {contractor_message_count}")

        # If this is one of the first few contractor messages AND we haven't sent the card, spawn it
        should_spawn_license_card = (contractor_message_count <= 5 and not has_sent_license_card)

        prompt = (
            f"You are a friendly onboarding assistant for contractors joining HomeAI Pro. "
            f"Recent conversation:\n{context}\n\n"
            f"Contractor said: {message_text}\n\n"
            f"{'Give a warm, brief welcome and let them know you will help them get started with license verification.' if should_spawn_license_card else 'Respond helpfully in 1-2 sentences.'}\n"
            f"Keep it friendly, professional, and encouraging. "
            f"Do NOT talk about maintenance issues or tenant problems - this is contractor onboarding only."
        )

        # Spawn license card if appropriate
        if should_spawn_license_card:
            card_to_spawn = "license_verification"
            print(f"[🔧 CONTRACTOR HANDLER] 🎯 Contractor message #{contractor_message_count}, spawning license card")
        elif has_sent_license_card:
            print(f"[🔧 CONTRACTOR HANDLER] ℹ️ License card already sent, not spawning duplicate")
        else:
            print(f"[🔧 CONTRACTOR HANDLER] ℹ️ Too many messages ({contractor_message_count}), not spawning initial card")

    # CRITICAL LOGGING: Print the exact prompt being sent to AI
    print(f"\n{'='*80}")
    print(f"[🔧 CONTRACTOR HANDLER] PROMPT BEING SENT TO AI:")
    print(f"{'='*80}")
    print(prompt)
    print(f"{'='*80}\n")

    # Generate AI response using SIMPLE CONVERSATIONAL mode (NOT the tenant analysis framework)
    print(f"[🔧 CONTRACTOR HANDLER] Calling get_simple_conversational_response_async (BYPASS tenant analysis)")
    contractor_system_prompt = (
        "You are a friendly, helpful onboarding assistant for contractors joining HomeAI Pro. "
        "Your role is to guide contractors through:\n"
        "- License verification\n"
        "- Identity verification (Jumio)\n"
        "- Bank account setup for payments\n"
        "- Getting started with jobs\n"
        "- Platform features and benefits\n\n"
        "Always be warm, professional, and encouraging. "
        "Keep responses SHORT (1-2 sentences max) and actionable. "
        "NEVER discuss tenant maintenance issues or property management - focus ONLY on contractor onboarding."
    )
    reply = await get_simple_conversational_response_async(
        system_prompt=contractor_system_prompt,
        user_message=prompt,
        temperature=0.7,
        max_tokens=150  # Shorter responses
    )
    reply_text = reply if isinstance(reply, str) else (json.dumps(reply, ensure_ascii=False) if isinstance(reply, (dict, list)) else str(reply))

    print(f"\n{'='*80}")
    print(f"[🔧 CONTRACTOR HANDLER] AI RESPONSE:")
    print(f"{'='*80}")
    print(reply_text)
    print(f"{'='*80}\n")

    # Post text response to channel
    post_agent_message(client, channel_id, reply_text)
    print(f"[🔧 CONTRACTOR HANDLER] ✅ Posted contractor onboarding response to channel {channel_id}")

    # Spawn interactive card if needed
    if card_to_spawn:
        print(f"[🔧 CONTRACTOR HANDLER] 🎴 Spawning card: {card_to_spawn}")
        _send_contractor_card(client, channel_id, card_to_spawn, card_metadata)
        print(f"[🔧 CONTRACTOR HANDLER] ✅ Posted {card_to_spawn} card to channel {channel_id}")


def _send_contractor_card(client: Any, channel_id: str, card_type: str, extra_metadata: Dict[str, Any] = None) -> None:
    """
    Send an interactive card message to the contractor chat.
    Cards are rendered by ContractorChatPane when it detects card_type in metadata.
    """
    from ..services.chatbot import ensure_agent_user, AGENT_USER_ID

    if StreamChat is None:
        raise RuntimeError("stream-chat SDK not installed")

    ensure_agent_user(client)

    # Parse channel type and ID
    channel_type, parsed_channel_id = (
        tuple(channel_id.split(":", 1)) if ":" in channel_id
        else ("messaging", channel_id)
    )

    channel = client.channel(channel_type, parsed_channel_id)

    # Build card metadata
    card_metadata = {
        "card_type": card_type,
        "is_card": True,
        **(extra_metadata or {})
    }

    # Send card message (empty text, metadata triggers card rendering)
    print(f"[card-sender] Sending {card_type} card with metadata: {card_metadata}")
    channel.send_message({
        "text": "",  # Empty text - card is rendered by metadata
        "metadata": card_metadata,
        "type": "regular"
    }, user_id=AGENT_USER_ID)


async def _handle_landlord_message(
    client: Any,
    channel,
    channel_state: Dict[str, Any],
    message: Dict[str, Any],
    persona: Optional[str] = None,
) -> None:
    """
    Handle landlord messages with landlord-specific AI responses.
    Focus on property management, tenant issues, contractor approvals.
    """
    channel_id = _channel_identifier(channel, channel_state)
    message_text = message.get("text", "").strip()

    if not message_text:
        return

    # Build context from recent messages
    messages = channel_state.get("messages", [])
    recent_messages = messages[-5:] if len(messages) > 5 else messages
    context_lines = []
    for msg in recent_messages:
        user_id = msg.get("user", {}).get("id", "unknown")
        text = msg.get("text", "")
        context_lines.append(f"{user_id}: {text}")
    context = "\n".join(context_lines)

    # Landlord-specific prompt
    prompt = (
        f"You are a property management assistant for landlords. "
        f"Recent conversation:\n{context}\n\n"
        f"Landlord said: {message_text}\n\n"
        f"Respond helpfully about:\n"
        f"- Reviewing and approving maintenance requests\n"
        f"- Managing properties and tenants\n"
        f"- Contractor bids and work orders\n"
        f"- Property analytics and reports\n"
        f"- Cost management and budgets\n\n"
        f"Keep it professional and focused on landlord concerns. "
        f"Provide actionable insights and clear next steps."
    )

    # Generate AI response using SIMPLE CONVERSATIONAL mode (NOT the tenant analysis framework)
    print(f"[landlord-handler] Calling get_simple_conversational_response_async (BYPASS tenant analysis)")
    landlord_system_prompt = (
        "You are a professional property management assistant for landlords. "
        "Your role is to help with:\n"
        "- Reviewing and approving maintenance requests\n"
        "- Managing properties and tenants\n"
        "- Evaluating contractor bids and work orders\n"
        "- Property analytics and reports\n"
        "- Cost management and budgets\n\n"
        "Always be professional, data-driven, and provide clear actionable insights. "
        "Focus on helping landlords make informed decisions about their properties."
    )
    reply = await get_simple_conversational_response_async(
        system_prompt=landlord_system_prompt,
        user_message=prompt,
        temperature=0.5,
        max_tokens=512
    )
    reply_text = reply if isinstance(reply, str) else (json.dumps(reply, ensure_ascii=False) if isinstance(reply, (dict, list)) else str(reply))

    # Post response to channel
    post_agent_message(client, channel_id, reply_text)
    print(f"[landlord-handler] Posted landlord response")


@router.post("/chat/stream/webhook")
# @router.post("/ai/stream-webhook")  # Alternative path for compatibility
async def stream_webhook(request: Request):
    """
    Stream Chat webhook endpoint that receives message.new and other events.
    Handles both regular messages and action button clicks.
    """
    # Comprehensive logging for debugging
    print(f"\n{'='*80}")
    print(f"[🔔 WEBHOOK] Incoming Stream event")
    print(f"{'='*80}")

    # if not WEBHOOK_SECRET:
    #     print("[❌ WEBHOOK] ERROR: Stream webhook secret not configured")
    #     raise HTTPException(status_code=501, detail="Stream webhook secret not configured")

    body = await request.body()
    print(f"[📦 WEBHOOK] Payload size: {len(body)} bytes")
    print(f"[📥 WEBHOOK] Payload preview: {body.decode('utf-8', errors='ignore')}")
    signature = request.headers.get("X-Signature", "")

    # # Log headers for debugging
    # print(f"[📋 WEBHOOK] Headers: X-Signature={'*' * 8 if signature else 'MISSING'}")

    # if not verify_stream_signature(body, signature, WEBHOOK_SECRET):
    #     print("[❌ WEBHOOK] ERROR: Invalid Stream signature")
    #     raise HTTPException(status_code=401, detail="Invalid Stream signature")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as e:
        print(f"[❌ WEBHOOK] ERROR: Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Log event type
    event_type = payload.get("type", "unknown")
    print(f"[📨 WEBHOOK] Event type: {event_type}")

    # Handle different event types
    if event_type != "message.new":
        print(f"[⏭️  WEBHOOK] Ignoring event type: {event_type}")
        return {"status": "ignored", "reason": f"event_type_{event_type}"}

    message = payload.get("message") or {}
    message_text = message.get("text", "").strip()
    message_id = message.get("id", "unknown")
    user_id = message.get("user", {}).get("id", "unknown")

    print(f"[💬 WEBHOOK] Message ID: {message_id}")
    print(f"[👤 WEBHOOK] User ID: {user_id}")
    print(f"[📝 WEBHOOK] Message text: {message_text[:100]}{'...' if len(message_text) > 100 else ''}")

    # Log attachments if present
    attachments = message.get("attachments", [])
    if attachments:
        print(f"[📎 WEBHOOK] ✅ Message has {len(attachments)} attachment(s)")
        for idx, attachment in enumerate(attachments):
            print(f"[📎 WEBHOOK] Attachment {idx + 1}: type={attachment.get('type')}, {attachment}")
    else:
        print(f"[📎 WEBHOOK] ⚠️ No attachments in message")

    # Ignore messages from our AI agent
    if user_id == AGENT_USER_ID:
        print(f"[⏭️  WEBHOOK] Ignoring message from AI agent: {AGENT_USER_ID}")
        return {"status": "ignored", "reason": "agent_message"}

    # Validate channel ID
    cid = payload.get("channel_id")
    print(f"[📺 WEBHOOK] Full message: {message}")
    print(f"[📺 WEBHOOK] Channel ID: {cid}")
    if not cid:
        print(f"[❌ WEBHOOK] ERROR: Invalid channel ID: {cid}")
        return {"status": "ignored", "reason": "invalid_cid"}

    channel_type, channel_id = cid.split(":", 1)
    print(f"[📺 WEBHOOK] Channel: {channel_type}:{channel_id}")

    # Get channel state
    client = _get_stream_client()
    bot_ensure_agent_user(client)
    channel = client.channel(channel_type, channel_id)
    channel_state = channel.query(state=True, watch=False)
    # Enrich channel_state with useful metadata snapshot to aid reasoning and discovery
    channel_data = channel_state.get("channel", {}).get("data", {}) or {}
    channel_state["metadata"] = {
        "timestamp": time.time(),
        "persona": channel_data.get("persona", "tenant"),
        "active_incident": channel_data.get("active_incident"),
        "active_job": channel_data.get("active_job"),
        "flow_state": channel_data.get("flow_state", {}),
        "incident_details": channel_data.get("incident_details", {}),
        "context_snapshot": [
            {
                "user": msg.get("user", {}).get("id"),
                "text": msg.get("text"),
                "ts": msg.get("created_at"),
            }
            for msg in channel_state.get("messages", [])[-10:]
        ],
    }

    # Extract persona from message metadata first, fall back to channel data
    message_metadata = message.get("metadata", {})
    persona = message_metadata.get("persona") or channel_data.get("persona") or "tenant"

    # AGGRESSIVE LOGGING FOR DEBUGGING
    print(f"\n{'='*80}")
    print(f"[🔍 PERSONA DEBUG] Message metadata: {json.dumps(message_metadata, indent=2)}")
    print(f"[🔍 PERSONA DEBUG] Channel data persona: {channel_data.get('persona')}")
    print(f"[🔍 PERSONA DEBUG] Final persona: {persona}")
    print(f"[🔍 PERSONA DEBUG] Persona source: {'message metadata' if message_metadata.get('persona') else 'channel data' if channel_data.get('persona') else 'default (tenant)'}")
    print(f"{'='*80}\n")

    discovery = channel_data.get("discovery") or {}

    print(f"[👔 WEBHOOK] Persona: {persona} (from: {'message metadata' if message_metadata.get('persona') else 'channel data'})")
    print(f"[🔍 WEBHOOK] Discovery stage: {discovery.get('stage', 'none')}")

    # Print a concise channel summary for logging / dashboards
    try:
        summary = summarize_channel_state(channel_state)
        print(f"[channel-summary] {json.dumps(summary, indent=2)}")
    except Exception as e:
        print(f"[channel-summary] failed: {e}")

    # Run lightweight AI analysis for classification and suggested next actions
    try:
        reasoning = get_ai_reasoning()
        ai_result = reasoning.infer_intent(message_text, {"recent_conversation": channel_state.get("messages", [])}, persona or "tenant")
        # Ensure ai_analysis exists (from LLM or fallback)
        ai_analysis = ai_result.get("ai_analysis") or ai_result.get("entities") or reasoning._analyze_message_fallback(message_text)
        channel_state.setdefault("ai_analysis", ai_analysis)
        print(f"[ai-analysis] {json.dumps(ai_analysis, indent=2)}")

        # Enrich metadata with unified flow intelligence
        category = ai_analysis.get("category") or channel_state.get("metadata", {}).get("incident_details", {}).get("category")
        urgency = ai_analysis.get("urgency") or channel_state.get("metadata", {}).get("incident_details", {}).get("urgency")
        severity = ai_analysis.get("severity") or channel_state.get("metadata", {}).get("incident_details", {}).get("severity")
        created_at = channel_state.get("metadata", {}).get("timestamp") or time.time()
        # Simple priority score: severity weight (high=3, medium=2, low=1) * urgency weight * recency factor
        sev_weight = {"high": 3, "medium": 2, "low": 1}.get(severity, 2)
        urg_weight = {"immediate": 4, "urgent": 3, "routine": 1}.get(urgency, 1)
        age_hours = max(0.1, (time.time() - float(created_at)) / 3600.0)
        priority_score = round((sev_weight * urg_weight) / age_hours, 3)

        # Populate standardized metadata fields
        meta = channel_state.setdefault("metadata", {})
        meta.update({
            "urgency_level": urgency,
            "category": category,
            "priority_score": priority_score,
            "assigned_contractor": channel_data.get("assigned_contractor"),
            "tenant_id": channel_data.get("tenant_id") or message.get("user", {}).get("id"),
            "landlord_id": channel_data.get("landlord_id"),
            "mttr_target_hours": channel_data.get("mttr_target_hours") or (8 if urgency == "immediate" else 48),
            "status_metric_flags": channel_data.get("status_metric_flags", {}),
        })

        # Emit SLA metrics log
        sla_payload = {
            "channel_id": channel_id,
            "incident_id": channel_data.get("active_incident"),
            "priority_score": priority_score,
            "mttr_target_hours": meta.get("mttr_target_hours"),
        }
        print(f"[sla-metrics] {json.dumps(sla_payload)}")

    except Exception as e:
        print(f"[ai-analysis] failed to analyze message: {e}")

    # Check if this is an action message (button click)
    if message_text.startswith("action:"):
        print(f"[🎯 WEBHOOK] ACTION DETECTED: {message_text}")
        _handle_action_message(client, channel, channel_state, message, persona)
        print(f"[✅ WEBHOOK] Action handled successfully")
        return {"status": "ok", "action_handled": True}

    # Route based on persona
    print(f"\n{'⚡'*40}")
    print(f"[⚡ ROUTING] Persona value: '{persona}'")
    print(f"[⚡ ROUTING] Type: {type(persona)}")
    print(f"[⚡ ROUTING] Checking equality: persona == 'contractor_onboarding' = {persona == 'contractor_onboarding'}")
    print(f"[⚡ ROUTING] Checking equality: persona == 'landlord' = {persona == 'landlord'}")
    print(f"{'⚡'*40}\n")

    if persona == "contractor_onboarding":
        print(f"[🔧 WEBHOOK] ✅ ROUTING TO CONTRACTOR ONBOARDING HANDLER")
        await _handle_contractor_message(client, channel, channel_state, message, persona)
        print(f"[✅ WEBHOOK] Contractor message handled successfully")
        print(f"{'='*80}\n")
        return {"status": "ok", "persona": "contractor_onboarding"}
    elif persona == "landlord":
        print(f"[🏠 WEBHOOK] ✅ ROUTING TO LANDLORD HANDLER")
        await _handle_landlord_message(client, channel, channel_state, message, persona)
        print(f"[✅ WEBHOOK] Landlord message handled successfully")
        print(f"{'='*80}\n")
        return {"status": "ok", "persona": "landlord"}
    else:
        # Default to tenant intelligent handler with discovery flows
        print(f"[🧠 WEBHOOK] ⚠️  ROUTING TO TENANT HANDLER (DEFAULT) - persona='{persona}'")
        _handle_intelligent_message(client, channel, channel_state, message, persona)
        print(f"[✅ WEBHOOK] Tenant message handled successfully")
        print(f"{'='*80}\n")
        return {"status": "ok", "persona": "tenant"}


def summarize_channel_state(channel_state: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts high-value keys for logging, dashboards, and AI context."""
    from pathlib import Path; Path("my_file.json").write_text(json.dumps(channel_state))
    data = channel_state.get("channel", {}).get("data", {})
    meta = channel_state.get("metadata", {})
    return {
        "channel_id": data.get("id"),
        "persona": data.get("persona"),
        "incident_id": data.get("active_incident"),
        "flow_stage": meta.get("flow_state", {}).get("stage"),
        "summary": data.get("incident_details", {}).get("summary"),
        "severity": data.get("incident_details", {}).get("severity"),
        "timestamp": meta.get("timestamp"),
    }


@router.get("/metrics/tenant/{tenant_id}")
def metrics_tenant(tenant_id: str, token: str = Depends(verify_firebase_token)):
    metrics = get_aggregated_metrics("tenant", tenant_id)
    print(f"[metrics] tenant {tenant_id}: {metrics}")
    return metrics


@router.get("/metrics/landlord/{landlord_id}")
def metrics_landlord(landlord_id: str, token: str = Depends(verify_firebase_token)):
    metrics = get_aggregated_metrics("landlord", landlord_id)
    print(f"[metrics] landlord {landlord_id}: {metrics}")
    return metrics


@router.get("/metrics/contractor/{contractor_id}")
def metrics_contractor(contractor_id: str, token: str = Depends(verify_firebase_token)):
    metrics = get_aggregated_metrics("contractor", contractor_id)
    print(f"[metrics] contractor {contractor_id}: {metrics}")
    return metrics
