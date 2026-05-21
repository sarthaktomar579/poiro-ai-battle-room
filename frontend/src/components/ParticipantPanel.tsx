"use client";

import { useMemo, useState } from "react";

import type { RoomState, User } from "@/lib/types";
import { api, ApiError } from "@/lib/api";

interface Props {
  state: RoomState;
  user: User;
  onError?: (msg: string) => void;
}

export function ParticipantPanel({ state, user, onError }: Props) {
  const round = state.current_round;
  const mySubmission = useMemo(
    () => round?.submissions.find((s) => s.user_id === user.id) ?? null,
    [round, user.id],
  );
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!round) return;
    setBusy(true);
    try {
      await api.submit(state.room.id, round.id, prompt.trim());
      setPrompt("");
    } catch (e) {
      onError?.(e instanceof ApiError ? e.message : "Submission failed");
    } finally {
      setBusy(false);
    }
  };

  if (!round) {
    return (
      <section className="panel space-y-3 p-5">
        <div className="flex items-center justify-between">
          <h3 className="font-display font-semibold">Waiting room</h3>
          <span className="chip text-accent2 border-accent2/40">participant</span>
        </div>
        <p className="text-sm text-white/60">
          Sit tight. The host hasn't started the next round yet.
        </p>
      </section>
    );
  }

  if (mySubmission) {
    return (
      <section className="panel space-y-3 p-5">
        <h3 className="font-display font-semibold">Your submission is in</h3>
        <p className="rounded-xl border border-edge bg-ink/60 px-3 py-2 text-sm text-white/80">
          {mySubmission.prompt}
        </p>
        <p className="text-xs text-white/50">
          Watch the cards on the right as your job moves from{" "}
          <span className="text-accent">queued</span> →{" "}
          <span className="text-accent2">running</span> →{" "}
          <span className="text-ok">completed</span>.
        </p>
      </section>
    );
  }

  if (round.status !== "open") {
    return (
      <section className="panel space-y-3 p-5">
        <h3 className="font-display font-semibold">Submissions closed</h3>
        <p className="text-sm text-white/60">
          You didn't submit in time for round {round.round_number}. The host is
          now scoring.
        </p>
      </section>
    );
  }

  return (
    <section className="panel space-y-3 p-5">
      <div className="flex items-center justify-between">
        <h3 className="font-display font-semibold">Round {round.round_number}</h3>
        <span className="chip text-accent2 border-accent2/40">participant</span>
      </div>
      <p className="text-sm text-white/70">
        <span className="text-[10px] uppercase tracking-wider text-muted">
          Host brief
        </span>
        <br />
        {round.prompt}
      </p>
      <div>
        <label className="label mb-1">Your prompt</label>
        <textarea
          className="input min-h-[100px] resize-y"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Twist the brief, ride the brief, or break the brief."
          maxLength={2000}
        />
      </div>
      <button
        className="btn-primary w-full"
        onClick={submit}
        disabled={busy || !prompt.trim()}
      >
        {busy ? "Submitting..." : "Submit to the battle"}
      </button>
    </section>
  );
}
