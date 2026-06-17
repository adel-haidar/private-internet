#!/usr/bin/env python3
"""Private Internet admin CLI.

Mainly for invite-only deployments (REGISTRATION_OPEN=false), where accounts are
created out-of-band:

    python manage.py create-user --email=user@example.com --name="Display Name"
    python manage.py create-user --email=a@b.com --name=Admin --admin --password=...

If --password is omitted a strong one is generated and printed once.
"""

import argparse
import asyncio
import secrets
import sys

from private_internet.users.passwords import MIN_PASSWORD_LENGTH, hash_password
from private_internet.users.service import (
    create_user,
    get_user_by_email,
    init_users_db,
)


def _gen_password() -> str:
    # token_urlsafe(12) → ~16 chars, comfortably above the minimum
    return secrets.token_urlsafe(12)


def cmd_create_user(args: argparse.Namespace) -> int:
    email = args.email.strip().lower()
    init_users_db()

    if get_user_by_email(email) is not None:
        print(f"error: an account with email {email!r} already exists", file=sys.stderr)
        return 1

    password = args.password or _gen_password()
    if len(password) < MIN_PASSWORD_LENGTH:
        print(
            f"error: password must be at least {MIN_PASSWORD_LENGTH} characters",
            file=sys.stderr,
        )
        return 1

    user = create_user(
        email=email,
        display_name=args.name.strip(),
        password_hash=hash_password(password),
        is_admin=args.admin,
    )
    print(f"created user {user['id']} ({email}){' [admin]' if args.admin else ''}")
    if not args.password:
        print(f"generated password: {password}")
        print("(shown once — store it now)")
    return 0


def cmd_backfill_covers(args: argparse.Namespace) -> int:
    """Generate covers/thumbnails for a user's existing content (demo prep).

    Scope: fills missing PULSE/ARIA covers and refreshes SIGNAL/STORIES
    thumbnails. Idempotent — safe to re-run.
    """
    from private_internet.content.jobs.cover_backfill import backfill_covers

    email = args.email.strip().lower()
    user = get_user_by_email(email)
    if user is None:
        print(f"error: no account with email {email!r}", file=sys.stderr)
        return 1

    print(f"backfilling covers for {email} (user {user['id']}) …")
    summary = asyncio.run(backfill_covers(user["id"]))
    for module, counts in summary.items():
        print(
            f"  {module:8s} candidates={counts['candidates']:<4d} "
            f"done={counts['done']:<4d} failed={counts['failed']}"
        )
    total_failed = sum(c["failed"] for c in summary.values())
    return 1 if total_failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="manage.py", description="Private Internet admin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-user", help="create a platform user account")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True, help="display name")
    p.add_argument("--password", default=None, help="omit to auto-generate")
    p.add_argument("--admin", action="store_true", help="grant admin rights")
    p.set_defaults(func=cmd_create_user)

    p = sub.add_parser(
        "backfill-covers",
        help="generate covers/thumbnails for a user's existing content",
    )
    p.add_argument("--email", required=True, help="account to backfill")
    p.set_defaults(func=cmd_backfill_covers)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
