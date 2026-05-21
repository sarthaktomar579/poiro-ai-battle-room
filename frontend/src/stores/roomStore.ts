import { create } from "zustand";
import type {
  Job,
  RoomState,
  Round,
  Submission,
  WSEvent,
} from "@/lib/types";

interface State {
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  wsStatus: "connecting" | "open" | "closed" | "error";
  state: RoomState | null;
  recentEvents: WSEvent[];
  setState: (s: RoomState) => void;
  reset: () => void;
  setError: (msg: string) => void;
  setLoading: () => void;
  setWsStatus: (s: State["wsStatus"]) => void;
  applyEvent: (e: WSEvent) => void;
}

/** Pure reducers, exported so they can be unit-tested if we add tests later. */
const reducers = {
  upsertSubmission(round: Round, sub: Submission): Round {
    const idx = round.submissions.findIndex((s) => s.id === sub.id);
    const submissions = [...round.submissions];
    if (idx >= 0) {
      submissions[idx] = { ...submissions[idx], ...sub };
    } else {
      submissions.push(sub);
    }
    return { ...round, submissions };
  },
  patchJob(round: Round, submissionId: string, patch: Partial<Job>): Round {
    const submissions = round.submissions.map((s) => {
      if (s.id !== submissionId) return s;
      const baseJob: Job = s.latest_job ?? {
        id: patch.id ?? "tmp",
        status: "queued",
        attempt: patch.attempt ?? 1,
        provider: patch.provider ?? "mock",
        output: null,
        error: null,
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: null,
      };
      return { ...s, latest_job: { ...baseJob, ...patch } };
    });
    return { ...round, submissions };
  },
};

export const useRoomStore = create<State>((set, get) => ({
  status: "idle",
  error: null,
  wsStatus: "closed",
  state: null,
  recentEvents: [],
  setLoading: () => set({ status: "loading", error: null }),
  setError: (msg) => set({ status: "error", error: msg }),
  setWsStatus: (s) => set({ wsStatus: s }),
  setState: (s) => set({ state: s, status: "ready", error: null }),
  reset: () =>
    set({
      status: "idle",
      error: null,
      wsStatus: "closed",
      state: null,
      recentEvents: [],
    }),
  applyEvent: (e) => {
    const prev = get().state;
    const recent = [e, ...get().recentEvents].slice(0, 25);

    if (!prev) {
      if (e.type === "room.snapshot") {
        set({ state: e.payload as unknown as RoomState, status: "ready", recentEvents: recent });
      } else {
        set({ recentEvents: recent });
      }
      return;
    }

    let next: RoomState = prev;

    switch (e.type) {
      case "room.snapshot":
        next = e.payload as unknown as RoomState;
        break;

      case "room.participant_joined": {
        const p = e.payload as {
          user_id: string;
          display_name: string;
          role: "host" | "participant";
        };
        if (prev.participants.some((x) => x.user_id === p.user_id)) break;
        next = {
          ...prev,
          participants: [
            ...prev.participants,
            {
              id: `tmp-${p.user_id}`,
              user_id: p.user_id,
              role: p.role,
              is_active: true,
              joined_at: e.ts,
              display_name: p.display_name,
              email: "",
            },
          ],
        };
        break;
      }

      case "room.state_changed": {
        const p = e.payload as { status?: RoomState["room"]["status"] };
        if (p.status) {
          next = { ...prev, room: { ...prev.room, status: p.status } };
        }
        break;
      }

      case "round.started": {
        const p = e.payload as {
          round_id: string;
          round_number: number;
          prompt: string;
          room_status?: RoomState["room"]["status"];
        };
        const newRound: Round = {
          id: p.round_id,
          room_id: prev.room.id,
          round_number: p.round_number,
          prompt: p.prompt,
          status: "open",
          winner_submission_id: null,
          started_at: e.ts,
          ended_at: null,
          submissions: [],
        };
        next = {
          ...prev,
          current_round: newRound,
          past_rounds: prev.current_round
            ? [prev.current_round, ...prev.past_rounds]
            : prev.past_rounds,
          room: {
            ...prev.room,
            status: p.room_status ?? "in_round",
            current_round_id: p.round_id,
          },
        };
        break;
      }

      case "round.submission_created": {
        const p = e.payload as {
          submission_id: string;
          round_id: string;
          user_id: string;
          display_name: string;
          prompt?: string;
        };
        if (!prev.current_round || prev.current_round.id !== p.round_id) break;
        const sub: Submission = {
          id: p.submission_id,
          round_id: p.round_id,
          user_id: p.user_id,
          display_name: p.display_name,
          prompt: p.prompt ?? "",
          created_at: e.ts,
          latest_job: {
            id: "tmp",
            status: "queued",
            attempt: 1,
            provider: "pending",
            output: null,
            error: null,
            created_at: e.ts,
            started_at: null,
            completed_at: null,
          },
          score: null,
        };
        next = {
          ...prev,
          current_round: reducers.upsertSubmission(prev.current_round, sub),
        };
        break;
      }

      case "job.queued":
      case "job.running":
      case "job.completed":
      case "job.failed":
      case "job.timed_out": {
        const p = e.payload as {
          submission_id: string;
          job_id: string;
          attempt?: number;
          output?: string;
          error?: string;
          provider?: string;
        };
        if (!prev.current_round) break;
        const statusMap: Record<string, Job["status"]> = {
          "job.queued": "queued",
          "job.running": "running",
          "job.completed": "completed",
          "job.failed": "failed",
          "job.timed_out": "timed_out",
        };
        next = {
          ...prev,
          current_round: reducers.patchJob(prev.current_round, p.submission_id, {
            id: p.job_id,
            status: statusMap[e.type],
            attempt: p.attempt ?? 1,
            output: p.output ?? null,
            error: p.error ?? null,
            provider: p.provider ?? "mock",
            completed_at:
              e.type === "job.completed" ||
              e.type === "job.failed" ||
              e.type === "job.timed_out"
                ? e.ts
                : null,
            started_at: e.type === "job.running" ? e.ts : null,
          }),
        };
        break;
      }

      case "round.state_changed": {
        const p = e.payload as { round_id: string; status: Round["status"] };
        if (prev.current_round && prev.current_round.id === p.round_id) {
          next = {
            ...prev,
            current_round: { ...prev.current_round, status: p.status },
            room: {
              ...prev.room,
              status:
                p.status === "scoring"
                  ? "scoring"
                  : p.status === "completed"
                    ? "lobby"
                    : prev.room.status,
            },
          };
        }
        break;
      }

      case "score.recorded": {
        const p = e.payload as {
          submission_id: string;
          value: number;
          round_id: string;
        };
        if (!prev.current_round) break;
        const submissions = prev.current_round.submissions.map((s) =>
          s.id === p.submission_id
            ? {
                ...s,
                score: {
                  id: s.score?.id ?? "tmp",
                  value: p.value,
                  note: s.score?.note ?? null,
                  scored_by_user_id: s.score?.scored_by_user_id ?? "",
                  created_at: e.ts,
                },
              }
            : s,
        );
        next = {
          ...prev,
          current_round: { ...prev.current_round, submissions },
        };
        break;
      }

      case "round.winner_picked": {
        const p = e.payload as { round_id: string; submission_id: string };
        if (prev.current_round && prev.current_round.id === p.round_id) {
          next = {
            ...prev,
            current_round: {
              ...prev.current_round,
              winner_submission_id: p.submission_id,
            },
          };
        }
        break;
      }

      case "round.completed": {
        const p = e.payload as {
          round_id: string;
          room_status?: RoomState["room"]["status"];
        };
        if (prev.current_round && prev.current_round.id === p.round_id) {
          const completed: Round = {
            ...prev.current_round,
            status: "completed",
            ended_at: e.ts,
          };
          next = {
            ...prev,
            current_round: null,
            past_rounds: [completed, ...prev.past_rounds],
            room: {
              ...prev.room,
              status: p.room_status ?? "lobby",
              current_round_id: null,
            },
          };
        }
        break;
      }

      default:
        break;
    }

    set({ state: next, recentEvents: recent });
  },
}));
