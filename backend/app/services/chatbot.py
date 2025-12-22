import os
from typing import List, Dict, Any, Optional

from ..services.ai_service import get_ai_response, get_ai_response_async

try:  # pragma: no cover
    from stream_chat import StreamChat
    from stream_chat.base.exceptions import StreamAPIException
except ImportError:  # pragma: no cover
    StreamChat = None  # type: ignore
    StreamAPIException = Exception  # type: ignore

AGENT_USER_ID = os.getenv("STREAM_AGENT_USER_ID", "landten-agent")
AGENT_DISPLAY_NAME = os.getenv("STREAM_AGENT_NAME", "LandTen Agent")
AGENT_ROLE = os.getenv("STREAM_AGENT_ROLE", "user")
AGENT_PERSONA = os.getenv("STREAM_AGENT_PERSONA", "assistant")


def ensure_agent_user(client: Any) -> Optional[str]:
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


async def agent_reply_async(prompt: str, context: Optional[str], persona: Optional[str]) -> str:
    """Async version of agent_reply for use in async webhook handlers"""
    if context:
        combined = f"Context:\n{context}\n\nUser:\n{prompt}"
    else:
        combined = prompt
    return await get_ai_response_async(combined, persona=persona, context=context)


async def get_simple_conversational_response_async(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> str:
    """
    Simple, direct conversational AI call WITHOUT the 3-step refinement loop.

    Use this for contractor/landlord onboarding where we need natural conversation,
    NOT structured JSON incident analysis.

    Args:
        system_prompt: System instructions for the AI
        user_message: The user's message to respond to
        temperature: Creativity level (0.7 = balanced)
        max_tokens: Max response length

    Returns:
        Natural conversational text response
    """
    from .openai_wrapper import get_openai_wrapper, RateLimitExceeded
    import os
    import logging

    logger = logging.getLogger(__name__)

    try:
        openai_wrapper = get_openai_wrapper()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        logger.info(f"🤖 [Simple Conversational] Sending to OpenAI")
        logger.info(f"🤖 [Simple Conversational] System: {system_prompt[:100]}...")
        logger.info(f"🤖 [Simple Conversational] User: {user_message[:100]}...")

        response = await openai_wrapper.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        reply = response.choices[0].message.content.strip()
        logger.info(f"✅ [Simple Conversational] Response: {reply[:100]}...")

        return reply

    except RateLimitExceeded:
        return "I'm experiencing high demand right now. Please try again in a moment!"

    except Exception as e:
        logger.error(f"❌ [Simple Conversational] Error: {e}", exc_info=True)
        return f"I apologize, but I encountered an error. Please try again."


def post_agent_message(client: Any, channel_id: str, text: str, msg_type: str = "agent") -> None:
    if StreamChat is None:
        raise RuntimeError("stream-chat SDK not installed")
    ensure_agent_user(client)
    channel = client.channel("messaging", channel_id)
    channel_type, channel_id = (tuple(channel_id.split(":", 1)) if ":" in channel_id else ("messaging", channel_id)); channel = client.channel(channel_type, channel_id)
    print(f"[stream-bot] Preparing to post {msg_type} message to channel {channel_id} to channel type {channel_type}")
    if msg_type not in ["regular", "system"]:
        msg_type = "regular"
    # If text is JSON-like with message + next_steps, use bot helper to render card
    try:
        from ..services.stream_bot import get_bot

        bot = get_bot()
        # Use send_ai_message which will detect JSON and render cards
        bot.send_ai_message(channel_id=channel_id, persona=AGENT_PERSONA, text=text, metadata={"context_type": "agent"})
        return
    except Exception:
        # Fallback to legacy behavior
        print(f"[stream-bot] posting {msg_type} message to channel {channel_id}: {text}")
        channel_type, channel_id = (tuple(channel_id.split(":", 1)) if ":" in channel_id else ("messaging", channel_id))
        print(f"[stream-bot] Sending message to channel {channel_id} of type {channel_type}")
        channel.send_message({"text": text, "type": msg_type}, user_id=AGENT_USER_ID)
