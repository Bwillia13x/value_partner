const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getPlugins(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/plugins`);
  if (!res.ok) {
    throw new Error("Failed to fetch plugins");
  }
  const data = await res.json();
  return data.available_plugins as string[];
}

export async function copilotQuery(question: string): Promise<string[]> {
  const res = await fetch(`${API_BASE}/copilot/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    throw new Error("Copilot unavailable");
  }
  const data = await res.json();
  return data.answers as string[];
}

export async function getFactors(limit = 200): Promise<{columns: string[]; rows: string[][]}> {
  const res = await fetch(`${API_BASE}/data/factors?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to load factors");
  return res.json();
}

export async function getBacktest(): Promise<{date: string; cumulative_returns: number}[]> {
  const res = await fetch(`${API_BASE}/data/backtest`);
  if (!res.ok) throw new Error("Failed to load backtest data");
  return res.json();
}

export async function runPlugin(plugin: string, payload: unknown): Promise<unknown> {
  const res = await fetch(`${API_BASE}/plugins/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plugin, payload }),
  });
  if (!res.ok) {
    throw new Error("Plugin invocation failed");
  }
  const data = await res.json();
  return data.result;
}
