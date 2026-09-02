import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";

export function useApi<T>(path: string | null, pollMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true); setError("");
    try { setData(await api.get<T>(path)); } catch (e) { setError(e instanceof Error ? e.message : "Unable to load data"); } finally { setLoading(false); }
  }, [path]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!path || pollMs <= 0) return;
    const timer = window.setInterval(() => { void load(); }, pollMs);
    return () => window.clearInterval(timer);
  }, [load, path, pollMs]);
  return { data, loading, error, refresh: load };
}
