"use client";
import { useEffect, useState } from "react";

interface RiskMetricsData {
  value_at_risk: {
    var_95: number;
    var_99: number;
    expected_shortfall_95: number;
    expected_shortfall_99: number;
  };
  distribution_metrics: {
    skewness: number;
    kurtosis: number;
  };
  period_days: number;
}

interface RiskMetricsProps {
  userId: number;
  periodDays?: number;
}

export default function RiskMetrics({ userId, periodDays = 365 }: RiskMetricsProps) {
  const [data, setData] = useState<RiskMetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/analytics/risk-metrics/${userId}?period_days=${periodDays}`);
        
        if (!response.ok) {
          throw new Error("Failed to fetch risk metrics");
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
            {[...Array(4)].map((_, i) => (
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
        <p className="text-red-700">Error loading risk metrics: {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <p className="text-gray-600">No risk metrics available</p>
      </div>
    );
  }

  const formatPercentage = (value: number) => {
    return (value * 100).toFixed(2) + "%";
  };

  const formatNumber = (value: number) => {
    return value.toFixed(3);
  };

  const getRiskLevel = (var95: number) => {
    const absVar = Math.abs(var95);
    if (absVar < 0.01) return { level: "Low", color: "text-green-600" };
    if (absVar < 0.03) return { level: "Medium", color: "text-yellow-600" };
    return { level: "High", color: "text-red-600" };
  };

  const riskLevel = getRiskLevel(data.value_at_risk.var_95);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Risk Analysis</h3>
        <p className="text-sm text-gray-600">
          Analysis period: {data.period_days} days
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Value at Risk */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-3">Value at Risk (VaR)</h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">95% VaR (1 day):</span>
              <span className="font-medium text-red-600">
                {formatPercentage(data.value_at_risk.var_95)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">99% VaR (1 day):</span>
              <span className="font-medium text-red-600">
                {formatPercentage(data.value_at_risk.var_99)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Expected Shortfall (95%):</span>
              <span className="font-medium text-red-600">
                {formatPercentage(data.value_at_risk.expected_shortfall_95)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Expected Shortfall (99%):</span>
              <span className="font-medium text-red-600">
                {formatPercentage(data.value_at_risk.expected_shortfall_99)}
              </span>
            </div>
          </div>
        </div>

        {/* Distribution Metrics */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-3">Distribution Metrics</h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Skewness:</span>
              <span className="font-medium text-gray-900">
                {formatNumber(data.distribution_metrics.skewness)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Kurtosis:</span>
              <span className="font-medium text-gray-900">
                {formatNumber(data.distribution_metrics.kurtosis)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Assessment */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Overall Risk Level:</span>
          <span className={`font-semibold ${riskLevel.color}`}>
            {riskLevel.level}
          </span>
        </div>
      </div>
      
      <div className="mt-4 text-xs text-gray-500">
        <p>• VaR: Maximum expected loss at given confidence level</p>
        <p>• Expected Shortfall: Average loss when VaR is exceeded</p>
        <p>• Skewness: Asymmetry of return distribution (negative = left tail)</p>
        <p>• Kurtosis: Tail heaviness (higher = more extreme events)</p>
      </div>
    </div>
  );
}