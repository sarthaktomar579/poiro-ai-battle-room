# Poiro · AI Creative Battle Room

> Full-Stack Developer Intern assignment for **Evam Labs (Poiro)**.
> Submitted by **Sarthak Tomar** — May 21, 2026.

A small but complete, real-time multiplayer **AI creative battle room**.
A host sets a creative brief, contestants join with a 6-character code,
the host opens a round, contestants submit prompts, the backend spawns
async generation jobs against Gemini (with a clean mock fallback), every
state change streams to every client over WebSockets, and the host
scores submissions and crowns a winner.

The product was built around the assignment's **Final Guidance** — “a
polished, reliable implementation of one room and one round is better
than a broad demo with fragile state.” Everything in this repo is on the
critical path of that loop.

**New here?** Jump to [Quick start](#1-quick-start--run-the-app) to run the app, then [How to use the app](#2-how-to-use-the-app) for a step-by-step walkthrough.

**Repository:** https://github.com/sarthaktomar579/poiro-ai-battle-room

---

## Table of contents

**Run & use (start here)**

1. [Quick start — run the app](#1-quick-start--run-the-app)
2. [How to use the app](#2-how-to-use-the-app)
3. [Configuration & demo accounts](#3-configuration--demo-accounts)
4. [Troubleshooting](#4-troubleshooting)

**Technical reference (for reviewers)**

5. [Demo at a glance](#5-demo-at-a-glance)
6. [Architecture overview](#6-architecture-overview)
7. [Database schema](#7-database-schema)
8. [Realtime event model](#8-realtime-event-model)
9. [Generation job lifecycle](#9-generation-job-lifecycle)
10. [Battle / judging mechanism](#10-battle--judging-mechanism-the-intentional-gap)
11. [What is persisted vs. ephemeral](#11-what-is-persisted-vs-ephemeral)
12. [Failure handling strategy](#12-failure-handling-strategy)
13. [Roles & backend-enforced permissions](#13-roles--backend-enforced-permissions)
14. [Tradeoffs & explicit non-goals](#14-tradeoffs--explicit-non-goals)
15. [Known limitations](#15-known-limitations)
16. [What I would improve with more time](#16-what-i-would-improve-with-more-time)
17. [Repo layout](#17-repo-layout)

---

## 1. Quick start — run the app

You need **two terminals** running at the same time: **backend** (port 8000) and **frontend** (port 3000).

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11–3.13 recommended (3.14 may be slow to install deps) |
| Node.js | 18+ (20 recommended) |
| npm | Comes with Node |

### Step 1 — Backend (Terminal 1)

```powershell
cd backend

# Copy env file and add your Gemini key (optional — mock AI works without a key)
copy .env.example .env
# Edit .env → set GEMINI_API_KEY=your_key_here

# Easiest: one script installs deps, seeds users, starts the API
.\start-backend.ps1
```

**macOS / Linux:**

```bash
cd backend
cp .env.example .env
# edit .env with your GEMINI_API_KEY
chmod +x start-backend.ps1  # if needed
./start-backend.ps1
```

Wait until you see:

```text
Uvicorn running on http://127.0.0.1:8000
```

Check: open [http://localhost:8000/health](http://localhost:8000/health) — you should see `"status":"ok"`.

API docs (optional): [http://localhost:8000/docs](http://localhost:8000/docs)

### Step 2 — Frontend (Terminal 2)

```powershell
cd frontend
.\start-frontend.ps1
```

**macOS / Linux:**

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

### Manual start (if scripts fail)

**Backend:**

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000
```

**Frontend:**

```powershell
cd frontend
npm install
npm run dev
```

---

## 2. How to use the app

### Sign in or sign up

1. Open [http://localhost:3000](http://localhost:3000).
2. Use **Sign in** with a demo account (see [§3](#3-configuration--demo-accounts)), or **Sign up** with your own email and password.
3. If you see a yellow **“Backend offline”** banner, start the backend first ([§1](#1-quick-start--run-the-app)).

### Play a full battle (recommended demo)

Use **two browser windows** (normal + incognito) to simulate host and contestants.

#### Window A — Host

1. Sign in as **`host@poiro.ai`** / password **`battleroom`**.
2. Click **Create battle room**.
3. Enter a room name and a creative brief (e.g. *“Create the most insane luxury cyberpunk perfume campaign for Gen-Z.”*).
4. Copy the **6-character room code** (top-right, e.g. `RVES93`).
5. Click **Start round** in the left **Host controls** panel.

#### Window B — Participant

1. Sign in as **`ada@poiro.ai`** / **`battleroom`** (or sign up as a new user).
2. Click **Join room** and paste the code from the host.
3. In **Round 1**, type a creative prompt and click **Submit to the battle**.
4. Watch your card move through **`queued` → `running` → `completed`** (no refresh needed).

#### Back to Host — Score & finish

1. When all jobs finish, the round moves to **scoring** (yellow notice in host panel).
2. On each completed card, drag the **score slider** (0–10) and click **Save score**.
3. Click **Pick as winner** on the best submission.
4. Optional: click **Start round** again for another round, or **End room** when done.

### What each role can do

| Action | Host (room creator) | Participant |
|--------|---------------------|-------------|
| Create room | Yes | — |
| Join with code | Yes (as host) | Yes |
| Start round | Yes | No |
| Submit prompt | No | Yes (one per round) |
| Score / pick winner | Yes | No |
| End room | Yes | No |

**Important:** Only the account that **created the room** can use host controls. If you created the room as `host@poiro.ai`, you must be signed in as that account to start rounds, score, or end the room.

### Understanding the battle room screen

| Area | Purpose |
|------|---------|
| **Host controls** (left) | Start round, end room (host only) |
| **Participant panel** (left) | Submit prompt when round is open |
| **Center** | Live round, submission cards, AI output |
| **Realtime activity** (right) | WebSocket event log |
| **Leaderboard** (left) | Wins + total scores after scoring |

### Job status on each submission card

| Status | Meaning |
|--------|---------|
| `queued` | Waiting for the AI worker |
| `running` | Gemini (or mock) is generating |
| `completed` | Output is ready to read and score |
| `failed` | Error (see red message; may auto-retry once) |
| `timed_out` | Took longer than the configured timeout |

### Ending a room

1. Host clicks **End room** and confirms.
2. You should see a green message: **“Room ended. Thanks for hosting!”**
3. The active round closes and the center shows **“Room ended”**.
4. Status pill shows **ENDED**.

---

## 3. Configuration & demo accounts

### Environment files

**Backend** — copy `backend/.env.example` → `backend/.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Random string for JWT signing |
| `GEMINI_API_KEY` | No | Google AI key; if empty, mock AI is used |
| `GEMINI_MODEL` | No | Default `gemini-2.5-flash` |
| `AI_PROVIDER` | No | `gemini` or `mock` |
| `DATABASE_URL` | No | Default SQLite at `./data/poiro.db` |

**Frontend** — copy `frontend/.env.local.example` → `frontend/.env.local`:

| Variable | Default |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` |

### Demo accounts (after `python -m app.seed`)

| Email | Password | Typical use |
|-------|----------|-------------|
| `host@poiro.ai` | `battleroom` | Create room, host rounds |
| `ada@poiro.ai` | `battleroom` | Join as contestant |
| `kai@poiro.ai` | `battleroom` | Second contestant |

---

## 4. Troubleshooting

### “Cannot reach the backend” (red error on login)

The frontend is running but **nothing is on port 8000**.

1. Start **Terminal 1** with `.\start-backend.ps1` in `backend/`.
2. Wait for `Uvicorn running on http://127.0.0.1:8000`.
3. Refresh [http://localhost:3000](http://localhost:3000).

### `Activate.ps1` not found (Windows)

Use the script (it does not need activation):

```powershell
.\start-backend.ps1
```

Or call Python directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000
```

### `email-validator is not installed`

```powershell
.\.venv\Scripts\python.exe -m pip install email-validator "pydantic[email]"
```

### Gemini 404 / “model not found”

Set in `backend/.env`:

```env
GEMINI_MODEL=gemini-2.5-flash
```

Restart the backend.

### “Host privileges required” or “Only the host can end the room”

You are signed in as a **participant**, not the **room creator**.

1. Sign out.
2. Sign in as the account that **created** the room (e.g. `host@poiro.ai` for demo rooms).
3. Hard refresh (Ctrl+Shift+R).

### End room seems to do nothing

Update to the latest code and restart both servers. After ending, you should see a green success message and **Room ended** in the center. Old versions only changed a small status pill while the round still looked open.

### Python 3.14 slow `pip install`

Use Python 3.13:

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 5. Demo at a glance

```
Host  →  Create room  →  Share code  →  Start round
                                          │
                                          ▼
Participant joins  →  Submit prompt  →  Job queued
                                          │
                  WebSocket fans out: queued → running → completed
                                          │
                                          ▼
                       Host scores + picks winner  →  Leaderboard updates
```

* **Refresh-safe**: the snapshot endpoint and WS handshake rebuild the
  exact same state, so closing your browser does not lose the room.
* **Failure-aware**: every job can finish as `completed`, `failed`, or
  `timed_out`. Transient failures get one automatic retry.
* **Host vs participant**: the host *cannot* submit; participants
  *cannot* start rounds or score. Both rules are enforced server-side.

Demo logins are listed in [§3 Configuration & demo accounts](#3-configuration--demo-accounts).

---

## 6. Architecture overview

```
┌──────────────────────────────┐         ┌──────────────────────────────┐
│         Next.js  UI          │         │        FastAPI  API          │
│                              │         │                              │
│  ─ Zustand stores (auth +   │  HTTP   │  ─ /auth, /rooms, /rounds    │
│    room) act as the only   │ ───────▶│  ─ JWT auth on every route   │
│    UI state container       │         │  ─ Pydantic schemas          │
│                              │         │                              │
│  ─ RoomSocket: reconnecting │   WS    │  ─ /ws/rooms/{id}            │
│    WebSocket client.        │ ◀──────▶│  ─ ConnectionManager fans    │
│    Reducer maps named       │ events  │    events to all sockets in  │
│    events → store patches.  │         │    a room.                   │
└──────────────┬───────────────┘         └─────────────┬────────────────┘
               │                                       │
               │                                       │ enqueue Job
               │                                       ▼
               │                          ┌────────────────────────────┐
               │                          │  In-process asyncio.Queue  │
               │                          │  + N worker coroutines     │
               │                          │    (concurrency = N)       │
               │                          └─────────────┬──────────────┘
               │                                        │ call provider
               │                                        ▼
               │                          ┌────────────────────────────┐
               │                          │   AIProvider interface     │
               │                          │   ├─ GeminiProvider        │
               │                          │   └─ MockProvider          │
               │                          └─────────────┬──────────────┘
               │                                        │ persist
               │                                        ▼
               │                          ┌────────────────────────────┐
               └─────────── reads ───────▶│  SQLite (SQLAlchemy 2.0)   │
                                          │  + Event table (audit log) │
                                          └────────────────────────────┘
```

### Design pillars

1. **One source of truth per layer.** Database = persistent state.
   FastAPI = server state machine. Zustand = UI mirror.
2. **REST writes, WS reads.** Every write goes through HTTP so we get
   typed schemas, validation, and clean error semantics. The WebSocket
   channel is one-directional fan-out of named events. (Clients send
   only `ping` keepalives.) This avoids two ways to do the same thing.
3. **Events are first-class.** Every state change is written to the
   `events` table *and* broadcast over WS using the same payload. The
   audit log and the realtime stream cannot drift.
4. **Provider is a seam.** The worker never imports Gemini directly; it
   calls `get_provider().generate(prompt)`. Swapping models, or running
   the entire demo with the mock provider, is one env variable.

---

## 7. Database schema

SQLite via SQLAlchemy 2.0. The schema mirrors the assignment's required
entities so the README diagram and the code stay 1:1.

```
users (id, email, display_name, password_hash, created_at)
rooms (id, code, name, prompt, status, host_id → users, current_round_id, created_at)
participants (id, room_id → rooms, user_id → users, role[host|participant], is_active, joined_at)
rounds (id, room_id → rooms, round_number, prompt, status, winner_submission_id, started_at, ended_at)
submissions (id, round_id → rounds, user_id → users, prompt, created_at)
jobs (id, submission_id → submissions, status, attempt, provider, output, error, created_at, started_at, completed_at)
scores (id, submission_id → submissions, value, note, scored_by_user_id, created_at)
events (id, room_id → rooms, type, payload(json), created_at)         ← append-only audit log
```

### Why SQLite

The assignment says *“Choose the simplest database that supports your
design and explain the tradeoff.”* Everything I need is single-writer
(one FastAPI process drives both HTTP and the in-process worker), the
total dataset for a demo is well under a megabyte, and SQLite gives us
ACID transactions, foreign keys, JSON columns, and zero ops cost.

**Tradeoff** I am accepting: SQLite locks the file briefly during write
transactions, so this would not survive horizontal scale-out. The
schema is portable — switching `DATABASE_URL` to `postgresql+psycopg://…`
is a one-line change because nothing in the code relies on SQLite-only
features.

---

## 8. Realtime event model

All event names live in [`backend/app/events.py`](backend/app/events.py)
so the client and server cannot drift. Every WS payload is shaped:

```jsonc
{ "type": "round.started",
  "payload": { "round_id": "…", "round_number": 1, "prompt": "…" },
  "ts":      "2026-05-21T18:42:11.041Z" }
```

| Event                         | Producer                | Frontend reaction                             |
|-------------------------------|-------------------------|-----------------------------------------------|
| `room.snapshot`               | WS handshake            | Fully hydrate the Zustand store               |
| `room.participant_joined`     | `POST /rooms/join`      | Append to participants list                   |
| `room.state_changed`          | host actions            | Update room status pill                       |
| `round.started`               | `POST /rooms/{id}/rounds` | Open the submission UI                      |
| `round.submission_created`    | `POST …/submissions`    | Add a card in `queued` state                  |
| `round.state_changed`         | worker (auto-advance)   | Flip round to `scoring` once all jobs settled |
| `round.winner_picked`         | host action             | Highlight the winning card                    |
| `round.completed`             | host action             | Move round into history + unlock lobby        |
| `job.queued` / `job.running`  | worker                  | Animate the card; show provider name          |
| `job.completed`               | worker                  | Render the generated copy                     |
| `job.failed` / `job.timed_out`| worker                  | Show a red error state with retry hint        |
| `score.recorded`              | host action             | Update score + leaderboard                    |

Refresh hydration: the WS endpoint sends `room.snapshot` immediately on
connect, so the client never has to chase down a missed event after a
reload. Reconnect is exponential-backoff (max 8s) with full snapshot on
reattach.

---

## 9. Generation job lifecycle

```
        ┌─────────┐    worker picks    ┌─────────┐
HTTP →  │ queued  │ ─────────────────▶ │ running │
        └─────────┘                    └────┬────┘
                                            │
                  ┌───────────────────┬─────┴────────────────┐
                  ▼                   ▼                      ▼
              completed             failed              timed_out
                                       │                      │
                            transient + attempts < max ──▶ new queued Job
```

Implementation: [`backend/app/workers/job_worker.py`](backend/app/workers/job_worker.py).

* **Non-blocking enqueue.** `POST …/submissions` inserts the
  `Submission` + a `Job(status=queued)` row, broadcasts `job.queued`,
  pushes the job id onto an `asyncio.Queue`, and returns 200 in
  milliseconds. **The HTTP request never waits for the AI provider.**
* **Bounded concurrency.** `WORKER_CONCURRENCY` (default 3) worker
  coroutines drain the queue.
* **Per-job hard timeout.** Each attempt is wrapped in
  `asyncio.wait_for(provider.generate(...), timeout=JOB_TIMEOUT_SECONDS)`.
  Exceeding it transitions the job to `timed_out`.
* **Retries.** If the provider raises a `ProviderError(retriable=True)`
  (e.g. a Gemini 429 / 503) and attempts are under `JOB_MAX_ATTEMPTS`,
  a fresh `Job(attempt=n+1, status=queued)` row is created and
  re-enqueued after linear backoff. Every attempt is kept in the table
  so the timeline is fully auditable.
* **Round auto-advance.** When every submission in a round reaches a
  terminal state, the worker flips the round to `scoring` and
  broadcasts `round.state_changed`, unlocking the host scoring UI.

This is intentionally **not** Celery/RQ. The assignment explicitly
accepts *“a lightweight in-process worker”* and that is the simplest
honest choice for a single-process FastAPI app with SQLite. Promoting
to RQ would mean (a) swapping `asyncio.Queue.put_nowait` for `rq.enqueue`
and (b) running a separate `rq worker` process — the rest of the code
is already structured for it.

---

## 10. Battle / judging mechanism (the intentional gap)

The assignment intentionally leaves *“what makes one submission better
than another”* open and asks us to defend our choice.

### What I built — **Host-Judged Score + Pick-a-Winner**

* The host sees every completed generation in the same card grid.
* For each, the host drags a 0–10 slider and presses **Save score**.
  Scores are persisted (`scores` row, one-to-one with submission).
* The host then presses **Pick as winner** on exactly one card per
  round. That submission's user gets +1 to their `wins`. The
  leaderboard ranks by `(wins desc, total_score desc)`.

### Why this mechanism

1. **It is the only mechanism that always works.** Audience voting needs
   a quorum; LLM-as-judge introduces a second provider that can fail
   the demo; deterministic rubrics ("longest output wins") punish good
   answers. A live host can judge with full context.
2. **It maps cleanly to the product idea.** Poiro pitches itself as a
   creative platform with humans in the loop. A host-judged round
   models that loop literally.
3. **It is auditable.** Every score is written to a row tied to a user.
   In a production system we could replay them.

### Weaknesses I am explicit about

* **Bias.** The host can score arbitrarily; nothing prevents them from
  always picking their friend.
* **Single-rater variance.** No inter-rater reliability check.
* **Cold start.** With 0 submissions, the leaderboard is empty.

### How I would harden it in production (see §16)

* Add a second axis: **audience voting** (1 vote per participant, 30s
  window after generation), and surface both scores.
* Add an **LLM judge** option that scores along three dimensions
  (relevance, originality, executability) and blend with host weight.
* Track score **distributions over rounds** to surface biased hosts.

---

## 11. What is persisted vs. ephemeral

Persisted (SQLite):

* Users + password hashes + JWT subject mapping.
* Rooms (including code, host, brief, status).
* Rounds, submissions, jobs (every attempt), scores, winner pick.
* `events` table — append-only log of every meaningful state change.

Ephemeral (in-process):

* WebSocket connection set (we know "this socket is interested in this
  room id"). On restart, clients reconnect and hydrate from the DB.
* The asyncio job queue — *on restart, jobs that were `queued` in DB
  but never re-enqueued would stay in `queued` indefinitely.* This is a
  known limitation (§15); a startup hook to re-enqueue any non-terminal
  jobs would fix it in ~10 lines.

---

## 12. Failure handling strategy

| Failure                         | Surface                                              |
|---------------------------------|------------------------------------------------------|
| Bad auth                        | 401 with `{"detail": "..."}`, UI shows form-level message |
| Non-participant joins room URL  | Auto-call `/rooms/join`; if room is closed → 410     |
| Host tries to submit            | 403 *before* writing — UI hides the form too         |
| Participant tries `/start_round`| 403 from `require_host` dependency                   |
| Duplicate submission            | 409 — UI keeps the existing submission card          |
| Provider transient error        | Job marked `failed`, retried up to `JOB_MAX_ATTEMPTS`, new attempt visible |
| Provider hard timeout           | Job marked `timed_out`, red card with error          |
| Empty Gemini response (safety)  | Non-retriable `ProviderError`, card shows reason     |
| Backend unreachable             | API client raises `ApiError(status=0)` with friendly copy |
| Frontend WS drop                | RoomSocket reconnects (exp backoff, jitter, cap 8s), then re-receives `room.snapshot` |

A failed job **does not break the round**. The auto-advance logic
treats `completed | failed | timed_out` all as terminal, so one
exploding submission can't hang the room.

---

## 13. Roles & backend-enforced permissions

The assignment calls this out as a strong signal vs. a common pitfall.
Every privileged action goes through one of two FastAPI dependencies:

```python
require_participant(room_id, user, db)   # POST submissions, read state
require_host(room_id, user, db)          # start round, score, pick winner, end room
```

| Action            | Allowed roles                          |
|-------------------|----------------------------------------|
| Create room       | any authenticated user (becomes host)  |
| Join room         | any authenticated user                 |
| Start round       | **host only**                          |
| Submit prompt     | **participants only** (host blocked)   |
| Score submission  | **host only**                          |
| Pick winner       | **host only**                          |
| End room          | **host only**                          |

The UI also hides the wrong buttons for each role, but those checks are
strictly cosmetic; pulling out devtools and pressing the API directly
returns a 403.

---

## 14. Tradeoffs & explicit non-goals

| Tradeoff                                        | Reason                                                                                 |
|-------------------------------------------------|----------------------------------------------------------------------------------------|
| In-process worker, not Celery                   | Single-process FastAPI is the simplest honest design; provider seam keeps it portable. |
| SQLite, not Postgres                            | Zero ops, perfectly sufficient for one room at a time.                                 |
| JWT in `localStorage`, not HttpOnly cookies     | Production-grade auth was an explicit non-goal. Identity persists across refresh.      |
| WS is fan-out only (client writes via REST)     | One write path → typed schemas, easier auth, no message-format duplication.            |
| REST first, WS for streaming                    | Same reason — clear contract, easy to test with `curl`/Swagger.                        |
| One-host-judges scoring                         | Demo always works without a quorum and matches Poiro's "human + AI" pitch.             |
| Provider abstraction with mock fallback         | Demo never hard-fails if a key is missing or quota is hit.                             |

I deliberately did **not** build: media generation, OAuth, payments,
admin panels, perfect mobile responsiveness, K8s deployment, advanced
safety/moderation, or multiple tournament formats. All of these were
explicit non-goals.

---

## 15. Known limitations

1. **Worker is in-process.** If the server crashes mid-round, jobs that
   were `running` will not be picked back up on restart. I do persist
   the row, but I don't have a startup hook that re-enqueues
   non-terminal jobs (~10 lines to add).
2. **No spectator mode.** Listeners must be participants. Adding a
   `spectator` role would be one enum value + one branch in `require_host`.
3. **No retry button in the UI.** The worker auto-retries transient
   failures once; a manual "regenerate this submission" button would be
   easy but the assignment treats it as optional.
4. **Single-round-at-a-time.** A room only ever has one active round;
   the model supports many rounds in history but not concurrent rounds.
5. **No automated tests checked in.** I would add pytest coverage of
   the worker state machine and the role guards next; the worker code
   is structured to be unit-testable (`_load_and_mark_running` and
   `_maybe_advance_round` are pure DB functions).
6. **Mobile is functional, not delightful.** Layout collapses to one
   column under `lg`, but interaction density is tuned for laptop.
7. **No rate limits.** Anyone can spam submissions. Realistically the
   round-level "one submission per user" rule contains this for now.

---

## 16. What I would improve with more time

In rough priority order:

1. **Persist & re-enqueue non-terminal jobs on boot** — production
   correctness, ~10 lines.
2. **LLM-as-judge + audience vote blend** — directly addresses the
   "intentional product gap" with a richer mechanism.
3. **Pytest suite** for the worker state machine, role guards, and the
   reducer in `roomStore.ts` (the reducers are already pure).
4. **Real media generation.** Swap `GeminiProvider.generate` for an
   image model (or chain text→image) and stream a final asset URL.
5. **Spectator mode + reactions.** New role, new event names, easy fit
   into the existing event model.
6. **Retry/backoff UX.** Surface a "regenerate" button on failed cards.
7. **Move provider call to a separate `worker` process** behind RQ/Arq
   once horizontal scale matters.
8. **Postgres + Alembic migrations** for any multi-tenant deployment.
9. **Mobile polish + accessibility pass.**
10. **Hosted deployment** (frontend → Vercel, backend → Fly.io,
    database → managed Postgres).

---

## 17. Repo layout

```
poiro-ai-battle-room/
├── README.md                ← you are here
├── .gitignore
├── backend/
│   ├── .env.example
│   ├── start-backend.ps1    ← one-command setup + run (Windows/macOS/Linux)
│   ├── requirements.txt
│   └── app/
│       ├── main.py          ← FastAPI app + lifespan + CORS
│       ├── config.py        ← Pydantic settings
│       ├── database.py      ← engine, session, Base
│       ├── models.py        ← SQLAlchemy ORM models
│       ├── schemas.py       ← Pydantic request/response shapes
│       ├── auth.py          ← bcrypt + JWT helpers
│       ├── deps.py          ← auth + role guards (require_host, etc.)
│       ├── events.py        ← canonical event names
│       ├── services.py      ← state-shaping helpers (room snapshot, leaderboard)
│       ├── seed.py          ← `python -m app.seed`
│       ├── providers/
│       │   ├── base.py      ← AIProvider interface + ProviderError
│       │   ├── gemini.py    ← Google Gemini implementation
│       │   └── mock.py      ← deterministic-ish mock with latency/failure/timeout
│       ├── workers/
│       │   └── job_worker.py← asyncio worker pool + retry/timeout/auto-advance
│       ├── ws/
│       │   └── manager.py   ← ConnectionManager (room → sockets)
│       └── routers/
│           ├── auth.py      ← /auth (signup, login, me)
│           ├── rooms.py     ← /rooms (create, join, snapshot, end)
│           ├── rounds.py    ← /rooms/{id}/rounds + submissions + score + winner
│           └── ws.py        ← /ws/rooms/{id} handshake + snapshot push
└── frontend/
    ├── .env.local.example
    ├── start-frontend.ps1     ← install deps + npm run dev
    ├── package.json
    ├── tailwind.config.ts
    ├── tsconfig.json
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx           ← landing + login/signup
        │   ├── dashboard/page.tsx ← my rooms + create/join
        │   └── room/[code]/page.tsx ← the battle room
        ├── components/
        │   ├── HostControls.tsx
        │   ├── ParticipantPanel.tsx
        │   ├── SubmissionCard.tsx
        │   ├── Leaderboard.tsx
        │   ├── ActivityFeed.tsx
        │   └── StatusPill.tsx
        ├── lib/
        │   ├── api.ts             ← typed fetch wrapper
        │   ├── ws.ts              ← reconnecting RoomSocket
        │   └── types.ts           ← schema mirror
        └── stores/
            ├── authStore.ts
            └── roomStore.ts       ← pure reducers per event type
```

---

Thanks for reading — and for the carefully scoped brief. Building this
was genuinely fun. If anything in the loop is unclear, the
`/health` and `/docs` endpoints on the backend and the
**Realtime activity** column on the right-hand side of the room view
were both designed to make the system observable while the demo is
running.

— Sarthak
