# LandTenMVP Function/Class/Module Overview

## Frontend
- **App (Next.js):** Main React app, handles routing, UI, and state.
- **Firebase Auth:** Manages user authentication and session.
- **Pusher Integration:** Enables real-time chat and notifications.
- **Chat UI:** Sends/receives messages via backend and Pusher.

## Backend
- **FastAPI App:** Main API server, exposes health, chat, and business logic endpoints.
- **Routers:** Modular API endpoints for chat, health, etc.
- **Dockerfile:** Containerizes backend for cloud deployment.
- **requirements.txt:** Lists Python dependencies for backend.

## Cloud/Infra
- **AWS CLI Scripts:** Automate ECR repo creation, EC2 launch, security group management, Docker image push/pull.
- **.env Files:** Store secrets and config for frontend/backend.

## Key Implementation Rationale
- Decoupled frontend/backend for scalability.
- Real-time chat via Pusher for responsiveness.
- Automated infra for reproducibility and error recovery.
