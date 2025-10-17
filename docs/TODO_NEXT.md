# LandTenMVP Outstanding Tasks & Debugging Notes

## Outstanding Tasks
- [ ] Backend container: Ensure it runs and exposes port 8080 on EC2.
- [ ] Security group: Confirm inbound rules for ports 22 (SSH) and 8080 (API).
- [ ] ECR authentication: Validate docker login and image pull on EC2.
- [ ] Frontend: Test chat UI with EC2 backend URL.
- [ ] Backend: Validate health and chat endpoints with curl.
- [ ] Error logging: Continue breadth-first recursive fixes for any failures.
- [ ] Documentation: Expand non-dev docs for business, ops, and future planning.

## Debugging Notes
- If backend unreachable, check container status, logs, port, and security group.
- If Docker permission denied, add ec2-user to docker group and reconnect.
- If SSH fails, update security group for port 22 from your IP.
- Always log errors and continue to next actionable fix.
