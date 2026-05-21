// Shared types mirroring the FastAPI schemas. Kept manually in sync; small
// surface so the dev cost is low.

export type RoomStatus = "lobby" | "in_round" | "scoring" | "ended";
export type RoundStatus = "open" | "generating" | "scoring" | "completed";
export type JobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "timed_out";
export type ParticipantRole = "host" | "participant";

export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface RoomSummary {
  id: string;
  code: string;
  name: string;
  prompt: string;
  status: RoomStatus;
  host_id: string;
  current_round_id: string | null;
  created_at: string;
}

export interface Participant {
  id: string;
  user_id: string;
  role: ParticipantRole;
  is_active: boolean;
  joined_at: string;
  display_name: string;
  email: string;
}

export interface Job {
  id: string;
  status: JobStatus;
  attempt: number;
  provider: string;
  output: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Score {
  id: string;
  value: number;
  note: string | null;
  scored_by_user_id: string;
  created_at: string;
}

export interface Submission {
  id: string;
  round_id: string;
  user_id: string;
  display_name: string;
  prompt: string;
  created_at: string;
  latest_job: Job | null;
  score: Score | null;
}

export interface Round {
  id: string;
  room_id: string;
  round_number: number;
  prompt: string;
  status: RoundStatus;
  winner_submission_id: string | null;
  started_at: string;
  ended_at: string | null;
  submissions: Submission[];
}

export interface LeaderboardEntry {
  user_id: string;
  display_name: string;
  total_score: number;
  wins: number;
}

export interface RoomState {
  room: RoomSummary;
  role: ParticipantRole;
  participants: Participant[];
  current_round: Round | null;
  past_rounds: Round[];
  leaderboard: LeaderboardEntry[];
}

export interface WSEvent<T = Record<string, unknown>> {
  type: string;
  payload: T;
  ts: string;
}
