from fastapi import FastAPI
from app.routes import chat, incident, job, agent

app = FastAPI()

app.include_router(chat.router)
app.include_router(incident.router)
app.include_router(job.router)
app.include_router(agent.router)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI backend!"}
