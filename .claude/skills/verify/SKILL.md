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
- Happy path: upload with `POST /api/rfps/upload` (a PDF gives `--- Page N ---` markers; form field `content` gives plain text with no pages), then `POST /api/workflows/runs {"workflow":"rfp-analysis","rfp_id":N,"params":{"provider":"gemini"}}`, then poll `GET /api/workflows/runs/{id}`, then `GET /api/rfps/{id}/clauses`. **`rfp-analysis` now does clause extraction and always makes a paid AI call** (Gemini Flash takes about 40–100 s per tender).
- Known-answer tender: `backend/tests/fixtures/sample_tender.txt`. Build a PDF from it with pymupdf (one page per marker) to exercise page numbers. The corrigendum should set PQ 3.1(a) to ₹20 Cr, 3.1(c) to 2 projects, and the deadline to 22 Dec.
- Free failure path through n8n: `"provider":"claude"` while `ANTHROPIC_API_KEY` is invalid, which results in FAILED with a 401 message.
- UI: `http://localhost:3000/rfps/{id}` (`npm run dev` in `frontend/`), Tender Analysis section. Don't click Re-analyse when clauses are already reviewed: it opens a `confirm()` dialog, which blocks browser automation.
- FAILED branch: upload an empty `.txt` file. Extraction returns 400 and n8n's error output reports FAILED.
- n8n down: stop the n8n node processes (`Get-CimInstance Win32_Process -Filter "Name='node.exe'"` filtered on `*n8n*`). Starting a run should return 502 and the run should be FAILED.

## Gotchas
- Use `127.0.0.1`, not `localhost`, for `BACKEND_INTERNAL_URL`. Node resolves localhost to `::1` and uvicorn is IPv4-only.
- Workflow changes imported via the CLI (`n8n import:workflow`, `n8n publish:workflow --id=pcRfpAnalysis001`) only take effect after n8n restarts. Stopping the background task leaves the node child running, so kill the processes too.
- Run Python with `-u` when polling; buffered output looks like a hang.
