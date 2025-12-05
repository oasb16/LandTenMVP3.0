"""
AI Message Formatter - Generates consistently structured AI messages
Supports ChatGPT-style expandable messages for frontend CustomMessageUI
"""
from typing import List, Dict, Any, Optional
import json


def format_expandable_message(
    raw_content: str,
    preview_content: Optional[str] = None,
    actions: Optional[List[str]] = None,
    expandable: bool = True,
) -> str:
    """
    Format an AI message in the <ai-expanded> format for frontend parsing.

    Args:
        raw_content: Full message content
        preview_content: Truncated preview (if None, auto-generates from raw_content)
        actions: List of suggested next actions
        expandable: Whether message should be expandable

    Returns:
        Formatted message string in <ai-expanded> format

    Example:
        >>> format_expandable_message(
        ...     raw_content="Long detailed response...",
        ...     preview_content="Short preview...",
        ...     actions=["Upload photos", "Add more details"]
        ... )
    """
    # Auto-generate preview if not provided
    if preview_content is None:
        preview_content = _generate_preview(raw_content, max_length=200)

    # Format actions section
    actions_text = ""
    if actions and len(actions) > 0:
        actions_text = "\n\nACTIONS:\n" + "\n".join(f"- {action}" for action in actions)

    # Build the <ai-expanded> message
    message = f"""<ai-expanded>
RAW:
{raw_content}

PREVIEW:
{preview_content}{actions_text}

EXPANDABLE: {str(expandable).lower()}
</ai-expanded>"""

    return message


def format_structured_json_message(
    summary: str,
    next_actions: Optional[List[Dict[str, str]]] = None,
    analysis: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Format an AI message as structured JSON for frontend AIResponseParser.

    Args:
        summary: Main message summary
        next_actions: List of action dicts with 'action' and optional 'details' keys
        analysis: Additional analysis data

    Returns:
        JSON string that frontend can parse

    Example:
        >>> format_structured_json_message(
        ...     summary="Issue classified as plumbing leak",
        ...     next_actions=[{"action": "Upload photos", "details": "Show the damage"}]
        ... )
    """
    message = {
        "analysis": {
            "summary": summary,
            "next_actions": next_actions or []
        }
    }

    if analysis:
        message["analysis"].update(analysis)

    return json.dumps(message, indent=2)


def format_simple_message_with_actions(
    text: str,
    actions: Optional[List[str]] = None,
    use_json: bool = False,
) -> str:
    """
    Format a simple AI message with optional action suggestions.
    Can output in JSON or <ai-expanded> format.

    Args:
        text: Message text
        actions: List of suggested actions
        use_json: If True, use JSON format; otherwise use <ai-expanded>

    Returns:
        Formatted message string
    """
    if not actions:
        return text

    if use_json:
        return format_structured_json_message(
            summary=text,
            next_actions=[{"action": action} for action in actions]
        )
    else:
        return format_expandable_message(
            raw_content=text,
            actions=actions
        )


def _generate_preview(text: str, max_length: int = 200) -> str:
    """Generate a preview from full text by truncating intelligently."""
    if len(text) <= max_length:
        return text

    # Try to cut at sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind('. ')

    if last_period > max_length * 0.7:
        return truncated[:last_period + 1]

    # Fall back to word boundary
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space] + "..."

    return truncated + "..."


def should_use_expandable_format(text: str, threshold: int = 300) -> bool:
    """
    Determine if a message should use expandable format.

    Args:
        text: Message text
        threshold: Character count threshold for expandable format

    Returns:
        True if message should be expandable
    """
    return len(text) > threshold
