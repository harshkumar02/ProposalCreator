---
name: verify
description: Launch and drive ProposalCreator (FastAPI backend + local n8n) to verify changes at the HTTP/n8n surface.
---

# Verifying ProposalCreator

## Launch
- Backend (from `backend/`): `./venv/Scripts/python -m uvicorn app.main:app --port 8000`. Migrations run at startup; look for the Alembic lines in the log.
- n8n (installed in `C:\Users\harsh\n8n-local`, not via npx because npx's cache cleanup hits EPERM):
  `cd /c/Users/harsh/n8n-local && N8N_SECURE_COOKIE=false N8N_DIAGNOSTICS_ENABLED=false ./node_modules/.bin/n8n start`
- Ready checks:
  - backend: `curl http://127.0.0.1:8000/health`
  - n8n webhook registered: `POST http://127.0.0.1:5678/webhook/rfp-analysis` with a wrong `X-Workflow-Secret` returns **403**. `/healthz` returns 200 before the workflows are active.

## Drive
- Test user: `e2e-n8n-test@example.com` / `e2e-test-pass-123` (log in via `/api/auth/login`).
- Happy path: upload text with `POST /api/rfps/upload` (form field `content`), then `POST /api/workflows/runs {"workflow":"rfp-analysis","rfp_id":N,"params":{"engines":[]}}`, then poll `GET /api/workflows/runs/{id}`. `engines: []` means no paid AI calls.
- FAILED branch: upload an empty `.txt` file. Extraction returns 400 and n8n's error output reports FAILED.
- n8n down: stop the n8n node processes (`Get-CimInstance Win32_Process -Filter "Name='node.exe'"` filtered on `*n8n*`). Starting a run should return 502 and the run should be FAILED.

## Gotchas
- Use `127.0.0.1`, not `localhost`, for `BACKEND_INTERNAL_URL`. Node resolves localhost to `::1` and uvicorn is IPv4-only.
- Workflow changes imported via the CLI (`n8n import:workflow`, `n8n publish:workflow --id=pcRfpAnalysis001`) only take effect after n8n restarts. Stopping the background task leaves the node child running, so kill the processes too.
- Run Python with `-u` when polling; buffered output looks like a hang.
