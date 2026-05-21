"use client";

import { useState } from "react";

import type { RoomState } from "@/lib/types";
import { api, ApiError } from "@/lib/api";

interface Props {
  state: RoomState;
  onError?: (msg: string) => void;
}

export function HostControls({ state, onError }: Props) {
  const [prompt, setPrompt] = useState(state.room.prompt);
  const [busy, setBusy] = useState(false);

  const hasOpenRound = state.current_round?.status === "open";
  const hasGeneratingRound = state.current_round?.status === "generating";
  const hasScoringRound = state.current_round?.status === "scoring";
  const inLobby = !state.current_round;

  const start = async () => {
    setBusy(true);
    try {
      await api.startRound(state.room.id, prompt.trim() || undefined);
    } catch (e) {
      onError?.(e instanceof ApiError ? e.message : "Could not start round");
    } finally {
      setBusy(false);
    }
  };

  const endRoom = async () => {
    if (!confirm("End the room? Participants will lose write access.")) return;
    setBusy(true);
    try {
      await api.endRoom(state.room.id);
    } catch (e) {
      onError?.(e instanceof ApiError ? e.message : "Could not end room");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel space-y-3 p-5">
      <div className="flex items-center justify-between">
        <h3 className="font-display font-semibold">Host controls</h3>
        <span className="chip text-accent border-accent/40">host</span>
      </div>

      <div>
        <label className="label mb-1">Round prompt</label>
        <textarea
          className="input min-h-[88px] resize-y"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          maxLength={2000}
          placeholder="Leave blank to reuse the room's brief."
          disabled={hasOpenRound || hasGeneratingRound || hasScoringRound}
        />
      </div>

      {inLobby && (
        <button className="btn-primary w-full" disabled={busy} onClick={start}>
          Start round {state.past_rounds.length + 1}
        </button>
      )}

      {hasOpenRound && (
        <div className="rounded-xl border border-accent/40 bg-accent/5 px-3 py-3 text-sm text-accent">
          Round is open. Participants are submitting prompts.
        </div>
      )}
      {hasGeneratingRound && (
        <div className="rounded-xl border border-accent2/40 bg-accent2/5 px-3 py-3 text-sm text-accent2">
          Generation in progress. Watch the cards stream in real time.
        </div>
      )}
      {hasScoringRound && (
        <div className="rounded-xl border border-warn/40 bg-warn/5 px-3 py-3 text-sm text-warn">
          All jobs finalized. Score submissions and crown a winner.
        </div>
      )}

      <button className="btn-danger w-full" onClick={endRoom} disabled={busy}>
        End room
      </button>
    </section>
  );
}
