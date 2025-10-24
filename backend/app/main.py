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

@app.get("/")
def root():
    return {"status": "ok", "message": "LandTenMVP3 backend is running."}

@app.get("/health")
def health():
    return {"status": "healthy"}

handler = Mangum(app)

for w in validate_env():
    logging.warning(w)
