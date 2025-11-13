import os,json
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


def get_ai_response(message: str,
                    persona: Optional[str] = None,
                    context: Optional[str] = None,
                    n_refine: int = 3) -> str:
    """
    TRM-style recursive reasoning loop for a stateless OpenAI API.
    Each loop refines the previous reasoning (z) and answer (y).
    """

    system_prompt = os.getenv(
        "AGENT_SYSTEM_PROMPT",
        "You are LandTen's property-management assistant. "
        "Infer issues, incidents, and actions intelligently."
    )
    if persona:
        system_prompt += f" You are assisting a {persona}."
    if context:
        system_prompt += f" Context: {context}."

    client = _get_openai_client()
    if not client:
        return f"(Agent offline) {message[::-1]}"

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
    def normalize_role(msg_type: str) -> str:
        """
        Normalize StreamChat message types to valid OpenAI chat roles.
        """
        if not msg_type:
            return "user"
        msg_type = msg_type.lower()
        mapping = {
            "regular": "user",
            "agent": "assistant", 
            "ai-message": "assistant",
            "card": "assistant",
            "system": "system",
        }
        return mapping.get(msg_type, "user")
    
    for step in range(n_refine):
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": normalize_role("regular"), "content": prompt + "\n\nRespond strictly in JSON format."},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        response_choices = json.loads(completion.choices)
        print(f"response_choices : {response_choices}")  # Debug print
        raw_content = completion.choices[0].message.content
        print(f"[agent-debug] step={step+1} raw_content={raw_content}")

        try:
            data = json.loads(raw_content)
            reasoning = data.get("reasoning", reasoning)

            # 🧠 Select best field, supporting lists/dicts
            answer = (
                data.get("answer")
                or data.get("reply")
                or data.get("summary")
                or data.get("next_actions")
                or data.get("response")
                or data
                or answer
            )

            # 🔄 Normalize lists/dicts to string for display
            if isinstance(answer, (list, dict)):
                answer = json.dumps(answer, indent=2)

        except Exception as e:
            print(f"[agent-debug] JSON parse error: {e}")
            reasoning += "\n" + str(raw_content)
            answer = str(raw_content).strip()

    # ✅ Safe text fallback
    if not isinstance(answer, str):
        answer = json.dumps(answer, indent=2)
    if not answer.strip():
        answer = "(Agent found no actionable reply.)"

    return answer.strip()

