from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.migrations import run_migrations
from app.api import auth, rfps, proposals, templates, extraction, generation, proposal_types, blocks, workflows, clauses

if settings.AUTO_MIGRATE:
    run_migrations()

app = FastAPI(
    title="ProposalCreator API",
    description="RFP to Proposal Platform for Cybersecurity Consultants",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(rfps.router, prefix="/api/rfps", tags=["rfps"])
app.include_router(extraction.router, prefix="/api/rfps", tags=["extraction"])
app.include_router(clauses.router, prefix="/api/rfps", tags=["clauses"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["proposals"])
app.include_router(generation.router, prefix="/api/proposals", tags=["generation"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(proposal_types.router, prefix="/api/proposal-types", tags=["proposal_types"])
app.include_router(blocks.router, prefix="/api/blocks", tags=["blocks"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
# Called by n8n only (shared-secret auth); keep off the public reverse proxy.
app.include_router(workflows.internal_router, prefix="/internal", tags=["internal"])


@app.get("/")
def root():
    return {"message": "ProposalCreator API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}