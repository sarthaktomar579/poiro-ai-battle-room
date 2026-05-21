import type { WSEvent } from "@/lib/types";

const labels: Record<string, string> = {
  "room.snapshot": "Connected",
  "room.participant_joined": "Joined",
  "room.participant_left": "Left",
  "room.state_changed": "Room",
  "round.started": "Round started",
  "round.submission_created": "New submission",
  "round.state_changed": "Round",
  "round.completed": "Round complete",
  "round.winner_picked": "Winner picked",
  "job.queued": "Job queued",
  "job.running": "Job running",
  "job.completed": "Job done",
  "job.failed": "Job failed",
  "job.timed_out": "Job timed out",
  "score.recorded": "Score recorded",
};

const colors: Record<string, string> = {
  "round.started": "text-accent",
  "round.winner_picked": "text-accent",
  "round.completed": "text-accent",
  "job.completed": "text-ok",
  "job.failed": "text-danger",
  "job.timed_out": "text-danger",
  "job.running": "text-accent2",
};

export function ActivityFeed({ events }: { events: WSEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-edge bg-ink/40 px-3 py-3 text-sm text-white/50">
        No realtime activity yet.
      </div>
    );
  }
  return (
    <ul className="space-y-1 font-mono text-xs">
      {events.map((e, i) => (
        <li
          key={`${e.ts}-${i}`}
          className="flex items-center gap-2 rounded-md border border-edge/60 bg-ink/40 px-2 py-1"
        >
          <span className="text-white/30">
            {new Date(e.ts).toLocaleTimeString()}
          </span>
          <span className={colors[e.type] ?? "text-white/80"}>
            {labels[e.type] ?? e.type}
          </span>
        </li>
      ))}
    </ul>
  );
}
