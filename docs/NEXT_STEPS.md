# Next Steps: Breadth-First Execution Plan

## EC2 Backend Container
- [ ] SSH into EC2 and verify Docker group permissions for ec2-user.
- [ ] Run `docker ps -a` to check backend container status.
- [ ] If not running, pull and run backend image from ECR.
- [ ] Check container logs for errors and resolve as needed.
- [ ] Ensure port 8080 is listening (`netstat -tuln | grep 8080`).
- [ ] Update security group to allow inbound TCP on 8080 from your IP.
- [ ] Test backend health endpoint with curl.

## Frontend Integration
- [ ] Confirm `NEXT_PUBLIC_BACKEND_URL` in `.env.local` points to EC2 public IP.
- [ ] Restart frontend and test chat UI.
- [ ] Validate chat message flow end-to-end.
  - Channel/Event standardized to `chat`/`message`.
  - Ensure Pusher keys/cluster set in `.env.local`.

## Backend Validation
- [ ] Test `/health` and `/chat/send` endpoints from local and frontend.
- [ ] Log and fix any errors recursively.
  - Dev auth bypass via `AUTH_DISABLED=true` for local/dev.
  - CORS enabled to allow Next.js origin.

## Documentation & Repo
- [ ] Review and update all documentation files in `/docs` and `/non-dev`.
- [ ] Commit and push all changes to the repo.
- [ ] If git push fails, resolve and retry until successful.

## Continuous Breadth-First Fixes
- [ ] For every error, log and move to next actionable fix.
- [ ] Never halt; always continue breadth-first until MVP is fully functional.
