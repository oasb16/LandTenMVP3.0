# LandTenMVP Development Log

## Chronological Key Changes & Rationales

### Initial Scaffold
- Created Next.js frontend and FastAPI backend.
- Set up .env files for secrets/config.
- Dockerized backend, wrote Dockerfile and requirements.txt.

### Cloud Deployment Automation
- Created AWS ECR repo, built/pushed Docker image.
- Launched EC2 instance, created key pair, set up security group.
- Automated all steps via AWS CLI, logging errors and continuing recursively.

### Error Handling & Iterative Fixes
- Zappa/AWS Lambda failed (C extension issue), pivoted to EC2 Docker.
- Fly.io, Elastic Beanstalk, App Runner: network/IAM/config errors, logged and moved to next solution.
- EC2: Key pair/AMI/security group errors, fixed by listing resources and relaunching as needed.
- Docker permission denied: added ec2-user to docker group, iterated until container access worked.
- Backend unreachable: iterated container/log/port/security group fixes until endpoint was reachable.

### Frontend Integration & Validation
- Updated .env.local with EC2 backend URL.
- Restarted frontend, tested chat UI.
- Validated backend endpoints with curl, iterated on errors.

### Recursion Principle
- For every error, log and move to next actionable fix.
- Never halt; always continue breadth-first until MVP is functional.
