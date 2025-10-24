import os, json
import re
from uuid import uuid4
from typing import List, Dict, Any, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps.auth import verify_firebase_token
from app.services.ai_service import get_ai_response

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


def _get_stream_client() -> "StreamChat":
    if StreamChat is None:
        raise HTTPException(status_code=500, detail="stream-chat SDK not installed on backend")
    api_key = os.getenv("STREAM_CHAT_API_KEY")
    api_secret = os.getenv("STREAM_CHAT_API_SECRET")
    if not api_key or not api_secret:
        raise HTTPException(status_code=501, detail="Stream Chat credentials not configured")
    return StreamChat(api_key, api_secret)


def _ensure_agent_user(client: "StreamChat") -> Optional[str]:
    if not AGENT_USER_ID:
        return None
    payload = {
        "id": AGENT_USER_ID,
        "role": AGENT_ROLE,
        "name": AGENT_DISPLAY_NAME,
        "persona": AGENT_PERSONA,
    }
    try:
        client.upsert_user(payload)
    except (KeyError, StreamAPIException) as exc:  # pragma: no cover - logging only
        print(f"[stream] failed to upsert agent user: {exc}")
    return AGENT_USER_ID


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
        _ensure_agent_user(client)

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
    _ensure_agent_user(client)

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
    agent_id = _ensure_agent_user(client)
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
