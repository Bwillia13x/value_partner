'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, AlertTriangle, Shield, Zap } from 'lucide-react'
import { TradingInterface } from '../../components/trading/TradingInterface'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'

export default function TradingPage() {
  const [userId] = useState(1) // In real app, get from auth context
  const [paperTradingMode, setPaperTradingMode] = useState(true)

  const handleOrderSubmit = async (order: any) => {
    console.log('Order submitted:', order)
    // In a real app, this would submit to your trading API
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50/30"
    >
      <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-gray-900">
                Trading Terminal
              </h1>
              <p className="text-gray-600 mt-2">
                Execute trades with real-time market data and advanced order types
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">Paper Trading</span>
                <button
                  onClick={() => setPaperTradingMode(!paperTradingMode)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    paperTradingMode ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      paperTradingMode ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
              {paperTradingMode && (
                <div className="flex items-center space-x-2 bg-blue-50 px-3 py-1 rounded-full">
                  <Shield className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-800">
                    Safe Mode Active
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Risk Disclaimer */}
        {!paperTradingMode && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <Card className="border-orange-200 bg-orange-50">
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  <AlertTriangle className="h-5 w-5 text-orange-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-orange-800">Live Trading Mode</h3>
                    <p className="text-sm text-orange-700 mt-1">
                      You are trading with real money. All orders will be executed in live markets. 
                      Please review your orders carefully before submission.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Market Status Bar */}
        <div className="mb-6">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-6">
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-medium">Market Open</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">S&P 500:</span> 4,145.58 
                    <span className="ml-2 text-green-600">+0.75%</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">NASDAQ:</span> 12,834.87 
                    <span className="ml-2 text-red-600">-0.23%</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">DOW:</span> 33,482.94 
                    <span className="ml-2 text-green-600">+0.42%</span>
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  Last updated: {new Date().toLocaleTimeString()}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trading Interface */}
        <TradingInterface
          userId={userId}
          onOrderSubmit={handleOrderSubmit}
          paperTrading={paperTradingMode}
        />

        {/* Features Section */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Zap className="h-5 w-5 mr-2 text-blue-600" />
                Fast Execution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Lightning-fast order execution with sub-second response times and real-time market data feeds.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Shield className="h-5 w-5 mr-2 text-green-600" />
                Risk Management
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Advanced risk controls including position limits, stop-loss orders, and portfolio-level risk monitoring.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <TrendingUp className="h-5 w-5 mr-2 text-purple-600" />
                Advanced Analytics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Comprehensive market analysis tools, technical indicators, and AI-powered trading insights.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  )
} 