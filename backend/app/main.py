from fastapi import FastAPI
from mangum import Mangum
from app.routes import chat, incident, job, agent

app = FastAPI()

app.include_router(chat.router)
app.include_router(incident.router)
app.include_router(job.router)
app.include_router(agent.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "LandTenMVP3 backend is running."}

@app.get("/health")
def health():
    return {"status": "healthy"}

handler = Mangum(app)
