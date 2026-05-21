import type { WSEvent } from "./types";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, "") || "ws://localhost:8000";

export type WSHandler = (event: WSEvent) => void;

export interface RoomSocketOptions {
  roomId: string;
  token: string;
  onEvent: WSHandler;
  onStatus?: (status: "connecting" | "open" | "closed" | "error") => void;
}

/** Lightweight reconnecting websocket client for a single room. */
export class RoomSocket {
  private ws: WebSocket | null = null;
  private opts: RoomSocketOptions;
  private closed = false;
  private retry = 0;
  private pingTimer: ReturnType<typeof setInterval> | null = null;

  constructor(opts: RoomSocketOptions) {
    this.opts = opts;
  }

  start() {
    this.closed = false;
    this.connect();
  }

  stop() {
    this.closed = true;
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    if (this.ws) {
      try {
        this.ws.close();
      } catch {}
      this.ws = null;
    }
  }

  private connect() {
    if (this.closed) return;
    this.opts.onStatus?.("connecting");
    const url = `${WS_URL}/ws/rooms/${this.opts.roomId}?token=${encodeURIComponent(this.opts.token)}`;
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => {
      this.retry = 0;
      this.opts.onStatus?.("open");
      if (this.pingTimer) clearInterval(this.pingTimer);
      this.pingTimer = setInterval(() => {
        try {
          ws.send("ping");
        } catch {}
      }, 20000);
    };

    ws.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data) as WSEvent;
        this.opts.onEvent(ev);
      } catch {}
    };

    ws.onerror = () => {
      this.opts.onStatus?.("error");
    };

    ws.onclose = () => {
      this.opts.onStatus?.("closed");
      if (this.pingTimer) {
        clearInterval(this.pingTimer);
        this.pingTimer = null;
      }
      if (this.closed) return;
      // Exponential backoff with jitter, capped at 8s.
      const delay = Math.min(8000, 500 * 2 ** this.retry) + Math.random() * 300;
      this.retry += 1;
      setTimeout(() => this.connect(), delay);
    };
  }
}
