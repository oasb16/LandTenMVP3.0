import os


def validate_env():
    warnings = []
    if not os.getenv("PUSHER_KEY"):
        warnings.append("PUSHER_KEY missing; realtime may fail.")
    if os.getenv("AUTH_DISABLED", "false").lower() in {"true", "1", "yes"}:
        warnings.append("AUTH_DISABLED is true; dev mode bypass active.")
    return warnings

