'use client'

import React, { useState, useEffect, useMemo, useCallback } from 'react'
import useWebSocket, { ReadyState } from 'react-use-websocket'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  DollarSign,
  PieChart,
  BarChart3,
  AlertTriangle,
  RefreshCcw,
  Wifi,
  WifiOff,
  Settings,
  Filter,
  Download
} from 'lucide-react'
import { cn, formatCurrency, formatPercentage, getPercentageColor } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle, MetricCard } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { PortfolioChart, ChartDataPoint } from '@/components/charts/AdvancedChart'

interface PortfolioData {
  totalValue: number
  totalChange: number
  totalChangePercent: number
  cashBalance: number
  investedAmount: number
  dayChange: number
  dayChangePercent: number
  positions: Position[]
  alerts: Alert[]
  recentTransactions: Transaction[]
  marketStatus: 'open' | 'closed' | 'pre-market' | 'after-hours'
}

interface Position {
  symbol: string
  name: string
  quantity: number
  currentPrice: number
  marketValue: number
  costBasis: number
  unrealizedPL: number
  unrealizedPLPercent: number
  dayChange: number
  dayChangePercent: number
  weight: number
  sector: string
  lastUpdate: string
}

interface Alert {
  id: string
  type: 'price' | 'volume' | 'news' | 'system'
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  message: string
  timestamp: string
  symbol?: string
  actionRequired?: boolean
}

interface Transaction {
  id: string
  type: 'buy' | 'sell' | 'dividend' | 'fee'
  symbol: string
  quantity: number
  price: number
  amount: number
  timestamp: string
  status: 'pending' | 'completed' | 'cancelled'
}

interface MarketOverview {
  indices: {
    name: string
    value: number
    change: number
    changePercent: number
  }[]
  topMovers: {
    gainers: Position[]
    losers: Position[]
  }
  volume: number
  volatility: number
}

interface RealTimeDashboardProps {
  userId: number
  className?: string
  websocketUrl?: string
  refreshInterval?: number
  enableNotifications?: boolean
}

export function RealTimeDashboard({
  userId,
  className,
  websocketUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/portfolio/${userId}`,
  refreshInterval = 5000,
  enableNotifications = true
}: RealTimeDashboardProps) {
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null)
  const [, setMarketOverview] = useState<MarketOverview | null>(null)
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [selectedTimeframe] = useState('1D')
  const [isLoading, setIsLoading] = useState(true)
  const [notifications, setNotifications] = useState<Alert[]>([])
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [selectedView, setSelectedView] = useState<'overview' | 'positions' | 'analytics'>('overview')

  // Define callback functions with useCallback to prevent unnecessary re-renders
  const fetchInitialData = useCallback(async () => {
    try {
      setIsLoading(true)
      const [portfolioResponse, chartResponse] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/portfolio/summary?user_id=${userId}`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/portfolio/chart?user_id=${userId}&timeframe=${selectedTimeframe}`)
      ])

      if (portfolioResponse.ok) {
        const portfolioData = await portfolioResponse.json()
        setPortfolioData(portfolioData)
      }

      if (chartResponse.ok) {
        const chartData = await chartResponse.json()
        setChartData(chartData)
      }
    } catch (error) {
      console.error('Error fetching initial data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [userId, selectedTimeframe])

  const handleNewAlert = useCallback((alert: Alert) => {
    setNotifications(prev => [alert, ...prev.slice(0, 9)]) // Keep only 10 latest
    
    if (enableNotifications && 'Notification' in window) {
      if (Notification.permission === 'granted') {
        new Notification(alert.title, {
          body: alert.message,
          icon: '/favicon.ico',
          tag: alert.id
        })
      } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            new Notification(alert.title, {
              body: alert.message,
              icon: '/favicon.ico',
              tag: alert.id
            })
          }
        })
      }
    }
  }, [enableNotifications])

  const updatePositionPrices = useCallback((priceUpdates: { [symbol: string]: number }) => {
    setPortfolioData(prev => {
      if (!prev) return prev
      
      const updatedPositions = prev.positions.map(position => {
        const newPrice = priceUpdates[position.symbol]
        if (newPrice) {
          const newMarketValue = position.quantity * newPrice
          const newUnrealizedPL = newMarketValue - position.costBasis
          const newUnrealizedPLPercent = (newUnrealizedPL / position.costBasis) * 100
          
          return {
            ...position,
            currentPrice: newPrice,
            marketValue: newMarketValue,
            unrealizedPL: newUnrealizedPL,
            unrealizedPLPercent: newUnrealizedPLPercent,
            lastUpdate: new Date().toISOString()
          }
        }
        return position
      })

      const newTotalValue = updatedPositions.reduce((sum, pos) => sum + pos.marketValue, 0) + prev.cashBalance
      const newTotalChange = newTotalValue - (prev.totalValue - prev.totalChange)
      const newTotalChangePercent = ((newTotalValue - (prev.totalValue - prev.totalChange)) / (prev.totalValue - prev.totalChange)) * 100

      return {
        ...prev,
        positions: updatedPositions,
        totalValue: newTotalValue,
        totalChange: newTotalChange,
        totalChangePercent: newTotalChangePercent
      }
    })
  }, [])

  // WebSocket connection
  const { sendMessage, lastMessage, readyState } = useWebSocket(
    websocketUrl,
    {
      onOpen: () => setConnectionStatus('connected'),
      onClose: () => setConnectionStatus('disconnected'),
      onError: () => setConnectionStatus('disconnected'),
      shouldReconnect: () => true,
      reconnectAttempts: 10,
      reconnectInterval: 3000,
    }
  )

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage?.data) {
      try {
        const data = JSON.parse(lastMessage.data)
        
        switch (data.type) {
          case 'portfolio_update':
            setPortfolioData(data.payload)
            setLastUpdate(new Date())
            break
          case 'market_data':
            setMarketOverview(data.payload)
            break
          case 'chart_data':
            setChartData(data.payload)
            break
          case 'alert':
            handleNewAlert(data.payload)
            break
          case 'price_update':
            updatePositionPrices(data.payload)
            break
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }
  }, [lastMessage, handleNewAlert, updatePositionPrices])

  // Request initial data when connected
  useEffect(() => {
    if (readyState === ReadyState.OPEN) {
      sendMessage(JSON.stringify({
        type: 'subscribe',
        payload: { userId, timeframe: selectedTimeframe }
      }))
    }
  }, [readyState, sendMessage, userId, selectedTimeframe])

  // Fetch initial data
  useEffect(() => {
    fetchInitialData()
  }, [fetchInitialData])

  // Auto-refresh data
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      if (readyState === ReadyState.OPEN) {
        sendMessage(JSON.stringify({
          type: 'refresh',
          payload: { userId }
        }))
      } else {
        fetchInitialData()
      }
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, readyState, sendMessage, userId, refreshInterval, fetchInitialData])


  const connectionStatusColor = useMemo(() => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-500'
      case 'connecting': return 'text-yellow-500'
      case 'disconnected': return 'text-red-500'
      default: return 'text-gray-500'
    }
  }, [connectionStatus])

  const topGainers = useMemo(() => {
    if (!portfolioData) return []
    return portfolioData.positions
      .filter(p => p.dayChangePercent > 0)
      .sort((a, b) => b.dayChangePercent - a.dayChangePercent)
      .slice(0, 3)
  }, [portfolioData])

  const topLosers = useMemo(() => {
    if (!portfolioData) return []
    return portfolioData.positions
      .filter(p => p.dayChangePercent < 0)
      .sort((a, b) => a.dayChangePercent - b.dayChangePercent)
      .slice(0, 3)
  }, [portfolioData])

  const sectorAllocation = useMemo(() => {
    if (!portfolioData) return []
    
    const sectorMap = new Map<string, number>()
    portfolioData.positions.forEach(position => {
      const currentValue = sectorMap.get(position.sector) || 0
      sectorMap.set(position.sector, currentValue + position.marketValue)
    })

    return Array.from(sectorMap.entries()).map(([sector, value]) => ({
      sector,
      value,
      percentage: (value / portfolioData.investedAmount) * 100
    })).sort((a, b) => b.value - a.value)
  }, [portfolioData])

  if (isLoading) {
    return (
      <div className={cn("space-y-6", className)}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-1/2"></div>
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="h-96 bg-gray-100 rounded-lg animate-pulse"></div>
      </div>
    )
  }

  if (!portfolioData) {
    return (
      <div className={cn("flex items-center justify-center h-96", className)}>
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold">Unable to load portfolio data</h3>
          <p className="text-muted-foreground mb-4">Please check your connection and try again</p>
          <Button onClick={fetchInitialData}>
            <RefreshCcw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Portfolio Dashboard</h1>
          <div className="flex items-center space-x-4 mt-2">
            <div className="flex items-center space-x-2">
              {connectionStatus === 'connected' ? (
                <Wifi className={cn("h-4 w-4", connectionStatusColor)} />
              ) : (
                <WifiOff className={cn("h-4 w-4", connectionStatusColor)} />
              )}
              <span className={cn("text-sm", connectionStatusColor)}>
                {connectionStatus === 'connected' ? 'Live' : 'Offline'}
              </span>
            </div>
            <span className="text-sm text-muted-foreground">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </span>
            <div className={cn(
              "px-2 py-1 rounded-full text-xs font-medium",
              portfolioData.marketStatus === 'open' ? 'bg-green-100 text-green-800' :
              portfolioData.marketStatus === 'pre-market' ? 'bg-blue-100 text-blue-800' :
              portfolioData.marketStatus === 'after-hours' ? 'bg-purple-100 text-purple-800' :
              'bg-gray-100 text-gray-800'
            )}>
              Market {portfolioData.marketStatus.replace('-', ' ')}
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Activity className="h-4 w-4 mr-2" />
            Auto Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={fetchInitialData}>
            <RefreshCcw className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Portfolio Value"
          value={formatCurrency(portfolioData.totalValue)}
          change={portfolioData.totalChangePercent}
          icon={<DollarSign className="h-6 w-6 text-primary" />}
        />
        <MetricCard
          title="Day's Change"
          value={formatCurrency(portfolioData.dayChange)}
          change={portfolioData.dayChangePercent}
          icon={portfolioData.dayChange >= 0 ? 
            <TrendingUp className="h-6 w-6 text-green-600" /> : 
            <TrendingDown className="h-6 w-6 text-red-600" />
          }
        />
        <MetricCard
          title="Cash Balance"
          value={formatCurrency(portfolioData.cashBalance)}
          icon={<PieChart className="h-6 w-6 text-blue-600" />}
        />
        <MetricCard
          title="Invested Amount"
          value={formatCurrency(portfolioData.investedAmount)}
          change={((portfolioData.investedAmount / portfolioData.totalValue) * 100) - 100}
          icon={<BarChart3 className="h-6 w-6 text-purple-600" />}
        />
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-1 bg-muted p-1 rounded-lg">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart3 },
          { id: 'positions', label: 'Positions', icon: PieChart },
          { id: 'analytics', label: 'Analytics', icon: TrendingUp }
        ].map((tab) => (
          <Button
            key={tab.id}
            variant={selectedView === tab.id ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setSelectedView(tab.id as 'overview' | 'positions' | 'analytics')}
            className="flex-1"
          >
            <tab.icon className="h-4 w-4 mr-2" />
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Content based on selected view */}
      <AnimatePresence mode="wait">
        <motion.div
          key={selectedView}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.2 }}
        >
          {selectedView === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Portfolio Chart */}
              <div className="lg:col-span-2">
                <PortfolioChart
                  data={chartData}
                  realTimeUpdates={connectionStatus === 'connected'}
                  config={{
                    type: 'area',
                    title: 'Portfolio Performance',
                    timeframe: selectedTimeframe,
                    height: 400
                  }}
                />
              </div>

              {/* Top Movers */}
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Top Gainers</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {topGainers.map((position) => (
                      <div key={position.symbol} className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{position.symbol}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatCurrency(position.currentPrice)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium text-green-600">
                            +{formatPercentage(position.dayChangePercent)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatCurrency(position.dayChange)}
                          </p>
                        </div>
                      </div>
                    ))}
                    {topGainers.length === 0 && (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No gainers today
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Top Losers</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {topLosers.map((position) => (
                      <div key={position.symbol} className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{position.symbol}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatCurrency(position.currentPrice)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium text-red-600">
                            {formatPercentage(position.dayChangePercent)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatCurrency(position.dayChange)}
                          </p>
                        </div>
                      </div>
                    ))}
                    {topLosers.length === 0 && (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No losers today
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {selectedView === 'positions' && (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Positions List */}
              <div className="lg:col-span-3">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Portfolio Positions</CardTitle>
                      <div className="flex space-x-2">
                        <Button variant="outline" size="sm">
                          <Filter className="h-4 w-4 mr-2" />
                          Filter
                        </Button>
                        <Button variant="outline" size="sm">
                          <Download className="h-4 w-4 mr-2" />
                          Export
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Symbol</th>
                            <th>Quantity</th>
                            <th>Price</th>
                            <th>Market Value</th>
                            <th>Day Change</th>
                            <th>Total Return</th>
                            <th>Weight</th>
                          </tr>
                        </thead>
                        <tbody>
                          {portfolioData.positions.map((position) => (
                            <tr key={position.symbol} className="hover:bg-muted/50">
                              <td>
                                <div>
                                  <p className="font-medium">{position.symbol}</p>
                                  <p className="text-sm text-muted-foreground truncate max-w-[150px]">
                                    {position.name}
                                  </p>
                                </div>
                              </td>
                              <td className="mono">{position.quantity.toFixed(2)}</td>
                              <td className="mono">{formatCurrency(position.currentPrice)}</td>
                              <td className="mono">{formatCurrency(position.marketValue)}</td>
                              <td>
                                <span className={cn(
                                  "flex items-center space-x-1",
                                  getPercentageColor(position.dayChangePercent)
                                )}>
                                  {position.dayChangePercent >= 0 ? 
                                    <TrendingUp className="h-3 w-3" /> : 
                                    <TrendingDown className="h-3 w-3" />
                                  }
                                  <span className="mono">
                                    {formatPercentage(position.dayChangePercent)}
                                  </span>
                                </span>
                              </td>
                              <td>
                                <div>
                                  <p className={cn(
                                    "mono font-medium",
                                    getPercentageColor(position.unrealizedPLPercent)
                                  )}>
                                    {formatPercentage(position.unrealizedPLPercent)}
                                  </p>
                                  <p className={cn(
                                    "text-sm mono",
                                    getPercentageColor(position.unrealizedPL)
                                  )}>
                                    {formatCurrency(position.unrealizedPL)}
                                  </p>
                                </div>
                              </td>
                              <td className="mono">{position.weight.toFixed(1)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Sector Allocation */}
              <div>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Sector Allocation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {sectorAllocation.map((sector) => (
                        <div key={sector.sector}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium">{sector.sector}</span>
                            <span className="text-sm text-muted-foreground">
                              {sector.percentage.toFixed(1)}%
                            </span>
                          </div>
                          <div className="w-full bg-muted rounded-full h-2">
                            <div
                              className="bg-primary rounded-full h-2 transition-all"
                              style={{ width: `${sector.percentage}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Recent Transactions */}
                <Card className="mt-4">
                  <CardHeader>
                    <CardTitle className="text-lg">Recent Activity</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {portfolioData.recentTransactions.slice(0, 5).map((transaction) => (
                        <div key={transaction.id} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-sm">{transaction.symbol}</p>
                            <p className="text-xs text-muted-foreground">
                              {transaction.type.toUpperCase()} {transaction.quantity}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium">
                              {formatCurrency(transaction.amount)}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(transaction.timestamp).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {selectedView === 'analytics' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Performance Analytics</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">Advanced analytics coming soon...</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Risk Metrics</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">Risk analysis coming soon...</p>
                </CardContent>
              </Card>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Alerts Sidebar */}
      {notifications.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: 300 }}
          animate={{ opacity: 1, x: 0 }}
          className="fixed right-4 top-20 w-80 z-50"
        >
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Alerts</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setNotifications([])}
                >
                  Clear All
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 max-h-60 overflow-y-auto">
              {notifications.map((alert) => (
                <div
                  key={alert.id}
                  className={cn(
                    "p-3 rounded-lg border-l-4",
                    alert.severity === 'critical' ? 'border-red-500 bg-red-50' :
                    alert.severity === 'high' ? 'border-orange-500 bg-orange-50' :
                    alert.severity === 'medium' ? 'border-yellow-500 bg-yellow-50' :
                    'border-blue-500 bg-blue-50'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-sm">{alert.title}</h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        {alert.message}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                    {alert.severity === 'critical' && (
                      <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 ml-2" />
                    )}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  )
} 