"""Admin commands for private deployments (where ALLOW_REGISTRATION=false).

    python -m app.cli create-user --email a@63sats.com --name "Asha"   # prompts for password
    python -m app.cli set-password --email a@63sats.com
    python -m app.cli list-users

In docker: docker compose -f deploy/docker-compose.prod.yml exec backend python -m app.cli ...
Pass --password-stdin to read the password from stdin instead of prompting.
"""
import argparse
import getpass
import sys

from app.core.database import SessionLocal
from app.core.migrations import run_migrations
from app.core.security import get_password_hash
from app.models.models import User

MIN_PASSWORD_LENGTH = 8


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Password: ")
        if getpass.getpass("Repeat password: ") != password:
            sys.exit("Passwords do not match.")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    return password


def create_user(email: str, name: str, password: str) -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            sys.exit(f"User {email} already exists (use set-password to change the password).")
        db.add(User(email=email, name=name or None, password_hash=get_password_hash(password)))
        db.commit()
        print(f"Created user {email}")
    finally:
        db.close()


def set_password(email: str, password: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            sys.exit(f"No user {email}")
        user.password_hash = get_password_hash(password)
        db.commit()
        print(f"Password updated for {email}")
    finally:
        db.close()


def list_users() -> None:
    db = SessionLocal()
    try:
        for user in db.query(User).order_by(User.id).all():
            print(f"{user.id:4}  {user.email:40}  {user.name or ''}")
    finally:
        db.close()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="add a user")
    create.add_argument("--email", required=True)
    create.add_argument("--name", default="")
    create.add_argument("--password-stdin", action="store_true")
    reset = sub.add_parser("set-password", help="change a user's password")
    reset.add_argument("--email", required=True)
    reset.add_argument("--password-stdin", action="store_true")
    sub.add_parser("list-users", help="list users")
    args = parser.parse_args(argv)

    run_migrations()  # the CLI may run before the API has ever started
    if args.command == "create-user":
        create_user(args.email.strip(), args.name.strip(), _read_password(args.password_stdin))
    elif args.command == "set-password":
        set_password(args.email.strip(), _read_password(args.password_stdin))
    else:
        list_users()


if __name__ == "__main__":
    main()
