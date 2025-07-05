"use client";
import { useEffect, useState } from "react";
import Loader from "@/components/Loader";
import { getBacktest } from "@/lib/api";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  TimeScale,
} from "chart.js";
import { Line } from "react-chartjs-2";
import type { ChartData } from "chart.js";
import "chartjs-adapter-date-fns";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  TimeScale
);

interface Record {
  date: string;
  cumulative_returns: number;
}

export default function BacktestPage() {
  const [data, setData] = useState<Record[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const records = await getBacktest();
        setData(records);
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

  const chartData: ChartData<"line"> = {
    labels: data.map((d) => d.date),
    datasets: [
      {
        label: "Cumulative Returns",
        data: data.map((d) => d.cumulative_returns),
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.2)",
        tension: 0.2,
      },
    ],
  } as const;

  const options = {
    responsive: true,
    scales: {
      x: {
        type: "time" as const,
        time: { unit: "month" as const },
        title: { display: true, text: "Date" },
      },
      y: {
        beginAtZero: false,
        title: { display: true, text: "Cumulative Return" },
      },
    },
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Backtest Cumulative Returns</h1>
      {loading && <Loader />}
      {error && <p className="text-red-600 dark:text-red-400">{error}</p>}
      {!loading && !error && data.length > 0 && (
        <Line data={chartData} options={options} />
      )}
    </div>
  );
}
