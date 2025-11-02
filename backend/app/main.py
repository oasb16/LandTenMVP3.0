from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from app.routes import (
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
from app.utils.rate_limit import SimpleRateLimiter
from app.utils.startup_checks import validate_env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = FastAPI()

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
        webhook_url = os.getenv("STREAM_WEBHOOK_URL")

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
            # Get current app settings
            app_settings = client.get_app_settings()
            current_webhook = app_settings.get("app", {}).get("webhook_url")

            if current_webhook == webhook_url:
                logging.info(f"[Stream Webhook] ✅ Webhook already registered: {webhook_url}")
            else:
                # Update app settings with webhook
                client.update_app_settings(
                    webhook_url=webhook_url,
                    # Enable events we want to receive
                    # Note: Stream may require this to be set via Dashboard for some plans
                )
                logging.info(f"[Stream Webhook] ✅ Webhook registered successfully: {webhook_url}")
                logging.info("[Stream Webhook] Events enabled: message.new, reaction.new, custom.*")
        except Exception as e:
            logging.warning(f"[Stream Webhook] ⚠️  Could not auto-register webhook: {e}")
            logging.warning("[Stream Webhook] Please register webhook manually in Stream Dashboard:")
            logging.warning(f"[Stream Webhook]   URL: {webhook_url}")
            logging.warning("[Stream Webhook]   Events: message.new, reaction.new, typing.start")

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
