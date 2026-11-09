# n8n workflows

n8n only orchestrates. The business logic stays in FastAPI. The flow for every workflow:

```
Frontend ──POST /api/workflows/runs──▶ Backend ──webhook──▶ n8n
                                          ▲                  │
                                          │  /internal/...   │  (calls backend steps,
                                          └──────────────────┘   reports status)
Frontend ──GET /api/workflows/runs/{id}──▶ Backend   (polls status; never talks to n8n)
```

Every request in either direction carries the header `X-Workflow-Secret: <N8N_SHARED_SECRET>`.

## Production: automatic

In the `deploy/` stack, `deploy/n8n-init.sh` imports the credential and every workflow here on each start and publishes them, so the manual steps below aren't needed. Every workflow JSON must have a fixed top-level `id`. Edit workflows in this folder, not in the editor: editor-only changes are overwritten on restart.

## Local development: one-time setup

1. Put a long random `N8N_SHARED_SECRET` in `.env`, then run `docker-compose up`.
2. Open http://localhost:5678 and create the n8n owner account.
3. **Credentials → Add credential → Header Auth**:
   - Name: `ProposalCreator Workflow Secret`
   - Header name: `X-Workflow-Secret`
   - Value: the same `N8N_SHARED_SECRET`
4. Import the workflows (`./n8n/workflows` is mounted read-only at `/workflows`):
   ```bash
   docker-compose exec n8n n8n import:workflow --separate --input=/workflows
   ```
   You can also use **Workflows → Import from file** in the UI.
5. Open each imported workflow. On every node with a credential warning, select **ProposalCreator Workflow Secret**. Then toggle the workflow **Active**. Only active workflows answer on `/webhook/<name>`.

## Workflows

| Name (webhook path) | Steps | Status |
|---|---|---|
| `rfp-analysis` | Report RUNNING → `POST /internal/rfps/{id}/extract` → Report COMPLETED, or FAILED on error | Phase 1 (wraps the existing extractor) |

To add a workflow:
1. Register its name in `WORKFLOWS` in `backend/app/api/workflows.py`.
2. Add any `/internal/...` step endpoints it needs.
3. Export the workflow JSON into `n8n/workflows/`.

## Running the backend outside docker

If n8n runs in docker and the backend runs on the host (`uvicorn --reload`), set the following in `backend/.env`:

```
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
BACKEND_INTERNAL_URL=http://host.docker.internal:8000
```

If n8n also runs on the host (`npx n8n` or a local `npm install n8n`), use `BACKEND_INTERNAL_URL=http://127.0.0.1:8000`. **Don't use `localhost` there.** Node resolves `localhost` to IPv6 `::1`, while uvicorn listens on IPv4 only, so n8n's callbacks fail with `ECONNREFUSED ::1:8000`.

## Security

- `/internal/*` routes accept only the shared secret, never a user JWT. Don't expose them through a public reverse proxy.
- If `N8N_SHARED_SECRET` is empty, the backend disables both starting workflows and the internal API. It fails closed.
