import os
from typing import Optional

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore


_openai_client: Optional["OpenAI"] = None


def _get_openai_client() -> Optional["OpenAI"]:
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI is None or not api_key:
        return None
    _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def get_ai_response(message: str, persona: Optional[str] = None, context: Optional[str] = None) -> str:
    """Return an agent response using OpenAI when configured, else lightweight fallback."""

    system_prompt = os.getenv(
        "AGENT_SYSTEM_PROMPT",
        "You are LandTen's helpful assistant. Provide concise, actionable guidance for property management scenarios.",
    )
    if persona:
        system_prompt += f" You are currently supporting the {persona} persona."
    if context:
        system_prompt += f" Context: {context}."

    client = _get_openai_client()
    if client:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            )
            content = completion.choices[0].message.content if completion.choices else None
            if content:
                return content.strip()
        except Exception as exc:  # pragma: no cover - best effort logging
            print(f"[agent] OpenAI error: {exc}")

    # Fallback when OpenAI not configured or errors out
    return f"(Agent offline) {message[::-1]}"
