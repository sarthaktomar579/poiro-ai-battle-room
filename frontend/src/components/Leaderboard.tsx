import type { LeaderboardEntry } from "@/lib/types";

export function Leaderboard({ entries }: { entries: LeaderboardEntry[] }) {
  if (entries.length === 0) {
    return (
      <div className="rounded-xl border border-edge bg-ink/40 px-3 py-3 text-sm text-white/50">
        Leaderboard fills up once a round has been scored.
      </div>
    );
  }
  return (
    <ol className="space-y-2">
      {entries.map((e, idx) => (
        <li
          key={e.user_id}
          className="flex items-center justify-between rounded-xl border border-edge bg-ink/50 px-3 py-2"
        >
          <div className="flex items-center gap-3">
            <span className="w-5 text-center font-mono text-xs text-white/40">
              {idx + 1}
            </span>
            <span className="font-medium">{e.display_name}</span>
            {e.wins > 0 && (
              <span className="chip text-accent border-accent/40 text-[10px]">
                {e.wins} win{e.wins === 1 ? "" : "s"}
              </span>
            )}
          </div>
          <span className="font-mono text-accent">{e.total_score.toFixed(1)}</span>
        </li>
      ))}
    </ol>
  );
}
