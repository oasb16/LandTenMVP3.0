"""
Creative, persona-specific messages for rate limits, processing, etc.
Because "experiencing high demand" is boring AF.
"""
import random
from typing import Literal

PersonaType = Literal["tenant", "landlord", "contractor"]


def get_processing_message(persona: PersonaType = "tenant") -> str:
    """Get a creative 'working on it' message"""

    messages = {
        "tenant": [
            "On it! Give me just a sec to check this out...",
            "Got it - let me take a look at this for you!",
            "Looking into this now, one moment...",
            "I'm on it! Checking the details...",
            "Let me dig into this real quick...",
            "Processing your request - hang tight!",
            "Give me just a second to pull this up...",
            "Working on this for you right now...",
        ],
        "landlord": [
            "Reviewing this now, one moment...",
            "Let me check the details on this...",
            "Processing - I'll have an update shortly...",
            "Looking into this for you...",
            "Give me just a moment to review...",
            "Pulling up the details now...",
            "On it - checking the property records...",
        ],
        "contractor": [
            "Checking the job details now...",
            "Let me pull up that information...",
            "On it! Give me just a second...",
            "Looking into this for you...",
            "Pulling up the details now...",
            "One sec - checking availability...",
        ]
    }

    return random.choice(messages.get(persona, messages["tenant"]))


def get_rate_limit_message(persona: PersonaType = "tenant", urgent: bool = False) -> str:
    """Get a creative rate limit message"""

    if urgent:
        # For urgent incidents, acknowledge urgency
        urgent_messages = {
            "tenant": [
                "I see this is urgent! I'm swamped right now but I'll prioritize this and get back to you ASAP.",
                "Got it - this is urgent. I'm handling a lot right now but I'll jump on this in just a moment!",
                "I know this needs quick attention! Give me 30 seconds to wrap up what I'm doing...",
                "This is important - I'm finishing up with someone else but I'll be right with you!",
                "Urgent - understood! I'm with another tenant but I'll get to this within the next minute.",
            ],
            "landlord": [
                "I see this needs attention! I'm with another property owner right now, but I'll be with you shortly.",
                "Got it - I'm handling multiple requests but I'll prioritize this.",
                "I'm processing several items right now, but I'll get to this within the next minute.",
                "Noted - I'm juggling a few things but I'll have this for you momentarily.",
            ],
            "contractor": [
                "I see this is time-sensitive! I'm with another contractor right now but I'll be right with you.",
                "Got it - I'm handling a few bids but I'll jump on this ASAP.",
                "I'm processing other jobs right now, but I'll get to this within the next minute.",
            ]
        }
        return random.choice(urgent_messages.get(persona, urgent_messages["tenant"]))

    # Normal rate limit messages - more casual
    messages = {
        "tenant": [
            "Whoa, busy day! 😅 I'm helping a bunch of tenants right now. Give me 30 seconds and I'll be right with you!",
            "I'm swamped at the moment! 🔥 Helping other folks but I'll get to you in just a bit.",
            "Lots going on right now! I'm finishing up with someone else, then you're up next.",
            "I'm bouncing between a few issues right now - I'll circle back to you in about a minute!",
            "It's a busy one! I'm wrapping up another request, then I'm all yours.",
            "Getting slammed with requests! 💪 Give me like 60 seconds to finish what I'm doing...",
            "So many maintenance issues today! Let me finish helping someone else real quick...",
            "Running at full speed here! I'll be back with you in about a minute.",
        ],
        "landlord": [
            "I'm handling multiple property owners right now - I'll be with you shortly!",
            "Busy morning! Let me wrap up another review and I'll get to this.",
            "I'm coordinating a few jobs at the moment - give me about a minute!",
            "Lots of activity today! I'll circle back to you in just a moment.",
            "I'm reviewing other incidents right now, but you're next up!",
            "Managing several properties at once - I'll get to this ASAP!",
        ],
        "contractor": [
            "Lots of job activity right now! Let me finish with another contractor and I'll be right with you.",
            "I'm coordinating multiple bids at the moment - give me about a minute!",
            "Busy day for jobs! I'll wrap up what I'm doing and get back to you.",
            "Handling a few contractors right now - you're next in line!",
            "I'm reviewing bids for another job - I'll get to yours in just a sec!",
        ]
    }

    return random.choice(messages.get(persona, messages["tenant"]))


def get_queue_busy_message(persona: PersonaType = "tenant") -> str:
    """When task queue is full"""

    messages = {
        "tenant": [
            "Wow, everyone's reporting issues today! 📱 I'm at capacity but I've got you in the queue. I'll get to this within a few minutes!",
            "It's super busy right now! I've queued your request and I'll process it as soon as I can (probably 2-3 minutes).",
            "I'm maxed out at the moment! Don't worry though - you're in line and I'll handle this very soon.",
            "Crazy busy! 🏃 I've added you to my list and I'll get to your issue ASAP.",
        ],
        "landlord": [
            "I'm at full capacity processing requests - I've queued yours and will get to it within a few minutes.",
            "System is quite busy! Your request is in the queue and will be processed shortly.",
            "I'm handling the maximum number of concurrent requests - yours is queued and coming up soon!",
        ],
        "contractor": [
            "I'm processing the max number of jobs right now - you're queued up and I'll get to this soon!",
            "At full capacity! Your request is in line and I'll handle it within a few minutes.",
            "System is busy - but I've got you queued and you'll hear back very soon!",
        ]
    }

    return random.choice(messages.get(persona, messages["tenant"]))


def get_error_recovery_message(persona: PersonaType = "tenant") -> str:
    """When something went wrong but we're retrying"""

    messages = {
        "tenant": [
            "Oops, hit a small snag! 🔧 Let me try that again...",
            "Hmm, that didn't work. Give me one more sec...",
            "Quick hiccup there - retrying now!",
            "Well that was weird... trying again!",
        ],
        "landlord": [
            "Encountered a technical issue - retrying now...",
            "Small error there - attempting again...",
            "That didn't work as expected - retrying...",
        ],
        "contractor": [
            "Hit a small issue - trying that again!",
            "Quick technical hiccup - retrying now...",
            "Oops - let me try that one more time...",
        ]
    }

    return random.choice(messages.get(persona, messages["tenant"]))


def get_welcome_back_message(persona: PersonaType = "tenant") -> str:
    """When user returns after rate limit"""

    messages = {
        "tenant": [
            "Okay I'm back! Thanks for waiting. What's going on?",
            "Alright, all yours now! What can I help with?",
            "Thanks for your patience! What's the issue?",
            "I'm back! What do you need help with?",
        ],
        "landlord": [
            "Thank you for waiting. How can I assist?",
            "I'm available now - what do you need?",
            "Thanks for your patience. What can I help with?",
        ],
        "contractor": [
            "I'm available now! What's up?",
            "Thanks for waiting - what can I help you with?",
            "Alright, I'm free now! What do you need?",
        ]
    }

    return random.choice(messages.get(persona, messages["tenant"]))
