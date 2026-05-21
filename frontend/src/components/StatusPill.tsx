import clsx from "clsx";
import type { JobStatus, RoomStatus, RoundStatus } from "@/lib/types";

const colorMap: Record<string, { dot: string; text: string; bg: string }> = {
  queued: { dot: "bg-warn", text: "text-warn", bg: "border-warn/40 bg-warn/10" },
  running: {
    dot: "bg-accent2",
    text: "text-accent2",
    bg: "border-accent2/40 bg-accent2/10",
  },
  completed: { dot: "bg-ok", text: "text-ok", bg: "border-ok/40 bg-ok/10" },
  failed: { dot: "bg-danger", text: "text-danger", bg: "border-danger/40 bg-danger/10" },
  timed_out: {
    dot: "bg-danger",
    text: "text-danger",
    bg: "border-danger/40 bg-danger/10",
  },
  lobby: { dot: "bg-muted", text: "text-white/80", bg: "border-edge bg-ink/60" },
  in_round: {
    dot: "bg-accent",
    text: "text-accent",
    bg: "border-accent/40 bg-accent/10",
  },
  scoring: {
    dot: "bg-accent2",
    text: "text-accent2",
    bg: "border-accent2/40 bg-accent2/10",
  },
  ended: { dot: "bg-muted", text: "text-muted", bg: "border-edge bg-ink/40" },
  open: { dot: "bg-accent", text: "text-accent", bg: "border-accent/40 bg-accent/10" },
  generating: {
    dot: "bg-accent2",
    text: "text-accent2",
    bg: "border-accent2/40 bg-accent2/10",
  },
};

export function StatusPill({
  status,
  label,
}: {
  status: JobStatus | RoomStatus | RoundStatus | string;
  label?: string;
}) {
  const c = colorMap[status] ?? colorMap.lobby;
  const animated = status === "running" || status === "queued" || status === "generating";
  return (
    <span className={clsx("chip", c.bg, c.text)}>
      <span
        className={clsx("h-1.5 w-1.5 rounded-full", c.dot, animated && "animate-pulseDot")}
      />
      {label ?? status.replace(/_/g, " ")}
    </span>
  );
}
