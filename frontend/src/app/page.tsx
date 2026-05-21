"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";

type Mode = "login" | "signup";

export default function LandingPage() {
  const router = useRouter();
  const { token, hydrate, setSession } = useAuthStore();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (token) router.replace("/dashboard");
  }, [token, router]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp =
        mode === "login"
          ? await api.login({ email, password })
          : await api.signup({ email, password, display_name: displayName.trim() || email.split("@")[0] });
      setSession(resp.access_token, resp.user);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = () => {
    setMode("login");
    setEmail("host@poiro.ai");
    setPassword("battleroom");
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6 py-10">
      <div className="grid w-full grid-cols-1 gap-10 md:grid-cols-2 md:items-center">
        <section className="space-y-6">
          <div className="chip text-accent border-accent/40">
            <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulseDot" />
            Poiro Labs · AI Battle Room
          </div>
          <h1 className="font-display text-5xl font-bold leading-tight tracking-tight md:text-6xl">
            Run a live <span className="text-accent">creative battle</span>.
            <br />
            Watch ideas race in real time.
          </h1>
          <p className="max-w-md text-white/70">
            One host. A creative brief. Contestants submit prompts. The system
            spawns async generation jobs, streams every state change over
            WebSockets, and lets the host crown a winner.
          </p>

          <div className="grid grid-cols-3 gap-3 text-xs text-white/60">
            <Feature label="Realtime" detail="WebSocket-driven room state" />
            <Feature label="Async jobs" detail="Queued / running / failed" />
            <Feature label="Persistent" detail="Refresh-safe rooms & scores" />
          </div>
        </section>

        <section className="panel p-7">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold">
              {mode === "login" ? "Sign in" : "Create an identity"}
            </h2>
            <div className="flex gap-1 rounded-full border border-edge p-1 text-xs">
              <button
                type="button"
                onClick={() => setMode("login")}
                className={`rounded-full px-3 py-1 ${mode === "login" ? "bg-accent text-ink" : "text-muted"}`}
              >
                Sign in
              </button>
              <button
                type="button"
                onClick={() => setMode("signup")}
                className={`rounded-full px-3 py-1 ${mode === "signup" ? "bg-accent text-ink" : "text-muted"}`}
              >
                Sign up
              </button>
            </div>
          </div>

          <form onSubmit={onSubmit} className="space-y-3">
            <div>
              <label className="label mb-1">Email</label>
              <input
                className="input"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            {mode === "signup" && (
              <div>
                <label className="label mb-1">Display name</label>
                <input
                  className="input"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="What should the room call you?"
                />
              </div>
            )}

            <div>
              <label className="label mb-1">Password</label>
              <input
                className="input"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>

            {error && (
              <div className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
                {error}
              </div>
            )}

            <button className="btn-primary w-full" disabled={loading}>
              {loading
                ? "Working..."
                : mode === "login"
                  ? "Enter the room"
                  : "Create account"}
            </button>
          </form>

          <div className="mt-5 flex items-center justify-between text-xs text-muted">
            <span>Demo accounts seeded for reviewers</span>
            <button onClick={fillDemo} className="text-accent hover:underline">
              Use demo host
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}

function Feature({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="panel px-3 py-2">
      <div className="text-[11px] uppercase tracking-wider text-accent">
        {label}
      </div>
      <div className="text-white/80">{detail}</div>
    </div>
  );
}
