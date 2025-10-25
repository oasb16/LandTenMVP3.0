import os, json
import re
from uuid import uuid4
from typing import List, Dict, Any, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.deps.auth import verify_firebase_token
from app.deps.stream_signing import verify_stream_signature
from app.services.ai_service import get_ai_response
from app.services.chatbot import (
    ensure_agent_user as bot_ensure_agent_user,
    build_context,
    agent_reply,
    post_agent_message,
)
from app.services.incident_flow import (
    classify_issue,
    diy_suggestions,
    create_incident_record,
    summarize_for_landlord,
    threshold_decision,
    generate_contractor_bids,
)

try:
    from stream_chat import StreamChat
    from stream_chat.base.exceptions import StreamAPIException
except ImportError:  # pragma: no cover
    StreamChat = None  # type: ignore
    StreamAPIException = Exception  # type: ignore


router = APIRouter()


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
    {"key": "location", "prompt": "Where exactly is the leak or issue located?"},
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
    client: "StreamChat",
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

    def ask_question(index: int, acknowledgement: Optional[str] = None):
        question = DISCOVERY_QUESTIONS[index]["prompt"]
        prompt = (
            f"You are assisting a tenant with a maintenance issue. "
            f"{acknowledgement or ''} Ask them: {question}. Keep it short and friendly."
        )
        reply = agent_reply(prompt, context, persona)
        post_agent_message(client, channel_id, reply)

    if not discovery or discovery.get("stage") in {None, "complete"} or "start discovery" in lower_text:
        discovery = {
            "stage": "questions",
            "question_index": 0,
            "answers": {},
            "history": [],
        }
        _persist_discovery(channel, discovery)
        prompt = (
            "A tenant requested help with a maintenance issue. "
            f"Let them know you'll gather a few details and ask the first question: {DISCOVERY_QUESTIONS[0]['prompt']}"
        )
        reply = agent_reply(prompt, context, persona)
        post_agent_message(client, channel_id, reply)
        return

    if discovery.get("stage") == "questions":
        idx = discovery.get("question_index", 0)
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
            post_agent_message(client, channel_id, reply)
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
            post_agent_message(client, channel_id, reply)
            return

        discovery["stage"] = "incident"
        discovery["diy_result"] = "Unresolved"
        _persist_discovery(channel, discovery)
        classification = discovery.get("classification", {})
        summary = discovery.get("summary", message.get("text"))
        tenant_email = message.get("user", {}).get("id", "tenant")
        incident = create_incident_record(
            channel_id,
            tenant_email,
            {
                "category": classification.get("category", "general"),
                "severity": classification.get("severity", "medium"),
                "urgency": classification.get("urgency", "routine"),
                "summary": summary,
                "diy_attempted": True,
                "diy_result": "Unresolved",
                "media": discovery.get("media", []),
            },
        )
        bids = generate_contractor_bids(classification.get("category", "general"))
        decision = threshold_decision(bids[0]["quote"])
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


def _get_stream_client() -> "StreamChat":
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
def get_stream_token(user_id: str, persona: str, token: str = Depends(verify_firebase_token)):
    api_key = os.getenv("STREAM_CHAT_API_KEY")
    allowed_roles = {
        role.strip() for role in os.getenv("STREAM_ALLOWED_ROLES", "user,admin,guest").split(",") if role.strip()
    }
    allowed_roles.add(AGENT_ROLE)

    try:
        client = _get_stream_client()
        bot_ensure_agent_user(client)

        sanitized_user_id = _slugify(user_id, allow_at=True)
        if not sanitized_user_id:
            sanitized_user_id = f"user-{uuid4().hex[:8]}"
            print(f"[stream] sanitized user_id empty; generated {sanitized_user_id}")

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
        channel = client.channel("messaging", DEFAULT_CHANNEL_ID, {"name": "LandTen Conversations"})
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

        token_value = client.create_token(sanitized_user_id)

        return {
            "api_key": api_key,
            "token": token_value,
            "channel_id": DEFAULT_CHANNEL_ID,
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
        members_payload = [{"user_id": mid} for mid in sanitized_members]
        members_payload = json.loads(members_payload)
        print("[stream] members payload:", members_payload)
        channel.create(
            user_id=creator_sanitized,
            data={
                "created_by": {creator_sanitized},
                "name": name or "Conversation",
                "members_meta": member_meta,
                **({"persona": req.persona} if req.persona else {}),
                **req.extra_data
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
    if not req.channel_id:
        raise HTTPException(status_code=400, detail="channel_id required")

    client = _get_stream_client()
    agent_id = bot_ensure_agent_user(client)
    if not agent_id:
        raise HTTPException(status_code=500, detail="Agent user not configured")

    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    # Basic context assembly for AI
    context_lines = []
    if req.context:
        context_lines.append(req.context)
    if req.requesting_user:
        context_lines.append(f"Request from {req.requesting_user}")

    context_text = "\n".join(context_lines) if context_lines else None
    ai_response = get_ai_response(prompt, persona=req.persona, context=context_text)

    channel = client.channel("messaging", req.channel_id)
    try:
        channel.send_message(
            {
                "text": ai_response,
                "type": "agent",
            },
            user_id=agent_id,
        )
    except (KeyError, StreamAPIException) as exc:
        raise HTTPException(status_code=500, detail=f"Stream error posting agent reply: {exc}")

    return {"status": "sent", "agent_id": agent_id, "message": ai_response}
@router.post("/chat/stream/webhook")
async def stream_webhook(request: Request):
    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=501, detail="Stream webhook secret not configured")

    body = await request.body()
    signature = request.headers.get("X-Signature", "")
    if not verify_stream_signature(body, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid Stream signature")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if payload.get("type") != "message.new":
        return {"status": "ignored"}

    message = payload.get("message") or {}
    if message.get("user", {}).get("id") == AGENT_USER_ID:
        return {"status": "ignored"}

    cid = message.get("cid")
    if not cid or ":" not in cid:
        return {"status": "ignored"}
    channel_type, channel_id = cid.split(":", 1)

    client = _get_stream_client()
    bot_ensure_agent_user(client)
    channel = client.channel(channel_type, channel_id)
    channel_state = channel.query(state=True, watch=False)
    channel_data = channel_state.get("channel", {}).get("data", {}) or {}
    persona = channel_data.get("persona")
    discovery = channel_data.get("discovery") or {}

    lower_text = (message.get("text") or "").lower()
    should_handle = False
    if "agent" in lower_text or "start discovery" in lower_text:
        should_handle = True
    if discovery.get("stage") in {"questions", "diy"}:
        should_handle = True

    if not should_handle:
        return {"status": "ignored"}

    _handle_discovery_message(client, channel, channel_state, message, persona)
    return {"status": "ok"}
