"""
Message Card Formatters for Stream Chat
Creates beautiful, structured messages for incidents, discovery, and attachments.
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime


def format_incident_card(incident_data: Dict[str, Any]) -> str:
    """
    Formats incident data as a beautiful card-like message.

    Args:
        incident_data: Dict containing incident_id, title, category, severity, urgency, etc.

    Returns:
        Formatted markdown string for Stream Chat
    """
    incident_id = incident_data.get("incident_id", "INC-XXXXX")
    title = incident_data.get("title", "Maintenance Issue")
    category = incident_data.get("category", "General").capitalize()
    severity = incident_data.get("severity", "Medium").capitalize()
    urgency = incident_data.get("urgency", "Routine").capitalize()
    description = incident_data.get("description", "")

    # Severity emoji mapping
    severity_emoji = {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🟠",
        "Emergency": "🔴",
    }

    # Urgency emoji mapping
    urgency_emoji = {
        "Routine": "📅",
        "Urgent": "⚡",
        "Immediate": "🚨",
    }

    severity_icon = severity_emoji.get(severity, "⚪")
    urgency_icon = urgency_emoji.get(urgency, "📌")

    # Build the card
    card_lines = [
        "✅ **Incident Reported**",
        "",
        f"**Incident ID:** {incident_id}",
        f"**Title:** {title}",
        f"**Category:** {category}",
        f"**Severity:** {severity_icon} {severity}",
        f"**Urgency:** {urgency_icon} {urgency}",
    ]

    # Add description if present and not too long
    if description and description != title:
        short_desc = description[:200] + "..." if len(description) > 200 else description
        card_lines.extend([
            "",
            f"**Details:** {short_desc}",
        ])

    card_lines.extend([
        "",
        "📋 We'll gather more details to help resolve this quickly.",
    ])

    return "\n".join(card_lines)


def collapse_long_text(text: str, max_length: int = 300) -> Tuple[str, Optional[str]]:
    """
    Collapses long text into preview + full version.

    Args:
        text: Original text
        max_length: Maximum preview length (default 300)

    Returns:
        Tuple of (preview_text, full_text)
        - If text is short, returns (text, None)
        - If text is long, returns (truncated_preview, full_text)
    """
    if len(text) <= max_length:
        return (text, None)

    # Find a good break point (sentence or word boundary)
    preview = text[:max_length]

    # Try to break at sentence
    last_period = preview.rfind(". ")
    if last_period > max_length * 0.7:  # At least 70% through
        preview = preview[:last_period + 1]
    else:
        # Break at last word
        last_space = preview.rfind(" ")
        if last_space > 0:
            preview = preview[:last_space]

    preview_with_indicator = f"{preview}...\n\n_[Message truncated - tap to expand]_"

    return (preview_with_indicator, text)


def format_attachment_card(attachment_info: Dict[str, Any]) -> str:
    """
    Formats attachment confirmation message.

    Args:
        attachment_info: Dict with url, filename, content_type, etc.

    Returns:
        Formatted confirmation message
    """
    filename = attachment_info.get("filename", "file")
    content_type = attachment_info.get("content_type", "unknown")
    url = attachment_info.get("url", "")

    # Determine file type icon
    if content_type.startswith("image/"):
        icon = "🖼️"
        file_type = "Image"
    elif content_type.startswith("video/"):
        icon = "🎥"
        file_type = "Video"
    elif content_type.startswith("application/pdf"):
        icon = "📄"
        file_type = "PDF"
    else:
        icon = "📎"
        file_type = "File"

    card_lines = [
        f"{icon} **Attachment Received**",
        "",
        f"**Type:** {file_type}",
        f"**Name:** {filename}",
    ]

    if url:
        card_lines.append(f"**URL:** {url}")

    card_lines.extend([
        "",
        "✅ Your file has been uploaded successfully.",
    ])

    return "\n".join(card_lines)


def format_discovery_progress(
    question_index: int,
    total_questions: int,
    current_question: str
) -> str:
    """
    Formats discovery question with progress indicator.

    Args:
        question_index: Current question index (0-based)
        total_questions: Total number of questions
        current_question: The question text

    Returns:
        Formatted discovery question message
    """
    progress_num = question_index + 1
    progress_bar = "▓" * progress_num + "░" * (total_questions - progress_num)

    card_lines = [
        "🔍 **Discovery Question**",
        "",
        f"Progress: [{progress_bar}] {progress_num}/{total_questions}",
        "",
        f"**Q{progress_num}:** {current_question}",
        "",
        "_Please answer to help us understand the issue better._",
    ]

    return "\n".join(card_lines)


def format_discovery_complete(incident_id: str, summary: str) -> str:
    """
    Formats discovery completion message.

    Args:
        incident_id: The incident ID
        summary: Brief summary of gathered info

    Returns:
        Formatted completion message
    """
    card_lines = [
        "✅ **Discovery Complete**",
        "",
        f"**Incident:** {incident_id}",
        "",
        "Thank you for providing the details! Here's what we've gathered:",
        "",
        summary,
        "",
        "🔧 We'll create a work order to address this issue.",
    ]

    return "\n".join(card_lines)


def format_work_order_card(job_data: Dict[str, Any]) -> str:
    """
    Formats work order creation message.

    Args:
        job_data: Dict containing job_id, title, estimated_cost, etc.

    Returns:
        Formatted work order message
    """
    job_id = job_data.get("job_id", "JOB-XXXXX")
    title = job_data.get("title", "Repair Work")
    estimated_cost = job_data.get("estimated_cost", "TBD")
    urgency = job_data.get("urgency", "Routine").capitalize()
    category = job_data.get("category", "General").capitalize()

    card_lines = [
        "🔧 **Work Order Created**",
        "",
        f"**Job ID:** {job_id}",
        f"**Title:** {title}",
        f"**Category:** {category}",
        f"**Urgency:** {urgency}",
        f"**Estimated Cost:** ${estimated_cost}",
        "",
        "📋 This work order has been submitted for landlord approval.",
        "You'll be notified once it's approved and a contractor is assigned.",
    ]

    return "\n".join(card_lines)


def format_error_card(error_type: str, error_message: str, context: Optional[str] = None) -> str:
    """
    Formats error message in a user-friendly way.

    Args:
        error_type: Type of error (e.g., "Validation", "System")
        error_message: User-friendly error message
        context: Optional context information

    Returns:
        Formatted error message
    """
    card_lines = [
        "⚠️ **Issue Encountered**",
        "",
        f"**Type:** {error_type}",
        f"**Message:** {error_message}",
    ]

    if context:
        card_lines.extend([
            "",
            f"**Context:** {context}",
        ])

    card_lines.extend([
        "",
        "Please try again or contact support if the issue persists.",
    ])

    return "\n".join(card_lines)


def format_numbered_list(items: List[str], title: Optional[str] = None) -> str:
    """
    Formats a list of items as a numbered list.

    Args:
        items: List of strings to format
        title: Optional title for the list

    Returns:
        Formatted numbered list
    """
    lines = []

    if title:
        lines.extend([title, ""])

    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {item}")

    return "\n".join(lines)
