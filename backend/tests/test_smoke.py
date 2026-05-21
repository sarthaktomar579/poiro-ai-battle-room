"""Smoke tests covering critical backend logic without booting Uvicorn.

Run with:

    pip install pytest pytest-asyncio
    pytest backend/tests -q
"""
from __future__ import annotations

import asyncio
import os

import pytest
from fastapi import HTTPException

# Use a throw-away SQLite database for the tests.
os.environ["DATABASE_URL"] = "sqlite:///./data/test_poiro.db"
os.environ["AI_PROVIDER"] = "mock"

from app.auth import create_access_token, decode_token, hash_password, verify_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app import models, services  # noqa: E402
from app.deps import require_host  # noqa: E402
from app.providers.mock import MockProvider  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    # Recreate schema for each test for isolation.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_password_hashing_roundtrip():
    h = hash_password("battleroom")
    assert verify_password("battleroom", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    tok = create_access_token("user-123")
    assert decode_token(tok) == "user-123"
    assert decode_token("garbage") is None


def test_room_code_is_unique_and_safe():
    with SessionLocal() as db:
        codes = {services.generate_room_code(db) for _ in range(20)}
    assert len(codes) == 20
    for c in codes:
        # No visually ambiguous chars.
        assert not (set(c) & set("O0I1"))


def test_leaderboard_orders_by_wins_then_score():
    with SessionLocal() as db:
        host = models.User(email="h@x", display_name="Host", password_hash="x")
        ada = models.User(email="a@x", display_name="Ada", password_hash="x")
        kai = models.User(email="k@x", display_name="Kai", password_hash="x")
        db.add_all([host, ada, kai])
        db.flush()

        room = models.Room(code="ABCD12", name="r", prompt="p", host_id=host.id)
        db.add(room)
        db.flush()

        for u, role in [
            (host, models.ParticipantRole.host),
            (ada, models.ParticipantRole.participant),
            (kai, models.ParticipantRole.participant),
        ]:
            db.add(models.Participant(room_id=room.id, user_id=u.id, role=role))

        r1 = models.Round(room_id=room.id, round_number=1, prompt="p", status=models.RoundStatus.completed)
        db.add(r1)
        db.flush()

        s_ada = models.Submission(round_id=r1.id, user_id=ada.id, prompt="a")
        s_kai = models.Submission(round_id=r1.id, user_id=kai.id, prompt="b")
        db.add_all([s_ada, s_kai])
        db.flush()

        db.add(models.Score(submission_id=s_ada.id, value=6.0, scored_by_user_id=host.id))
        db.add(models.Score(submission_id=s_kai.id, value=9.0, scored_by_user_id=host.id))
        r1.winner_submission_id = s_ada.id
        db.commit()

        lb = services.leaderboard_for_room(db, room.id)

    # Ada wins by `wins desc`, even though Kai has a higher raw score.
    assert lb[0].display_name == "Ada"
    assert lb[0].wins == 1
    assert lb[1].display_name == "Kai"


def test_room_owner_can_require_host_without_participant_row():
    with SessionLocal() as db:
        host = models.User(email="owner@x", display_name="Owner", password_hash="x")
        other = models.User(email="other@x", display_name="Other", password_hash="x")
        db.add_all([host, other])
        db.flush()
        room = models.Room(code="OWN123", name="r", prompt="p", host_id=host.id)
        db.add(room)
        db.commit()

        # Owner has no participant row yet (re-join edge case).
        p = require_host(room.id, host, db)
        assert p.role == models.ParticipantRole.host
        db.commit()

        db.add(
            models.Participant(
                room_id=room.id, user_id=other.id, role=models.ParticipantRole.participant
            )
        )
        db.commit()
        with pytest.raises(HTTPException) as exc:
            require_host(room.id, other, db)
        assert exc.value.status_code == 403


def test_mock_provider_returns_output():
    async def go():
        p = MockProvider(min_latency=0.0, max_latency=0.01, failure_rate=0.0, timeout_rate=0.0)
        r = await p.generate("luxury cyberpunk perfume")
        return r

    r = asyncio.run(go())
    assert "Concept:" in r.output
    assert r.provider == "mock"
