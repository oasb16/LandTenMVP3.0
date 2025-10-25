import os
from typing import List, Dict, Any, Optional

from app.services.ai_service import get_ai_response

try:  # pragma: no cover
    from stream_chat import StreamChat
    from stream_chat.base.exceptions import StreamAPIException
except ImportError:  # pragma: no cover
    StreamChat = None  # type: ignore
    StreamAPIException = Exception  # type: ignore

AGENT_USER_ID = os.getenv("STREAM_AGENT_USER_ID", "landten-agent")
AGENT_DISPLAY_NAME = os.getenv("STREAM_AGENT_NAME", "LandTen Agent")
AGENT_ROLE = os.getenv("STREAM_AGENT_ROLE", "agent")
AGENT_PERSONA = os.getenv("STREAM_AGENT_PERSONA", "assistant")


def ensure_agent_user(client: "StreamChat") -> Optional[str]:
    if StreamChat is None:
        return None
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
        print(f"[stream-bot] failed to upsert agent user: {exc}")
    return AGENT_USER_ID


def build_context(messages: List[Dict[str, Any]], limit: int = 10) -> str:
    recent = messages[-limit:]
    lines = []
    for msg in recent:
        user = msg.get("user", {})
        speaker = user.get("name") or user.get("id") or msg.get("user_id", "unknown")
        text = msg.get("text") or msg.get("message") or ""
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def agent_reply(prompt: str, context: Optional[str], persona: Optional[str]) -> str:
    if context:
        combined = f"Context:\n{context}\n\nUser:\n{prompt}"
    else:
        combined = prompt
    return get_ai_response(combined, persona=persona, context=context)


def post_agent_message(client: "StreamChat", channel_id: str, text: str, msg_type: str = "agent") -> None:
    if StreamChat is None:
        raise RuntimeError("stream-chat SDK not installed")
    ensure_agent_user(client)
    channel = client.channel("messaging", channel_id)
    channel.send_message({"text": text, "type": msg_type}, user_id=AGENT_USER_ID)
