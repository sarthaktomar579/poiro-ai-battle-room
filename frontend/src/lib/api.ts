import type {
  AuthResponse,
  RoomState,
  RoomSummary,
  Round,
  Submission,
} from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("poiro:token");
}

async function request<T>(
  path: string,
  opts: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  if (opts.auth !== false) {
    const t = getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...opts, headers });
  } catch (e) {
    throw new ApiError(
      "Cannot reach the backend. Is the FastAPI server running?",
      0,
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail || detail;
    } catch {}
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

export const api = {
  signup: (body: { email: string; password: string; display_name: string }) =>
    request<AuthResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(body),
      auth: false,
    }),
  login: (body: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
      auth: false,
    }),
  me: () => request<AuthResponse["user"]>("/auth/me"),
  myRooms: () => request<RoomSummary[]>("/rooms/mine"),
  createRoom: (body: { name: string; prompt: string }) =>
    request<RoomState>("/rooms", { method: "POST", body: JSON.stringify(body) }),
  joinRoom: (code: string) =>
    request<RoomState>("/rooms/join", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  roomByCode: (code: string) =>
    request<RoomState>(`/rooms/by-code/${encodeURIComponent(code)}`),
  endRoom: (roomId: string) =>
    request<RoomState>(`/rooms/${roomId}/end`, { method: "POST" }),
  startRound: (roomId: string, prompt?: string) =>
    request<Round>(`/rooms/${roomId}/rounds`, {
      method: "POST",
      body: JSON.stringify({ prompt: prompt ?? null }),
    }),
  submit: (roomId: string, roundId: string, prompt: string) =>
    request<Submission>(`/rooms/${roomId}/rounds/${roundId}/submissions`, {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
  score: (
    roomId: string,
    roundId: string,
    body: { submission_id: string; value: number; note?: string | null },
  ) =>
    request<Round>(`/rooms/${roomId}/rounds/${roundId}/score`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  pickWinner: (roomId: string, roundId: string, submissionId: string) =>
    request<RoomState>(`/rooms/${roomId}/rounds/${roundId}/winner`, {
      method: "POST",
      body: JSON.stringify({ submission_id: submissionId }),
    }),
};

export const config = { API_URL };
