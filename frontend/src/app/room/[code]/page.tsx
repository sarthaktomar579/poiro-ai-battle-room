"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { api, ApiError } from "@/lib/api";
import { RoomSocket } from "@/lib/ws";
import { useAuthStore } from "@/stores/authStore";
import { useRoomStore } from "@/stores/roomStore";
import { ActivityFeed } from "@/components/ActivityFeed";
import { HostControls } from "@/components/HostControls";
import { Leaderboard } from "@/components/Leaderboard";
import { ParticipantPanel } from "@/components/ParticipantPanel";
import { StatusPill } from "@/components/StatusPill";
import { SubmissionCard } from "@/components/SubmissionCard";

export default function RoomPage() {
  const params = useParams<{ code: string }>();
  const router = useRouter();
  const { token, user, hydrate, setSession, clear } = useAuthStore();
  const {
    status,
    error,
    wsStatus,
    state,
    recentEvents,
    setError,
    setLoading,
    setState,
    setWsStatus,
    applyEvent,
    reset,
  } = useRoomStore();
  const sockRef = useRef<RoomSocket | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (token === null) {
      const t = setTimeout(() => {
        if (!useAuthStore.getState().token) router.replace("/");
      }, 50);
      return () => clearTimeout(t);
    }
  }, [token, router]);

  // Sync JWT user, then load room + websocket (re-run when account changes).
  useEffect(() => {
    if (!token || !params.code) return;

    let cancelled = false;

    const load = async () => {
      setLoading();
      setActionError(null);
      try {
        const me = await api.me();
        if (cancelled) return;
        setSession(token, me);

        let snapshot;
        try {
          snapshot = await api.roomByCode(params.code.toUpperCase());
        } catch (e) {
          if (e instanceof ApiError && e.status === 403) {
            snapshot = await api.joinRoom(params.code.toUpperCase());
          } else {
            throw e;
          }
        }
        if (cancelled) return;

        setState(snapshot);
        sockRef.current?.stop();
        const sock = new RoomSocket({
          roomId: snapshot.room.id,
          token,
          onEvent: applyEvent,
          onStatus: setWsStatus,
        });
        sock.start();
        sockRef.current = sock;
      } catch (e) {
        if (!cancelled) {
          if (e instanceof ApiError && e.status === 401) clear();
          setError(e instanceof ApiError ? e.message : "Could not load room");
        }
      }
    };

    load();

    return () => {
      cancelled = true;
      sockRef.current?.stop();
      sockRef.current = null;
      reset();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, params.code]);

  // Only the room owner (rooms.host_id) may use host controls — matches backend.
  const isHost = useMemo(
    () => Boolean(state && user && state.room.host_id === user.id),
    [state, user],
  );

  const onScore = async (submissionId: string, value: number) => {
    if (!state?.current_round) return;
    try {
      await api.score(state.room.id, state.current_round.id, {
        submission_id: submissionId,
        value,
      });
    } catch (e) {
      setActionError(e instanceof ApiError ? e.message : "Could not score submission");
    }
  };

  const onPickWinner = async (submissionId: string) => {
    if (!state?.current_round) return;
    try {
      await api.pickWinner(state.room.id, state.current_round.id, submissionId);
    } catch (e) {
      setActionError(e instanceof ApiError ? e.message : "Could not pick winner");
    }
  };

  const copy = async () => {
    if (!state) return;
    try {
      await navigator.clipboard.writeText(state.room.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {}
  };

  if (status === "loading" || !state) {
    return (
      <main className="grid min-h-screen place-items-center text-white/60">
        {error ? (
          <div className="panel max-w-md p-6">
            <h2 className="font-display text-lg font-semibold text-danger">
              Could not load room
            </h2>
            <p className="mt-2 text-sm text-white/60">{error}</p>
            <button className="btn-ghost mt-4" onClick={() => router.push("/dashboard")}>
              Back to dashboard
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 animate-pulseDot rounded-full bg-accent" />
            Hydrating room...
          </div>
        )}
      </main>
    );
  }

  const round = state.current_round;

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <button
            className="mb-2 text-xs text-muted hover:text-white"
            onClick={() => router.push("/dashboard")}
          >
            ← Dashboard
          </button>
          <h1 className="font-display text-3xl font-bold tracking-tight">
            {state.room.name}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-white/60">
            <span className="text-[10px] uppercase tracking-wider text-muted">
              Brief
            </span>
            <br />
            {state.room.prompt}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            <StatusPill status={state.room.status} />
            <span
              className={`chip ${wsStatus === "open" ? "text-ok border-ok/40" : "text-warn border-warn/40"}`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${wsStatus === "open" ? "bg-ok" : "bg-warn animate-pulseDot"}`}
              />
              {wsStatus === "open" ? "live" : wsStatus}
            </span>
          </div>
          <button
            onClick={copy}
            className="font-mono text-xl tracking-[0.35em] text-accent hover:text-accent/80"
          >
            {state.room.code}
            <span className="ml-2 text-[10px] uppercase tracking-wider text-muted">
              {copied ? "copied" : "click to copy"}
            </span>
          </button>
        </div>
      </header>

      {actionError && (
        <div className="mb-4 rounded-xl border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          {actionError}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr_300px]">
        {/* Left: role-specific control panel + participants + leaderboard */}
        <aside className="space-y-4">
          {isHost ? (
            <HostControls state={state} onError={setActionError} />
          ) : user ? (
            <ParticipantPanel state={state} user={user} onError={setActionError} />
          ) : null}

          <section className="panel p-5">
            <h3 className="mb-3 font-display font-semibold">
              Participants ({state.participants.length})
            </h3>
            <ul className="space-y-1.5 text-sm">
              {state.participants.map((p) => (
                <li key={p.id} className="flex items-center justify-between">
                  <span>
                    {p.display_name}
                    {user?.id === p.user_id && (
                      <span className="ml-1 text-xs text-accent">(you)</span>
                    )}
                  </span>
                  <span
                    className={`text-[10px] uppercase tracking-wider ${
                      p.role === "host" ? "text-accent" : "text-muted"
                    }`}
                  >
                    {p.role}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel p-5">
            <h3 className="mb-3 font-display font-semibold">Leaderboard</h3>
            <Leaderboard entries={state.leaderboard} />
          </section>
        </aside>

        {/* Center: live round */}
        <section className="space-y-4">
          {round ? (
            <>
              <div className="panel flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted">
                    Round {round.round_number}
                  </div>
                  <div className="text-sm text-white/80">{round.prompt}</div>
                </div>
                <StatusPill status={round.status} />
              </div>

              {round.submissions.length === 0 ? (
                <div className="panel p-8 text-center text-white/50">
                  No submissions yet. Waiting on the contestants...
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {round.submissions.map((s) => (
                    <SubmissionCard
                      key={s.id}
                      submission={s}
                      isHost={isHost}
                      isMine={user?.id === s.user_id}
                      isWinner={round.winner_submission_id === s.id}
                      canScore={round.status === "scoring" || round.status === "completed"}
                      onScore={(v) => onScore(s.id, v)}
                      onPickWinner={() => onPickWinner(s.id)}
                    />
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="panel p-10 text-center">
              <h3 className="font-display text-xl font-semibold">
                {state.past_rounds.length === 0 ? "Lobby" : "Between rounds"}
              </h3>
              <p className="mt-2 text-sm text-white/60">
                {isHost
                  ? "Use the host panel to launch the next round."
                  : "Waiting for the host to start the next round."}
              </p>
            </div>
          )}

          {state.past_rounds.length > 0 && (
            <details className="panel p-5">
              <summary className="cursor-pointer font-display font-semibold">
                Past rounds ({state.past_rounds.length})
              </summary>
              <div className="mt-4 space-y-4">
                {state.past_rounds.map((r) => (
                  <div key={r.id} className="rounded-xl border border-edge bg-ink/40 p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs uppercase tracking-wider text-muted">
                        Round {r.round_number}
                      </span>
                      <StatusPill status={r.status} />
                    </div>
                    <div className="mb-3 text-sm text-white/70">{r.prompt}</div>
                    <ul className="space-y-1 text-xs">
                      {r.submissions.map((s) => (
                        <li
                          key={s.id}
                          className={`flex items-center justify-between rounded-md border px-2 py-1 ${
                            r.winner_submission_id === s.id
                              ? "border-accent/60 bg-accent/5 text-accent"
                              : "border-edge bg-ink/30 text-white/70"
                          }`}
                        >
                          <span>
                            {s.display_name}
                            {r.winner_submission_id === s.id && " · winner"}
                          </span>
                          <span className="font-mono">
                            {s.score ? s.score.value.toFixed(1) : "—"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </details>
          )}
        </section>

        {/* Right: realtime activity feed */}
        <aside className="space-y-4">
          <section className="panel p-5">
            <h3 className="mb-3 font-display font-semibold">Realtime activity</h3>
            <ActivityFeed events={recentEvents} />
          </section>
        </aside>
      </div>
    </main>
  );
}
