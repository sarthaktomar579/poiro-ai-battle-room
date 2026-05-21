"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import type { RoomSummary } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const { user, token, hydrate, clear } = useAuthStore();
  const [rooms, setRooms] = useState<RoomSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState(
    "Create the most insane luxury cyberpunk perfume campaign for Gen-Z.",
  );
  const [joinCode, setJoinCode] = useState("");
  const [creating, setCreating] = useState(false);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (token === null) {
      // wait for hydrate; if still null after a tick, redirect
      const t = setTimeout(() => {
        if (!useAuthStore.getState().token) router.replace("/");
      }, 50);
      return () => clearTimeout(t);
    }
  }, [token, router]);

  useEffect(() => {
    if (!token) return;
    let alive = true;
    (async () => {
      try {
        const list = await api.myRooms();
        if (alive) setRooms(list);
      } catch (e) {
        if (alive) setError(e instanceof ApiError ? e.message : "Failed to load rooms");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [token]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const state = await api.createRoom({ name: name.trim() || "Untitled Battle", prompt });
      router.push(`/room/${state.room.code}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create room");
    } finally {
      setCreating(false);
    }
  };

  const onJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!joinCode.trim()) return;
    setJoining(true);
    setError(null);
    try {
      const state = await api.joinRoom(joinCode.trim().toUpperCase());
      router.push(`/room/${state.room.code}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to join room");
    } finally {
      setJoining(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-10 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="chip text-accent border-accent/40">
            <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulseDot" />
            Battle Room Console
          </div>
          <h1 className="mt-3 font-display text-3xl font-bold tracking-tight">
            Welcome back, {user?.display_name ?? "operator"}.
          </h1>
          <p className="text-white/60">
            Start a new battle or jump back into an existing room.
          </p>
        </div>
        <button
          className="btn-ghost"
          onClick={() => {
            clear();
            router.replace("/");
          }}
        >
          Sign out
        </button>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel p-6">
          <h2 className="font-display text-lg font-semibold">Host a new battle</h2>
          <p className="mb-4 text-sm text-white/60">
            You become the host. Hosts set the brief and judge submissions.
          </p>
          <form onSubmit={onCreate} className="space-y-3">
            <div>
              <label className="label mb-1">Room name</label>
              <input
                className="input"
                placeholder="Cyberpunk Perfume Wars"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={120}
              />
            </div>
            <div>
              <label className="label mb-1">Creative brief</label>
              <textarea
                className="input min-h-[110px] resize-y"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                maxLength={2000}
              />
            </div>
            <button className="btn-primary" disabled={creating}>
              {creating ? "Creating..." : "Create battle room"}
            </button>
          </form>
        </section>

        <section className="panel p-6">
          <h2 className="font-display text-lg font-semibold">Join a room</h2>
          <p className="mb-4 text-sm text-white/60">
            Got a room code from a host? Drop it here.
          </p>
          <form onSubmit={onJoin} className="space-y-3">
            <div>
              <label className="label mb-1">Room code</label>
              <input
                className="input uppercase tracking-[0.3em]"
                placeholder="A4B7Q2"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                maxLength={8}
              />
            </div>
            <button className="btn-ghost" disabled={joining}>
              {joining ? "Joining..." : "Join room"}
            </button>
          </form>
        </section>
      </div>

      {error && (
        <div className="mt-6 rounded-xl border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <section className="mt-10">
        <h2 className="mb-3 font-display text-lg font-semibold">Your rooms</h2>
        {loading ? (
          <div className="text-white/50">Loading...</div>
        ) : rooms.length === 0 ? (
          <div className="panel p-8 text-center text-white/50">
            No rooms yet. Create one above to start the battle.
          </div>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {rooms.map((r) => (
              <li key={r.id} className="panel p-4 hover:border-accent/60">
                <button
                  className="flex w-full items-start justify-between text-left"
                  onClick={() => router.push(`/room/${r.code}`)}
                >
                  <div>
                    <div className="font-semibold">{r.name}</div>
                    <div className="text-xs text-white/50">
                      {new Date(r.created_at).toLocaleString()} · code{" "}
                      <span className="font-mono text-accent">{r.code}</span>
                    </div>
                  </div>
                  <span className="chip text-[10px]">{r.status}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
