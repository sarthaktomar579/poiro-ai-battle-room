"""Canonical realtime event names.

Every state change that the frontend cares about flows through one of
these constants. Keeping them centralized makes it impossible for the
client and server to drift on event names.
"""
from __future__ import annotations

ROOM_PARTICIPANT_JOINED = "room.participant_joined"
ROOM_PARTICIPANT_LEFT = "room.participant_left"
ROOM_STATE_CHANGED = "room.state_changed"

ROUND_STARTED = "round.started"
ROUND_SUBMISSION_CREATED = "round.submission_created"
ROUND_STATE_CHANGED = "round.state_changed"
ROUND_COMPLETED = "round.completed"

JOB_QUEUED = "job.queued"
JOB_RUNNING = "job.running"
JOB_COMPLETED = "job.completed"
JOB_FAILED = "job.failed"
JOB_TIMED_OUT = "job.timed_out"

SCORE_RECORDED = "score.recorded"
WINNER_PICKED = "round.winner_picked"
