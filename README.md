# ProposalCreator

AI-powered RFP → proposal platform for **63SATS**. Upload an RFP, let AI extract the structured fields, review and edit them, and generate a fully branded 63SATS Word proposal.

- **Backend** — FastAPI + SQLAlchemy (SQLite by default, Postgres in Docker)
- **Frontend** — Next.js 14 (App Router) + Tailwind
- **AI** — Claude (Anthropic) for extraction and proposal-type detection, OpenAI optional as a second engine

---

## Features

| | |
|---|---|
| **RFP ingestion** | PDF (PyMuPDF), Word (mammoth), plain text, or pasted content |
| **Multi-engine extraction** | Claude, OpenAI, and a local regex engine that always runs — results are tagged per engine with confidence scores |
| **Review workflow** | Edit extracted fields before they reach the document; only reviewed fields are used |
| **Proposal type detection** | Keyword scoring over ~10 service types (firewall, OT/ICS, SOC, SIEM, VA, MSSP, endpoint, cloud, network, compliance), with an optional Claude pass to break ties |
| **Branded Word output** | 30-page proposal matching the 63SATS master template — branded page frame, cover page, Index (TOC), 19 numbered sections, 15 tables |
| **Modular block engine** | Reusable content blocks stored in the DB, filtered by conditions and rendered with a Handlebars-like syntax |
| **JWT auth** | Access + refresh tokens; every resource is scoped to its owner |

---

## Quick start

### Option A — Docker (everything, incl. Postgres)

```bash
cp .env.example .env          # add your ANTHROPIC_API_KEY
docker-compose up
```

- Frontend → http://localhost:3000
- API → http://localhost:8000
- API docs → http://localhost:8000/docs

### Option B — Run locally

**Backend** (from `backend/`):

```bash
python -m venv venv
venv\Scripts\activate                 # Windows
source venv/bin/activate              # macOS / Linux
pip install -r requirements.txt

python -m app.services.seed_blocks    # seed proposal types + block libraries (idempotent)
uvicorn app.main:app --reload         # http://localhost:8000
```

**Frontend** (from `frontend/`):

```bash
npm install
npm run dev                           # http://localhost:3000
```

Register an account at `/register`, upload an RFP, run extraction, review the fields, then generate.

---

## Configuration

Copy `.env.example` → `.env`:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Claude extraction + type detection. Without it, extraction silently falls back to the regex engine |
| `OPENAI_API_KEY` | No | — | Enables the optional second extraction engine |
| `DATABASE_URL` | No | `sqlite:///./proposalcreator.db` | Postgres URL in Docker |
| `SECRET_KEY` | **Yes in production** | `supersecretkeychangeinproduction` | JWT signing key — **change this before deploying** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | |

`.env` is gitignored. Never commit real keys.

---

## How it works

```
Upload RFP  →  text extracted (PyMuPDF / mammoth)  →  stored on RFP.content
     ↓
POST /api/rfps/{id}/extract  →  Claude + OpenAI + regex engines
     ↓
~19 structured fields written to extraction_results, tagged by engine
     ↓
User reviews/edits fields in the UI  (is_reviewed = true)
     ↓
POST /api/proposals/{id}/generate  →  branded .docx
```

Only fields marked reviewed are merged into the proposal, so a document renders with defaults until someone has been through the editor.

### Two generation paths

1. **Monolithic generator** (`services/document_generator.py`) — the path in use. Section content lives as Python constants, assembled with `python-docx` in a fixed order; extracted data overrides the defaults field by field.
2. **Modular block engine** (`services/block_composer.py`) — newer. Content lives in the DB as `ProposalBlock` rows grouped into libraries and scoped to proposal types, filtered by condition expressions and rendered with `{{var}}`, `{{var|default}}`, `{{#if}}`, `{{#each}}`. Returns rendered blocks plus the list of missing variables for the UI to prompt on.

### Document design

Output mirrors the 63SATS master template:

- A4, **Myriad Pro** 10pt body, `#112E54` headings with a `#45A2DD` accent bar
- Branded page frame (`backend/app/assets/63sats_page_frame.png`) floated behind the text of every page
- Cover page, Index with a live Word TOC field, section-per-page layout, shaded repeating table headers

Every visual property is a constant at the top of `document_generator.py` — change it there and it changes everywhere. Myriad Pro must be installed locally for Word to render it as designed; otherwise Word substitutes a similar face.

> The 63SATS master template and client proposals are **not** in this repository — they contain client data. Only the extracted brand artwork ships, under `backend/app/assets/`.

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` · `/login` · `/refresh` · `/me` | Auth |
| `POST` | `/api/rfps/upload` | Upload a file or paste content |
| `GET` | `/api/rfps/` · `/{id}` · `/{id}/content` | List / read RFPs |
| `POST` | `/api/rfps/{id}/extract` | Run extraction engines |
| `GET` | `/api/rfps/{id}/extraction-results` | Fetch extracted fields |
| `PUT` | `/api/rfps/{id}/extraction-results/{result_id}` | Edit / mark reviewed |
| `POST` | `/api/proposals/` | Create a proposal |
| `POST` | `/api/proposals/{id}/generate` | Download the `.docx` |
| `POST` | `/api/proposals/{id}/generate-text` | Text preview |
| `GET` | `/api/proposal-types/` · `POST /detect` | Types + detection |
| `GET` | `/api/blocks/` · `POST /preview` | Block library |
| `GET` | `/api/templates/` | Templates |

Full interactive docs at `/docs` when the backend is running.

---

## Database

Schema is managed by Alembic (`backend/alembic/`). The backend applies pending migrations automatically on startup (set `AUTO_MIGRATE=false` to disable). After changing a model:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"   # review the generated file
alembic upgrade head                                        # or just restart the backend
```

Existing databases created before Alembic are detected and stamped at the baseline revision automatically.

## n8n workflows

`docker-compose up` also starts n8n on http://localhost:5678. It orchestrates multi-step jobs (RFP analysis now; qualification and bid/no-bid next) by calling back into the backend. Set `N8N_SHARED_SECRET` in `.env`, then follow the one-time setup in [`n8n/README.md`](n8n/README.md).

---

## Deployment

**Recommended: private, free, single server.** `deploy/` contains a production stack (Postgres, backend, n8n, frontend and Caddy) that runs with one `docker compose` command on a free Oracle Cloud VM, or on any Linux box with 4 GB of RAM. Access is private through Tailscale or Cloudflare Access, with no public ports. Self-registration is off; accounts are created with `python -m app.cli create-user`. **Step-by-step guide: [`deploy/README.md`](deploy/README.md).**

```bash
cd deploy && ./setup.sh          # generates deploy/.env with random secrets
# add GEMINI_API_KEY to deploy/.env
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend python -m app.cli create-user --email you@example.com
```

The root `docker-compose.yml` is the **development** stack (hot reload, ports open on localhost). Don't expose it.

> GitHub Pages and other static hosts can't run this app: it needs the FastAPI backend, Postgres and n8n. Split hosting (e.g. Vercel + Render) also works poorly on free tiers, because free Render services sleep and lose n8n's state. Use the single-server stack.

---

## Project layout

```
backend/
  app/
    api/          auth, rfps, extraction, proposals, generation, templates,
                  proposal_types, blocks — one router per resource
    core/         config, database, security (JWT + bcrypt)
    models/       SQLAlchemy models (single file)
    schemas/      Pydantic v2 schemas (single file)
    services/     extractors, document_generator, block_composer,
                  proposal_type_detector, seed_blocks
    assets/       63SATS page-frame artwork
frontend/
  src/
    app/          App Router pages
    components/   shared UI primitives
    lib/          api.ts (single fetch client), AuthContext.tsx
```

---

## Development notes

- Register new routers in `app/main.py` under an `/api/...` prefix
- Every backend call goes through `frontend/src/lib/api.ts` — adding an endpoint means adding a method there
- Pydantic v2: use `Model.model_validate(orm_obj)` for responses
- Extractors catch all exceptions and return empty results, so a failed AI call looks like "no fields found" — check the backend log for `Claude extraction error:`
- `pytest` is configured; `backend/tests/` is currently empty

---

## License

MIT
