from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from .routes import (
    chat,
    incident,
    job,
    agent,
    thread,
    agent_summary,
    media,
    profile,
    task,
    chat_stream,
    property,
    ai_webhooks,
)
from starlette.middleware.base import BaseHTTPMiddleware
import time, uuid, logging
from .utils.rate_limit import SimpleRateLimiter
from .utils.startup_checks import validate_env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = FastAPI()

def get_base_url():
    import os
    # If running on Heroku, prefer HEROKU_BACKEND_URL
    if os.getenv("DYNO"):
        return os.getenv("HEROKU_BACKEND_URL") or os.getenv("BACKEND_URL")
    # Local fallback
    return os.getenv("BACKEND_URL") or os.getenv("BACKEND_INTERNAL_URL") or "http://localhost:8080"

# Startup event to register Stream webhook
@app.on_event("startup")
async def register_stream_webhook():
    """
    Register webhook with Stream Chat on startup.
    This ensures Stream sends message.new and other events to our backend.
    """
    import os
    try:
        from stream_chat import StreamChat

        api_key = os.getenv("STREAM_CHAT_API_KEY")
        api_secret = os.getenv("STREAM_CHAT_API_SECRET")
        webhook_url = os.getenv("STREAM_WEBHOOK_URL") or (get_base_url().rstrip("/") + "/ai/stream-webhook")

        if not api_key or not api_secret:
            logging.warning("[Stream Webhook] Stream Chat credentials not configured - skipping webhook registration")
            return

        if not webhook_url:
            logging.warning("[Stream Webhook] STREAM_WEBHOOK_URL not configured - skipping webhook registration")
            logging.warning("[Stream Webhook] Set STREAM_WEBHOOK_URL in .env (e.g., https://yourdomain.com/ai/stream-webhook)")
            return

        client = StreamChat(api_key, api_secret)

        # Register webhook with Stream
        logging.info(f"[Stream Webhook] Registering webhook: {webhook_url}")

        try:
            # Get current app settings (Stream Chat v2 API)
            logging.info("[stream-webhook] Fetching current app settings...")
            app_settings = client.get_app_settings()
            existing_hooks = app_settings.get("app", {}).get("event_hooks", [])

            logging.info(f"[stream-webhook] Found {len(existing_hooks)} existing webhook(s)")

            # Check if our webhook URL already exists
            hook_exists = False
            hook_index = -1
            for i, hook in enumerate(existing_hooks):
                if hook.get("url") == webhook_url:
                    hook_exists = True
                    hook_index = i
                    logging.info(f"[stream-webhook] Found existing hook at index {i}: {hook.get('name', 'unnamed')}")
                    break

            # Prepare the webhook configuration (Stream Chat v2 format)
            new_hook = {
                "name": "LandTen AI Webhook",
                "url": webhook_url,
                "events": ["message.new", "reaction.new", "typing.start"],
                "description": "Auto-registered webhook for PropertyAI conversational backend",
                "enabled": True,
            }

            if hook_exists:
                # Update existing hook
                logging.info(f"[stream-webhook] Updating existing webhook at index {hook_index}")
                existing_hooks[hook_index] = new_hook
            else:
                # Add new hook
                logging.info(f"[stream-webhook] Adding new webhook")
                existing_hooks.append(new_hook)

            # Update app settings with new/updated hooks (v2 API)
            logging.info(f"[stream-webhook] Calling update_app_settings with {len(existing_hooks)} hook(s)...")
            client.update_app_settings({
                "event_hooks": existing_hooks
            })

            logging.info(f"[stream-webhook] ✅ v2 webhook registered successfully")
            logging.info(f"[stream-webhook] URL: {webhook_url}")
            logging.info(f"[stream-webhook] Events: message.new, reaction.new, typing.start")
            logging.info(f"[stream-webhook] Verify at: https://getstream.io/dashboard → Chat → Event Hooks")

        except Exception as e:
            logging.warning(f"[stream-webhook] ⚠️  Could not auto-register webhook: {e}")
            logging.warning("[stream-webhook] This is usually due to API permissions or plan limits")
            logging.warning("[stream-webhook] Please register webhook manually in Stream Dashboard:")
            logging.warning(f"[stream-webhook]   1. Go to https://getstream.io/dashboard")
            logging.warning(f"[stream-webhook]   2. Navigate to Chat → Event Hooks")
            logging.warning(f"[stream-webhook]   3. Add webhook URL: {webhook_url}")
            logging.warning(f"[stream-webhook]   4. Enable events: message.new, reaction.new, typing.start")

    except ImportError:
        logging.warning("[Stream Webhook] stream-chat SDK not installed - skipping webhook registration")
    except Exception as e:
        logging.error(f"[Stream Webhook] ❌ Error during webhook registration: {e}")

# Minimal CORS for local dev and Next.js frontend
import os
cors_origins_env = os.getenv("BACKEND_CORS_ORIGINS", "*")
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = str(uuid.uuid4())
        start = time.time()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            dur = (time.time() - start) * 1000
            logging.info(
                {
                    "request_id": rid,
                    "method": request.method,
                    "path": request.url.path,
                    "status": getattr(response, "status_code", None),
                    "duration_ms": round(dur, 2),
                }
            )

app.add_middleware(LoggingMiddleware)

limiter = SimpleRateLimiter(max_requests=120, window_seconds=60)

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    key = f"ip:{client_ip}"
    if not limiter.allow(key):
        from fastapi import Response
        return Response(status_code=429, content="Too Many Requests")
    return await call_next(request)

app.include_router(chat.router)
app.include_router(incident.router)
app.include_router(job.router)
app.include_router(agent.router)
app.include_router(thread.router)
app.include_router(agent_summary.router)
app.include_router(media.router)
app.include_router(profile.router)
app.include_router(task.router)
app.include_router(chat_stream.router)
app.include_router(property.router)
app.include_router(ai_webhooks.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "LandTenMVP3 backend is running."}

@app.get("/health")
def health():
    return {"status": "healthy"}

handler = Mangum(app)

for w in validate_env():
    logging.warning(w)
