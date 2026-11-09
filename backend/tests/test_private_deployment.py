import io
import uuid

import pytest

from app import cli
from app.core.config import settings


def test_auth_config_reports_registration_state(client, monkeypatch):
    assert client.get("/api/auth/config").json() == {"registration_enabled": True}
    monkeypatch.setattr(settings, "ALLOW_REGISTRATION", False)
    assert client.get("/api/auth/config").json() == {"registration_enabled": False}


def test_registration_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_REGISTRATION", False)
    res = client.post("/api/auth/register", json={"email": f"x-{uuid.uuid4().hex[:8]}@example.com", "password": "pw-123456"})
    assert res.status_code == 403
    assert "administrator" in res.json()["detail"]


def test_cli_creates_user_who_can_log_in(client, monkeypatch, capsys):
    email = f"Admin-{uuid.uuid4().hex[:8]}@63sats.example"
    monkeypatch.setattr("sys.stdin", io.StringIO("correct-horse-1\n"))
    cli.main(["create-user", "--email", email, "--name", "Admin", "--password-stdin"])
    assert f"Created user {email}" in capsys.readouterr().out

    assert client.post("/api/auth/login", json={"email": email, "password": "correct-horse-1"}).status_code == 200

    monkeypatch.setattr("sys.stdin", io.StringIO("new-password-2\n"))
    cli.main(["set-password", "--email", email, "--password-stdin"])
    assert client.post("/api/auth/login", json={"email": email, "password": "correct-horse-1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "new-password-2"}).status_code == 200

    cli.main(["list-users"])
    assert email in capsys.readouterr().out


def test_cli_rejects_short_password_and_duplicates(monkeypatch):
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    monkeypatch.setattr("sys.stdin", io.StringIO("short\n"))
    with pytest.raises(SystemExit, match="at least 8"):
        cli.main(["create-user", "--email", email, "--password-stdin"])

    monkeypatch.setattr("sys.stdin", io.StringIO("long-enough-1\n"))
    cli.main(["create-user", "--email", email, "--password-stdin"])
    monkeypatch.setattr("sys.stdin", io.StringIO("long-enough-1\n"))
    with pytest.raises(SystemExit, match="already exists"):
        cli.main(["create-user", "--email", email, "--password-stdin"])
