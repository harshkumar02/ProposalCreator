import os
import sys
import tempfile
import types
import uuid

import pytest

# Configure before the app (and its settings singleton) is imported.
_db_dir = tempfile.mkdtemp(prefix="proposalcreator-test-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_db_dir, "test.db").replace("\\", "/")
os.environ["N8N_SHARED_SECRET"] = "test-secret"
os.environ["N8N_WEBHOOK_BASE_URL"] = "http://n8n.test/webhook"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

# PyMuPDF is only needed for PDF uploads; don't require it to run the suite.
try:
    import fitz  # noqa: F401
except ImportError:
    sys.modules["fitz"] = types.ModuleType("fitz")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SECRET_HEADER = {"X-Workflow-Secret": "test-secret"}


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def make_user(client):
    def _make():
        email = f"user-{uuid.uuid4().hex[:12]}@example.com"
        res = client.post("/api/auth/register", json={"email": email, "password": "pw-123456"})
        assert res.status_code == 200, res.text
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    return _make


@pytest.fixture
def make_rfp(client):
    def _make(headers, content="RFP from ABC Manufacturing for OT security assessment."):
        res = client.post("/api/rfps/upload", data={"content": content}, headers=headers)
        assert res.status_code == 200, res.text
        return res.json()["id"]

    return _make
