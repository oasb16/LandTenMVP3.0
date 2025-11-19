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
information.

Respond in JSON format with:
- summary: A concise 1-2 sentence summary of your analysis
- full_response: A complete detailed explanation with all relevant information
- next_actions: Array of actionable items, each with:
  - action: Brief action title
  - details: Description of the action
  - responsible_party: Who should take action ("tenant", "landlord", or "both")

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

            # 🧠 Build structured response with summary, full_response, and next_actions
            if data.get("summary") and data.get("full_response"):
                # New structured format
                answer = data
            else:
                # Legacy fallback: try to extract fields
                summary = data.get("summary") or data.get("answer") or data.get("reply") or ""
                full_response = data.get("full_response") or data.get("answer") or data.get("reasoning") or ""
                next_actions = data.get("next_actions") or []

                # Normalize next_actions to have responsible_party
                normalized_actions = []
                for action in next_actions:
                    if isinstance(action, str):
                        normalized_actions.append({
                            "action": action,
                            "details": "",
                            "responsible_party": "both"
                        })
                    elif isinstance(action, dict):
                        normalized_actions.append({
                            "action": action.get("action", ""),
                            "details": action.get("details", ""),
                            "responsible_party": action.get("responsible_party", "both")
                        })

                answer = {
                    "summary": summary,
                    "full_response": full_response,
                    "next_actions": normalized_actions
                }

        except Exception as e:
            print(f"[agent-debug] JSON parse error: {e}")
            reasoning += "\n" + str(raw_content)
            answer = {
                "summary": str(raw_content).strip(),
                "full_response": str(raw_content).strip(),
                "next_actions": []
            }

    # ✅ Return structured JSON string
    if isinstance(answer, dict):
        return json.dumps(answer)
    elif isinstance(answer, str):
        # Legacy string response - wrap in structure
        return json.dumps({
            "summary": answer,
            "full_response": answer,
            "next_actions": []
        })
    else:
        return json.dumps({
            "summary": "(Agent found no actionable reply.)",
            "full_response": "(Agent found no actionable reply.)",
            "next_actions": []
        })

