"use client";
import { useEffect, useState } from "react";

interface PerformanceMetricsData {
  total_return: number;
  annualized_return: number;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  current_value: number;
  benchmark_return: number;
  alpha: number;
  beta: number;
}

interface PerformanceMetricsProps {
  userId: number;
  periodDays?: number;
}

export default function PerformanceMetrics({ userId, periodDays = 365 }: PerformanceMetricsProps) {
  const [data, setData] = useState<PerformanceMetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/analytics/performance/${userId}?period_days=${periodDays}`);
        
        if (!response.ok) {
          throw new Error("Failed to fetch performance metrics");
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
  }, [userId, periodDays]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-300 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">Error loading performance metrics: {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <p className="text-gray-600">No performance metrics available</p>
      </div>
    );
  }

  const formatPercentage = (value: number) => {
    return (value * 100).toFixed(2) + "%";
  };

  const formatCurrency = (value: number) => {
    return "$" + value.toLocaleString();
  };

  const formatNumber = (value: number) => {
    return value.toFixed(2);
  };

  const metrics = [
    {
      label: "Current Value",
      value: formatCurrency(data.current_value),
      color: "text-blue-600",
    },
    {
      label: "Total Return",
      value: formatPercentage(data.total_return),
      color: data.total_return >= 0 ? "text-green-600" : "text-red-600",
    },
    {
      label: "Annualized Return",
      value: formatPercentage(data.annualized_return),
      color: data.annualized_return >= 0 ? "text-green-600" : "text-red-600",
    },
    {
      label: "Volatility",
      value: formatPercentage(data.volatility),
      color: "text-gray-600",
    },
    {
      label: "Sharpe Ratio",
      value: formatNumber(data.sharpe_ratio),
      color: data.sharpe_ratio >= 1 ? "text-green-600" : "text-yellow-600",
    },
    {
      label: "Max Drawdown",
      value: formatPercentage(data.max_drawdown),
      color: "text-red-600",
    },
    {
      label: "Benchmark Return",
      value: formatPercentage(data.benchmark_return),
      color: data.benchmark_return >= 0 ? "text-green-600" : "text-red-600",
    },
    {
      label: "Alpha",
      value: formatPercentage(data.alpha),
      color: data.alpha >= 0 ? "text-green-600" : "text-red-600",
    },
    {
      label: "Beta",
      value: formatNumber(data.beta),
      color: "text-gray-600",
    },
  ];

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Performance Metrics</h3>
        <p className="text-sm text-gray-600">
          Analysis period: {periodDays} days
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {metrics.map((metric, index) => (
          <div key={index} className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">{metric.label}</div>
            <div className={`text-lg font-semibold ${metric.color}`}>
              {metric.value}
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          <p>• Benchmark: S&P 500 (SPY)</p>
          <p>• Alpha: Excess return over benchmark (risk-adjusted)</p>
          <p>• Beta: Sensitivity to market movements</p>
          <p>• Sharpe Ratio: Risk-adjusted return (higher is better)</p>
        </div>
      </div>
    </div>
  );
}