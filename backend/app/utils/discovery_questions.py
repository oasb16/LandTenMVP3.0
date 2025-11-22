"""
Discovery Question System
Provides adaptive, category-specific diagnostic questions for incident follow-up.
"""

from typing import List, Dict, Any, Optional


# Category-specific question templates
DISCOVERY_QUESTION_LIBRARY: Dict[str, List[str]] = {
    "plumbing": [
        "Is water actively leaking right now, or has it stopped?",
        "Where exactly is the leak located? (e.g., under sink, toilet, ceiling)",
        "How severe is the leak? (dripping, steady stream, flooding)",
        "Can you see any visible water damage (wet spots, stains, bubbling)?",
        "Is the water clear, or does it appear dirty/discolored?",
    ],
    "electrical": [
        "Are you experiencing a complete power outage, or just certain outlets/lights?",
        "Did you notice any burning smell, sparks, or unusual sounds?",
        "Have you checked your circuit breaker panel? Are any breakers tripped?",
        "Which specific rooms or areas are affected?",
        "Is this a new issue, or has it been intermittent?",
    ],
    "hvac": [
        "Is the HVAC system making any unusual noises? (grinding, squealing, banging)",
        "Is there any airflow at all, or is it completely stopped?",
        "What temperature is the thermostat set to, and what's the current room temperature?",
        "Have you noticed any unusual smells coming from the vents?",
        "When did you first notice the heating/cooling problem?",
    ],
    "structural": [
        "Where exactly is the structural issue located?",
        "Can you describe what you're seeing? (cracks, sagging, separation, etc.)",
        "How long have you noticed this issue?",
        "Has it gotten worse recently, or stayed the same?",
        "Is there any visible water damage near the affected area?",
    ],
    "appliance": [
        "Which appliance is having the issue? (refrigerator, stove, dishwasher, etc.)",
        "What exactly is happening with the appliance?",
        "Is the appliance under warranty, or how old is it?",
        "Have you tried unplugging it and plugging it back in?",
        "Are there any error codes or lights flashing?",
    ],
    "locks": [
        "Which lock is the issue with? (front door, back door, window, etc.)",
        "Is the lock completely broken, stuck, or just difficult to use?",
        "Can you currently lock/unlock the door at all?",
        "Is this a security concern (cannot lock), or an access issue (cannot unlock)?",
        "When did the lock start having problems?",
    ],
    "pest": [
        "What type of pest have you seen? (rodents, insects, other)",
        "Where have you noticed the pest activity? (kitchen, bathroom, multiple rooms)",
        "How frequently are you seeing them? (daily, occasionally, just once)",
        "Have you noticed any droppings, nests, or damage?",
        "Is this a new problem, or ongoing?",
    ],
    "noise": [
        "What type of noise are you hearing? (banging, grinding, squeaking, buzzing)",
        "Where is the noise coming from?",
        "When does the noise occur? (constantly, at certain times, when using specific things)",
        "How loud is the noise? (barely noticeable, annoying, disruptive)",
        "Has the noise changed or gotten worse recently?",
    ],
    "safety": [
        "What is the immediate safety concern?",
        "Is anyone in danger right now?",
        "Have you contacted emergency services if needed?",
        "Can you safely stay in the property, or do you need alternative arrangements?",
        "Are there any children, elderly, or pets affected?",
    ],
    "general": [
        "Can you describe the issue in more detail?",
        "When did you first notice this problem?",
        "Has this happened before, or is this the first time?",
        "Is this affecting your ability to use the property normally?",
        "Are there any other related issues you've noticed?",
    ],
}


# Severity-based question modifiers
SEVERITY_MODIFIERS: Dict[str, List[str]] = {
    "emergency": [
        "Is anyone in immediate danger?",
        "Do you need to evacuate the property?",
        "Have you contacted emergency services (911, fire, police)?",
    ],
    "high": [
        "Is the issue getting worse right now?",
        "Is this preventing you from using essential services (water, power, heat)?",
    ],
    "medium": [
        "How much is this affecting your daily routine?",
    ],
    "low": [
        "Is this issue urgent, or can it wait for regular business hours?",
    ],
}


def get_discovery_questions(
    category: str,
    severity: str,
    user_message: str,
    max_questions: int = 5
) -> List[str]:
    """
    Returns a progressive list of follow-up diagnostic questions.

    Args:
        category: Incident category (plumbing, electrical, hvac, etc.)
        severity: Severity level (emergency, high, medium, low)
        user_message: Original user message (to avoid duplicate questions)
        max_questions: Maximum number of questions to return

    Returns:
        List of diagnostic questions tailored to category and severity
    """
    # Normalize inputs
    category = category.lower().strip()
    severity = severity.lower().strip()

    # Get base questions for category
    questions = DISCOVERY_QUESTION_LIBRARY.get(category, DISCOVERY_QUESTION_LIBRARY["general"]).copy()

    # Add severity-specific questions if emergency/high
    if severity in ["emergency", "high"]:
        severity_questions = SEVERITY_MODIFIERS.get(severity, [])
        questions = severity_questions + questions

    # Filter out questions already answered in user_message
    filtered_questions = []
    user_message_lower = user_message.lower()

    for question in questions:
        question_lower = question.lower()

        # Skip if question seems already answered
        # (e.g., if question asks "where is leak?" and user already said "under sink")
        skip = False

        # Simple heuristic: if key question words are in user message, skip
        if "where" in question_lower and any(loc in user_message_lower for loc in ["under", "in", "at", "near", "behind"]):
            skip = True
        elif "when" in question_lower and any(time in user_message_lower for time in ["today", "yesterday", "hour", "minute", "ago"]):
            skip = True
        elif "smell" in question_lower and "smell" in user_message_lower:
            skip = True

        if not skip:
            filtered_questions.append(question)

    # Limit to max_questions
    return filtered_questions[:max_questions]


def get_first_discovery_question(
    category: str,
    severity: str,
    user_message: str
) -> str:
    """
    Returns the first discovery question to ask immediately after incident creation.

    Args:
        category: Incident category
        severity: Severity level
        user_message: Original user message

    Returns:
        Single question string
    """
    questions = get_discovery_questions(category, severity, user_message, max_questions=1)
    return questions[0] if questions else "Can you provide more details about what you're experiencing?"


def format_discovery_questions_message(
    questions: List[str],
    incident_id: str,
    current_index: int = 0
) -> str:
    """
    Formats multiple discovery questions as a numbered list message.

    Args:
        questions: List of questions
        incident_id: Associated incident ID
        current_index: Current question index (for progress tracking)

    Returns:
        Formatted markdown message
    """
    if not questions:
        return "Thank you for the information. We'll process your incident now."

    total = len(questions)

    # Build progress bar
    progress_bar = "▓" * (current_index + 1) + "░" * (total - current_index - 1)

    lines = [
        "🔍 **Discovery Questions**",
        "",
        f"**Incident:** {incident_id}",
        f"Progress: [{progress_bar}] {current_index + 1}/{total}",
        "",
        "Please answer the following to help us diagnose the issue:",
        "",
    ]

    # Add numbered questions
    for i, question in enumerate(questions, 1):
        lines.append(f"{i}. {question}")

    lines.extend([
        "",
        "_You can answer all at once or one at a time._",
    ])

    return "\n".join(lines)


def should_ask_discovery_questions(category: str, severity: str) -> bool:
    """
    Determines if discovery questions should be asked for this incident.

    Args:
        category: Incident category
        severity: Severity level

    Returns:
        True if discovery questions are appropriate
    """
    # Always ask for specific categories
    specific_categories = ["plumbing", "electrical", "hvac", "structural", "appliance"]

    if category.lower() in specific_categories:
        return True

    # For emergency/high severity, always gather more info
    if severity.lower() in ["emergency", "high"]:
        return True

    # For general/other categories with low severity, may skip
    return category.lower() != "general" or severity.lower() != "low"
