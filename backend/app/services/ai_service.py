import os,json
import asyncio
from typing import Optional

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore


_openai_client: Optional["OpenAI"] = None


def _get_openai_client() -> Optional["OpenAI"]:
    """
    DEPRECATED: Use get_openai_wrapper() instead for rate-limit awareness.
    Kept for backwards compatibility only.
    """
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI is None or not api_key:
        return None
    # FIXED: Configure retry limits to prevent webhook timeouts
    _openai_client = OpenAI(
        api_key=api_key,
        max_retries=2,  # Limit retries for 429 errors
        timeout=25.0,   # Fail fast if request takes > 25s
    )
    return _openai_client


async def get_ai_response_async(message: str,
                                 persona: Optional[str] = None,
                                 context: Optional[str] = None,
                                 n_refine: int = 3) -> str:
    """
    ASYNC version with rate-limit awareness.
    TRM-style recursive reasoning loop using OpenAI wrapper.
    """
    from .openai_wrapper import get_openai_wrapper, RateLimitExceeded

    system_prompt = os.getenv(
        "AGENT_SYSTEM_PROMPT",
        "You are LandTen's property-management assistant. "
        "Infer issues, incidents, and actions intelligently."
    )
    if persona:
        system_prompt += f" You are assisting a {persona}."
    if context:
        system_prompt += f" Context: {context}."

    openai_wrapper = get_openai_wrapper()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

    reasoning, answer = "", ""
    for step in range(n_refine):
        prompt = f"""
Step {step+1}/{n_refine}.
Previous reasoning: {reasoning or "None"}.
Previous answer: {answer or "None"}.

Analyze the chat below. Decide whether it relates to property
management or maintenance, and if it contains incident-worthy
information. If so, summarize and propose next actions.

Chat:
{message}
"""

        try:
            response = await openai_wrapper.chat_completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt + "\n\nRespond strictly in JSON format."},
                ],
                temperature=temperature,
                max_tokens=1024,
            )

            raw_content = response.choices[0].message.content

            try:
                data = json.loads(raw_content)
                reasoning = data.get("reasoning", reasoning)

                # Select best field
                answer = (
                    data.get("answer")
                    or data.get("reply")
                    or data.get("summary")
                    or data.get("next_actions")
                    or data.get("response")
                    or data
                    or answer
                )

                # Normalize lists/dicts to string
                if isinstance(answer, (list, dict)):
                    answer = json.dumps(answer, indent=2)

            except Exception as e:
                reasoning += "\n" + str(raw_content)
                answer = str(raw_content).strip()

        except RateLimitExceeded:
            return "(Agent temporarily unavailable due to high demand. Please try again shortly.)"

        except Exception as e:
            return f"(Agent error: {str(e)})"

    # Safe text fallback
    if not isinstance(answer, str):
        answer = json.dumps(answer, indent=2)
    if not answer.strip():
        answer = "(Agent found no actionable reply.)"

    return answer.strip()


def get_ai_response(message: str,
                    persona: Optional[str] = None,
                    context: Optional[str] = None,
                    n_refine: int = 3) -> str:
    """
    DEPRECATED: Use get_ai_response_async() instead.

    Synchronous wrapper that calls async version.
    Kept for backwards compatibility with synchronous code.
    """
    # Check if we're already in an async context
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - cannot use asyncio.run()
        # This is a problem - synchronous code called from async context
        # For now, return error message
        return "(Agent error: Synchronous AI call from async context. Use get_ai_response_async() instead.)"
    except RuntimeError:
        # No running loop - we can use asyncio.run()
        return asyncio.run(get_ai_response_async(message, persona, context, n_refine))

