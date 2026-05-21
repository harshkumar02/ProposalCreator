from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db
from app.api import auth, rfps, proposals, templates, extraction, generation

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ProposalCreator API",
    description="RFP to Proposal Platform for Cybersecurity Consultants",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(rfps.router, prefix="/api/rfps", tags=["rfps"])
app.include_router(extraction.router, prefix="/api/rfps", tags=["extraction"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["proposals"])
app.include_router(generation.router, prefix="/api/proposals", tags=["generation"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])


@app.get("/")
def root():
    return {"message": "ProposalCreator API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}