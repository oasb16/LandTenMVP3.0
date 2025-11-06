#!/usr/bin/env python3
import sys, os, json, traceback
from pathlib import Path

# Ensure repo root is on path
repo_root = Path(__file__).resolve().parents[2]
# Ensure the backend folder is on sys.path so imports like `from app.services...` resolve
backend_dir = repo_root / 'backend'
sys.path.insert(0, str(backend_dir))

try:
    from app.services.stream_bot import PropertyAIBot, handle_ai_json_response
except Exception as e:
    print("IMPORT_ERROR", e)
    traceback.print_exc()
    sys.exit(2)


def run(channel_id, persona, variant):
    try:
        bot = PropertyAIBot()
    except Exception as e:
        print("BOT_INIT_ERROR", e)
        return
    bot_id = bot.get_bot_id(persona)
    if variant == 'single':
        payload = {"message":"Please follow these steps","next_action":"Gather photos of the damage"}
    else:
        payload = {"message":"Next steps for repair","actions":["Take photo","Send to landlord","Schedule repair"]}
    text = json.dumps(payload)
    print("Sending payload:", text)
    try:
        resp = handle_ai_json_response(bot.client, channel_id, bot_id, text, metadata={'user_id':'test-user'})
        print("handle_ai_json_response returned:", resp)
    except Exception as e:
        print("HANDLER_ERROR", e)
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: run_stream_test.py <channel_id> <persona> <variant(single|list)>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3])
