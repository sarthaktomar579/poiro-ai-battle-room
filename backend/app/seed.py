"""Seed the database with two demo users so reviewers can sign in fast.

Run with:

    python -m app.seed

Idempotent: re-running it does not duplicate users.
"""
from __future__ import annotations

from .auth import hash_password
from .database import Base, SessionLocal, engine
from . import models


DEMO_USERS = [
    {"email": "host@poiro.ai", "password": "battleroom", "display_name": "Demo Host"},
    {"email": "ada@poiro.ai", "password": "battleroom", "display_name": "Ada"},
    {"email": "kai@poiro.ai", "password": "battleroom", "display_name": "Kai"},
]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for u in DEMO_USERS:
            existing = db.query(models.User).filter(models.User.email == u["email"]).first()
            if existing:
                continue
            db.add(
                models.User(
                    email=u["email"],
                    display_name=u["display_name"],
                    password_hash=hash_password(u["password"]),
                )
            )
        db.commit()
    print("Seeded demo users:")
    for u in DEMO_USERS:
        print(f"  - {u['email']} / {u['password']}  ({u['display_name']})")


if __name__ == "__main__":
    run()
