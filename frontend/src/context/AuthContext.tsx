import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore } from "../lib/api";
import type { User } from "../types";

interface AuthValue { user: User | null; loading: boolean; login: (id: string, password: string) => Promise<void>; logout: () => void }
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!tokenStore.get()) { setLoading(false); return; }
    api.get<User>("/users/me").then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);
  async function login(id: string, password: string) {
    const response = await api.login(id, password);
    tokenStore.set(response.access_token);
    try { setUser(await api.get<User>("/users/me")); } catch (error) { tokenStore.clear(); throw error; }
  }
  function logout() { tokenStore.clear(); setUser(null); }
  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used within AuthProvider"); return value; }
