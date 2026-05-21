"use client";

import { useState } from "react";
import clsx from "clsx";

import type { Submission } from "@/lib/types";
import { StatusPill } from "./StatusPill";

interface Props {
  submission: Submission;
  isHost: boolean;
  isMine: boolean;
  isWinner: boolean;
  canScore: boolean;
  onScore?: (value: number) => Promise<void> | void;
  onPickWinner?: () => Promise<void> | void;
}

export function SubmissionCard({
  submission,
  isHost,
  isMine,
  isWinner,
  canScore,
  onScore,
  onPickWinner,
}: Props) {
  const job = submission.latest_job;
  const status = job?.status ?? "queued";
  const isError = status === "failed" || status === "timed_out";
  const [busy, setBusy] = useState(false);
  const [scoreValue, setScoreValue] = useState(submission.score?.value ?? 7);

  const submit = async () => {
    if (!onScore) return;
    setBusy(true);
    try {
      await onScore(scoreValue);
    } finally {
      setBusy(false);
    }
  };

  const pick = async () => {
    if (!onPickWinner) return;
    setBusy(true);
    try {
      await onPickWinner();
    } finally {
      setBusy(false);
    }
  };

  return (
    <article
      className={clsx(
        "panel animate-slideUp space-y-3 p-5",
        isWinner && "border-accent/80 shadow-[0_0_30px_-6px_rgba(196,255,62,0.5)]",
        isError && "border-danger/40",
      )}
    >
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-full bg-accent/10 text-accent">
            {submission.display_name?.slice(0, 1).toUpperCase() || "?"}
          </div>
          <div>
            <div className="text-sm font-semibold">
              {submission.display_name || "Anonymous"}{" "}
              {isMine && <span className="text-xs text-accent">(you)</span>}
            </div>
            <div className="text-[11px] text-white/40">
              attempt {job?.attempt ?? 1} · {job?.provider ?? "—"}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isWinner && <span className="chip text-accent border-accent/60">Winner</span>}
          <StatusPill status={status} />
        </div>
      </header>

      {submission.prompt ? (
        <p className="rounded-xl border border-edge bg-ink/60 px-3 py-2 text-sm text-white/80">
          <span className="text-[10px] uppercase tracking-wider text-muted">
            prompt
          </span>
          <br />
          {submission.prompt}
        </p>
      ) : null}

      {status === "queued" && (
        <div className="rounded-xl border border-edge bg-ink/40 px-3 py-3 text-sm text-white/60">
          Waiting in the queue...
        </div>
      )}

      {status === "running" && (
        <div className="rounded-xl border border-accent2/40 bg-accent2/10 px-3 py-3 text-sm text-accent2">
          <span className="mr-2 inline-block h-2 w-2 animate-pulseDot rounded-full bg-accent2" />
          Generating with {job?.provider || "AI"}...
        </div>
      )}

      {status === "completed" && job?.output && (
        <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-xl border border-ok/30 bg-ok/5 px-3 py-3 font-sans text-sm leading-relaxed text-white/90">
          {job.output}
        </pre>
      )}

      {isError && (
        <div className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-3 text-sm text-danger">
          <div className="font-semibold">
            {status === "timed_out" ? "Timed out" : "Generation failed"}
          </div>
          <div className="text-xs opacity-80">{job?.error || "Unknown error"}</div>
        </div>
      )}

      {isHost && canScore && status === "completed" && (
        <div className="flex flex-wrap items-center gap-3 border-t border-edge pt-3">
          <div className="flex items-center gap-2 text-xs text-white/60">
            Score
            <input
              type="range"
              min={0}
              max={10}
              step={0.5}
              value={scoreValue}
              onChange={(e) => setScoreValue(Number(e.target.value))}
              className="accent-accent"
            />
            <span className="w-10 text-center font-mono text-accent">
              {scoreValue.toFixed(1)}
            </span>
          </div>
          <button className="btn-ghost text-xs" onClick={submit} disabled={busy}>
            {submission.score ? "Update score" : "Save score"}
          </button>
          <button className="btn-primary text-xs" onClick={pick} disabled={busy}>
            Pick as winner
          </button>
        </div>
      )}

      {submission.score && (
        <div className="flex items-center justify-between border-t border-edge pt-3 text-xs text-white/60">
          <span>Host score</span>
          <span className="font-mono text-lg font-bold text-accent">
            {submission.score.value.toFixed(1)}
          </span>
        </div>
      )}
    </article>
  );
}
