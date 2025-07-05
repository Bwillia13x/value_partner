"use client";
import { useEffect, useState } from "react";
import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  TooltipItem,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

interface AssetAllocationData {
  allocation: { [key: string]: number };
  total_value: number;
}

interface AssetAllocationChartProps {
  userId: number;
  height?: number;
}

export default function AssetAllocationChart({ userId, height = 400 }: AssetAllocationChartProps) {
  const [data, setData] = useState<AssetAllocationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/analytics/allocation/${userId}`);
        
        if (!response.ok) {
          throw new Error("Failed to fetch allocation data");
        }
        
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">Error loading allocation data: {error}</p>
      </div>
    );
  }

  if (!data || Object.keys(data.allocation).length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <p className="text-gray-600">No allocation data available</p>
      </div>
    );
  }

  const colors = [
    "#3B82F6", // Blue
    "#10B981", // Green
    "#F59E0B", // Yellow
    "#EF4444", // Red
    "#8B5CF6", // Purple
    "#06B6D4", // Cyan
    "#F97316", // Orange
    "#84CC16", // Lime
    "#EC4899", // Pink
    "#6B7280", // Gray
  ];

  const chartData = {
    labels: Object.keys(data.allocation).map(key => 
      key.charAt(0).toUpperCase() + key.slice(1)
    ),
    datasets: [
      {
        data: Object.values(data.allocation).map(value => value * 100),
        backgroundColor: colors.slice(0, Object.keys(data.allocation).length),
        borderColor: colors.slice(0, Object.keys(data.allocation).length),
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "right" as const,
      },
      title: {
        display: true,
        text: "Asset Allocation",
      },
      tooltip: {
        callbacks: {
          label: function(context: TooltipItem<'pie'>) {
            return `${context.label}: ${context.parsed.toFixed(1)}%`;
          },
        },
      },
    },
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Asset Allocation</h3>
        <p className="text-sm text-gray-600">
          Total Portfolio Value: ${data.total_value.toLocaleString()}
        </p>
      </div>
      <div style={{ height: `${height}px` }}>
        <Pie data={chartData} options={options} />
      </div>
    </div>
  );
}