"use client";
import { useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import Loader from "@/components/Loader";
import { getFactors } from "@/lib/api";

export default function FactorsPage() {
  const [columns, setColumns] = useState<string[]>([]);
  const [rows, setRows] = useState<string[][]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const data = await getFactors(200);
        setColumns(data.columns);
        setRows(data.rows);
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
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Factor Dataset</h1>
      {loading && <Loader />}
      {error && <p className="text-red-600 dark:text-red-400">{error}</p>}
      {!loading && !error && rows.length > 0 && (
        <DataTable columns={columns} rows={rows} />
      )}
    </div>
  );
}
