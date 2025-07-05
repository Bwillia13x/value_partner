"use client";
import { useState } from "react";
import PerformanceChart from "../../components/PerformanceChart";
import AssetAllocationChart from "../../components/AssetAllocationChart";
import PerformanceMetrics from "../../components/PerformanceMetrics";
import RiskMetrics from "../../components/RiskMetrics";

export default function AnalyticsPage() {
  const [selectedPeriod, setSelectedPeriod] = useState(365);
  // For demo purposes, using user ID 1. In production, this would come from auth
  const userId = 1;

  const periods = [
    { value: 30, label: "1 Month" },
    { value: 90, label: "3 Months" },
    { value: 180, label: "6 Months" },
    { value: 365, label: "1 Year" },
    { value: 730, label: "2 Years" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Portfolio Analytics</h1>
          <p className="mt-2 text-gray-600">
            Comprehensive analysis of your investment performance and risk metrics
          </p>
        </div>

        {/* Period Selector */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            {periods.map((period) => (
              <button
                key={period.value}
                onClick={() => setSelectedPeriod(period.value)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedPeriod === period.value
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-700 hover:bg-gray-50 border border-gray-300"
                }`}
              >
                {period.label}
              </button>
            ))}
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="mb-8">
          <PerformanceMetrics userId={userId} periodDays={selectedPeriod} />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Performance Chart */}
          <div className="lg:col-span-2">
            <PerformanceChart userId={userId} periodDays={selectedPeriod} height={400} />
          </div>
          
          {/* Asset Allocation */}
          <AssetAllocationChart userId={userId} height={350} />
          
          {/* Risk Metrics */}
          <RiskMetrics userId={userId} periodDays={selectedPeriod} />
        </div>

        {/* Additional Analytics Sections */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Performance Attribution */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Contributors</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">AAPL</span>
                <span className="text-sm font-medium text-green-600">+2.3%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">MSFT</span>
                <span className="text-sm font-medium text-green-600">+1.8%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">GOOGL</span>
                <span className="text-sm font-medium text-green-600">+1.2%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">TSLA</span>
                <span className="text-sm font-medium text-red-600">-0.8%</span>
              </div>
            </div>
          </div>

          {/* Benchmark Comparison */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Benchmark Comparison</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Your Portfolio</span>
                <span className="text-sm font-medium text-blue-600">+12.5%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">S&P 500</span>
                <span className="text-sm font-medium text-gray-600">+10.2%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Outperformance</span>
                <span className="text-sm font-medium text-green-600">+2.3%</span>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <div>
                  <div className="text-sm font-medium text-gray-900">Portfolio Sync</div>
                  <div className="text-xs text-gray-500">2 hours ago</div>
                </div>
                <div className="text-green-600">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <div>
                  <div className="text-sm font-medium text-gray-900">Rebalance Alert</div>
                  <div className="text-xs text-gray-500">1 day ago</div>
                </div>
                <div className="text-yellow-600">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}