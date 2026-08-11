# Deployment configuration

SeatSync ships as Docker images and a Compose topology. For a small portfolio deployment, run the same `backend` image as a web process and a Celery worker, attach managed PostgreSQL and Redis, and host the built `frontend` image behind HTTPS.

Required production changes:

- provide a strong `SECRET_KEY` and managed service URLs;
- run `alembic upgrade head` as a release command;
- set `FRONTEND_ORIGIN` to the HTTPS UI origin;
- use an SMTP provider instead of MailHog;
- mount `EXPORT_DIRECTORY` on durable storage or replace it with object storage;
- keep the API and worker on the same application revision.

No Kubernetes manifests are included because this modular monolith does not need a cluster to demonstrate its engineering guarantees.

