import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Role, Tokens, User } from "../types";

interface AuthContextValue {
  user: User | null;
  login(email: string, password: string): Promise<User>;
  register(fullName: string, email: string, password: string, role: Role): Promise<User>;
  logout(): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem("seatsync.user");
    return raw ? JSON.parse(raw) as User : null;
  });
  const remember = (tokens: Tokens) => {
    localStorage.setItem("seatsync.access", tokens.access_token);
    localStorage.setItem("seatsync.refresh", tokens.refresh_token);
    localStorage.setItem("seatsync.user", JSON.stringify(tokens.user));
    setUser(tokens.user);
    return tokens.user;
  };
  const value = useMemo<AuthContextValue>(() => ({
    user,
    async login(email, password) {
      return remember((await api.post<Tokens>("/auth/login", { email, password })).data);
    },
    async register(fullName, email, password, role) {
      await api.post("/auth/register", { full_name: fullName, email, password, role });
      return remember((await api.post<Tokens>("/auth/login", { email, password })).data);
    },
    logout() {
      ["seatsync.access", "seatsync.refresh", "seatsync.user"].forEach((key) => localStorage.removeItem(key));
      setUser(null);
    }
  }), [user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be inside AuthProvider");
  return value;
}
