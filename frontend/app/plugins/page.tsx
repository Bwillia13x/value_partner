"use client";
import { useEffect, useState } from "react";
import Loader from "@/components/Loader";
import { getPlugins, runPlugin } from "@/lib/api";

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [result, setResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPlugins() {
      setLoading(true);
      try {
        const list = await getPlugins();
        setPlugins(list);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(String(err));
        }
      } finally {
        setLoading(false);
      }
    }
    fetchPlugins();
  }, []);

  async function handleRun() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await runPlugin(selected, {});
      setResult(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Plugin Marketplace</h1>
      {loading && <Loader />}
      {error && <p className="text-red-600 dark:text-red-400">{error}</p>}
      {!loading && plugins.length > 0 && (
        <div className="space-y-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Choose a plugin
            <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="border rounded px-3 py-2 dark:bg-gray-800 dark:border-gray-700"
          >
            <option value="">-- Select a plugin --</option>
            {plugins.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          </label>
          <button
            disabled={!selected}
            onClick={handleRun}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            Run Plugin
          </button>
        </div>
      )}
      {result !== null && (
        // Display JSON or primitive result

        <pre className="whitespace-pre-wrap bg-gray-100 dark:bg-gray-800 dark:text-gray-100 p-4 rounded">
          {typeof result === "string"
            ? result
            : JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
