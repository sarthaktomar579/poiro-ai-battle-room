import { create } from "zustand";
import type { User } from "@/lib/types";

interface AuthState {
  token: string | null;
  user: User | null;
  hydrate: () => void;
  setSession: (token: string, user: User) => void;
  clear: () => void;
}

const TOKEN_KEY = "poiro:token";
const USER_KEY = "poiro:user";

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  hydrate: () => {
    if (typeof window === "undefined") return;
    const token = window.localStorage.getItem(TOKEN_KEY);
    const rawUser = window.localStorage.getItem(USER_KEY);
    let user: User | null = null;
    try {
      user = rawUser ? (JSON.parse(rawUser) as User) : null;
    } catch {
      user = null;
    }
    set({ token, user });
  },
  setSession: (token, user) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(TOKEN_KEY, token);
      window.localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
    set({ token, user });
  },
  clear: () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(TOKEN_KEY);
      window.localStorage.removeItem(USER_KEY);
    }
    set({ token: null, user: null });
  },
}));
