# AGENTS.md

This file provides guidance to Codex (claude.ai/code) when working with code in this repository.

## Project

AI-powered RFP → proposal platform for 63SATS (cybersecurity MSSP). An RFP document is uploaded, AI engines extract structured fields, the user reviews/edits them, and a Word proposal is generated. Backend: FastAPI + SQLAlchemy. Frontend: Next.js 14 App Router + Tailwind.

## Commands

Backend (from `backend/`):
```bash
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload                     # http://localhost:8000, docs at /docs
python -m app.services.seed_blocks                # seed proposal types + block libraries (idempotent)
alembic revision --autogenerate -m "describe"    # after changing models/models.py
pytest                                            # workflow + LLM provider tests
pytest tests/test_x.py::test_name                 # single test
```

Frontend (from `frontend/`):
```bash
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

Full stack: `docker-compose up` (adds Postgres on 5432 — backend switches to `DATABASE_URL` postgres — and n8n on 5678; one-time n8n setup is in `n8n/README.md`).

Environment: copy `.env.example` → `.env`. `ANTHROPIC_API_KEY` is required for extraction and AI-assisted type detection; both extractors silently return `[]` when their key is unset, so extraction degrades to the local regex engine rather than erroring.

## Database

- Schema is managed by Alembic (`backend/alembic/versions/`). `app/main.py` calls `run_migrations()` (`app/core/migrations.py`) at import time unless `AUTO_MIGRATE=false`, so `uvicorn` upgrades the DB to head on startup. **After changing a model, generate a migration** (`alembic revision --autogenerate`) and review it — nothing calls `create_all` any more.
- `0001` is the baseline (the schema as it was when Alembic was introduced). A DB that has tables but no `alembic_version` was made by the old `create_all`; `run_migrations` stamps it at `0001` before upgrading. `env.py` uses batch mode on SQLite, since SQLite can't ALTER most columns.
- Default `DATABASE_URL` is SQLite (`backend/proposalcreator.db`); `app/core/database.py` branches on the URL prefix to add `check_same_thread` for SQLite.

## Architecture

### Two parallel proposal-generation paths

This is the most important thing to understand. There are **two independent generators**, and new work is on the second:

1. **Legacy monolithic generator** — `services/document_generator.py` + `api/generation.py`. Section text (Document Control, About 63SATS, Why 63SATS, risk register, etc.) is hardcoded as Python string constants and assembled with `python-docx` in a fixed numbered-section order; `extracted_data` only fills gaps via `.get(field, hardcoded_default)`. Note the 63SATS boilerplate constants are **duplicated** between `document_generator.py` and `api/generation.py` — change both or you'll get drift.

   Document appearance mirrors `template.docx` in the repo root (the 63SATS master template) and is driven by the design tokens at the top of `document_generator.py` — A4, Myriad Pro 10pt, `#112E54` headings with a `#45A2DD` accent bar, applied by `_configure_styles` / `_configure_header_footer` / `_add_cover_page`. The branded page artwork is `app/assets/63sats_page_frame.png`, extracted from `template.docx` and floated behind the text of every page by `_add_page_frame` (inline picture rewritten as a `wp:anchor` with `behindDoc="1"`); margins in `_configure_page` are sized to clear the shield and the footer band, so changing one without the other causes overlap. Never call `doc.add_paragraph` / `doc.add_heading` / `doc.add_table` directly in section code — use `_add_body_text`, `_add_heading`, `_add_paragraph`, `_add_table`, which pin the font on every run (`w:ascii`/`w:hAnsi`/`w:eastAsia`/`w:cs`) so extracted content can't drift to the Word theme font. `_add_body_text` also turns markdown pipe tables into real Word tables and bullet/numbered lines into hanging-indent list items.

2. **Modular block engine** (newer, untracked/in-progress files) — content lives in the DB as `ProposalBlock` rows grouped into `BlockLibrary`s and optionally scoped to a `ProposalType`. `services/block_composer.py` loads blocks (static blocks have `proposal_type_id IS NULL` and apply to every proposal; type-specific blocks match the proposal's type), filters them by `condition_expression`, orders them by template `block_order` or `(section_order, subsection_order)`, and renders a Handlebars-ish syntax: `{{var}}`, `{{var|default}}`, `{{#if var}}…{{/if}}`, `{{#each list}}…{{/each}}`. It returns `(rendered_blocks, missing_variables)` — the missing-variable list is what the UI surfaces for the user to fill in.

`services/seed_blocks.py` is the source of truth for the block content shipped with the product (per-type seeders: static, firewall, OT, SOC, risk). Editing proposal boilerplate for the modular path means editing the seed script, not the docx generator.

### Extraction pipeline

`POST /api/rfps/upload` → text extracted from the file (PyMuPDF for PDF, mammoth for DOCX, raw decode otherwise) and stored on `RFP.content`. `POST /api/rfps/{id}/extract` **deletes all prior `ExtractionResult` rows for that RFP**, then runs the requested engines. Each engine returns a flat list of `{field_name, value, confidence}` rows, all written to the same `extraction_results` table tagged by `engine` (`Codex`, `openai`, `local_regex` — the regex engine always runs). The ~19 field names (`client_name`, `project_title`, `current_challenges`, `objectives`, …) are defined by the prompt in `services/claude_extractor.py` and are the contract consumed downstream by the document generators and block variables.

Generation only picks up extraction rows where `is_reviewed == True`, merged over the JSON in `Proposal.extracted_data` — so a proposal renders defaults until the user has reviewed fields in the editor.

### RFP-specific content generation

The ~19 extracted fields are short snippets, so on their own they leave the generator rendering mostly boilerplate. `services/proposal_writer.py` closes that gap: it sends the **full `RFP.content`** to Codex once and gets back ~20 long-form sections written for that specific RFP (executive summary, understanding of requirements + a requirement/compliance matrix, the technical solution design, bill of materials, RACI, a real risk register, and so on). Its output keys deliberately match the names `document_generator` looks up in `extracted_data`, so a generated section transparently displaces the corresponding hardcoded constant.

`api/generation.py::_build_generation_data` layers the three sources, lowest precedence first: AI sections → whatever is stored on `Proposal.extracted_data` → reviewed extraction rows (human edits always win). Anything still absent falls through to the hardcoded defaults, so the whole path degrades rather than failing when `ANTHROPIC_API_KEY` is unset. The model call is expensive, so its result is cached back into `Proposal.extracted_data` under `_ai_sections` alongside an `_ai_fingerprint` of (RFP text + input fields + client name); it only regenerates when that fingerprint changes. Keys prefixed with `_` are internal and are stripped before rendering.

`services/proposal_type_detector.py` classifies the RFP into one of ~10 types by keyword scoring over the extracted text, with an optional Codex call to break ties/boost confidence.

### n8n orchestration

n8n (`docker-compose` service, workflows exported to `n8n/workflows/`) sequences multi-step jobs but holds no business logic. `api/workflows.py` is the only bridge:
- `POST /api/workflows/runs` creates a `WorkflowRun` and POSTs it to `{N8N_WEBHOOK_BASE_URL}/{workflow}`. Workflow names must be registered in `WORKFLOWS`.
- n8n calls back into `/internal/...` routes: `workflows/runs/{id}/status` (RUNNING → COMPLETED|FAILED; terminal runs reject further updates with 409) plus step endpoints such as `rfps/{id}/extract`, which wraps `extraction.run_extraction`.
- `/internal` authenticates with the `X-Workflow-Secret` header (`N8N_SHARED_SECRET`) instead of a JWT, and every step re-scopes data to `run.user_id`. When the secret is unset, workflows and `/internal` are disabled (they fail closed).
- The frontend polls `GET /api/workflows/runs/{id}` and never calls n8n directly.

New AI steps for workflows should call `services/llm.py::complete_json(system, prompt, schema, provider=None)`, which switches between Codex (`CLAUDE_MODEL`) and Gemini (`GEMINI_MODEL`) via `LLM_PROVIDER`. Unlike the legacy extractors it **raises `LLMError`** rather than returning empty, so a failed step marks the run FAILED instead of passing as "no fields found."

### Auth

JWT access + refresh tokens signed with `SECRET_KEY` (`core/security.py`, bcrypt with the 72-byte truncation applied on both hash and verify). Every resource route filters by `current_user.id` — preserve that pattern; the ORM has no row-level scoping. The frontend stores both tokens in `localStorage` (`lib/api.ts`) and refreshes via `/api/auth/refresh`.

### Frontend

`src/lib/api.ts` is a single hand-written fetch client — every backend call goes through it, so adding an endpoint means adding a method there. `src/lib/AuthContext.tsx` provides the session; `src/components/ui.tsx` holds the shared primitives. Pages are thin App Router route files under `src/app/`. CORS on the backend is pinned to `localhost:3000` / `127.0.0.1:3000`.

## Conventions

- Models, schemas, and routes each live in one file per concern (`models/models.py`, `schemas/schemas.py`, `api/<resource>.py`); register new routers in `app/main.py` under an `/api/...` prefix.
- Pydantic v2 — use `Model.model_validate(orm_obj)` for responses.
- AI calls use `model="Codex-opus-4-7"`; extractors catch all exceptions and return empty results rather than propagating, so a failed extraction looks like "no fields found."
