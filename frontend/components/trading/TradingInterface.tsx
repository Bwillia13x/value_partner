'use client'

import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useForm } from 'react-hook-form'
import { 
  ShoppingCart,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  XCircle,
  BarChart3,
  Target,
  Shield,
  Zap,
  Wallet,
  Search,
  RefreshCcw
} from 'lucide-react'
import { cn, formatCurrency, formatPercentage, debounce } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StockChart, ChartDataPoint } from '@/components/charts/AdvancedChart'

interface SecurityQuote {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  volume: number
  marketCap: number
  bid: number
  ask: number
  bidSize: number
  askSize: number
  dayHigh: number
  dayLow: number
  fiftyTwoWeekHigh: number
  fiftyTwoWeekLow: number
  lastUpdate: string
  sector: string
  exchange: string
}

interface OrderType {
  id: string
  name: string
  description: string
  icon: React.ReactNode
}

interface Order {
  id: string
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  orderType: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
  limitPrice?: number
  stopPrice?: number
  timeInForce: 'DAY' | 'GTC' | 'IOC' | 'FOK'
  status: 'PENDING' | 'SUBMITTED' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'REJECTED'
  createdAt: string
  estimatedValue: number
  commission: number
}

interface Position {
  symbol: string
  quantity: number
  averageCost: number
  marketValue: number
  unrealizedPL: number
  unrealizedPLPercent: number
}

interface TradingInterfaceProps {
  userId: number
  className?: string
  onOrderSubmit?: (order: Partial<Order>) => void
  paperTrading?: boolean
}

export function TradingInterface({
  userId,
  className,
  onOrderSubmit,
  paperTrading = false
}: TradingInterfaceProps) {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('')
  const [quote, setQuote] = useState<SecurityQuote | null>(null)
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'>('MARKET')
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY')
  const [timeInForce, setTimeInForce] = useState<'DAY' | 'GTC' | 'IOC' | 'FOK'>('DAY')
  const [quantity, setQuantity] = useState<number>(0)
  const [limitPrice, setLimitPrice] = useState<number>(0)
  const [stopPrice, setStopPrice] = useState<number>(0)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [searchResults, setSearchResults] = useState<SecurityQuote[]>([])
  const [recentOrders, setRecentOrders] = useState<Order[]>([])
  const [currentPositions] = useState<Position[]>([])
  const [accountBalance] = useState<number>(0)
  const [buyingPower] = useState<number>(0)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [orderValidation, setOrderValidation] = useState<{
    isValid: boolean
    errors: string[]
    warnings: string[]
  }>({ isValid: true, errors: [], warnings: [] })

  const { handleSubmit, setValue, reset } = useForm()

  const orderTypes: OrderType[] = [
    {
      id: 'MARKET',
      name: 'Market',
      description: 'Execute immediately at current market price',
      icon: <Zap className="h-4 w-4" />
    },
    {
      id: 'LIMIT',
      name: 'Limit',
      description: 'Execute only at specified price or better',
      icon: <Target className="h-4 w-4" />
    },
    {
      id: 'STOP',
      name: 'Stop',
      description: 'Trigger market order when price hits stop price',
      icon: <Shield className="h-4 w-4" />
    },
    {
      id: 'STOP_LIMIT',
      name: 'Stop Limit',
      description: 'Trigger limit order when price hits stop price',
      icon: <BarChart3 className="h-4 w-4" />
    }
  ]

  // Debounced search function
  const debouncedSearch = useMemo(
    () => debounce(async (query: string) => {
      if (query.length < 2) {
        setSearchResults([])
        return
      }

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/market/search?q=${encodeURIComponent(query)}`)
        if (response.ok) {
          const results = await response.json()
          setSearchResults(results)
        }
      } catch (error) {
        console.error('Error searching securities:', error)
      }
    }, 300),
    []
  )

  // Search effect
  useEffect(() => {
    debouncedSearch(searchQuery)
  }, [searchQuery, debouncedSearch])

  // Fetch quote data when symbol changes
  useEffect(() => {
    if (selectedSymbol) {
      fetchQuoteData(selectedSymbol)
      fetchChartData(selectedSymbol)
    }
  }, [selectedSymbol])

  // Update limit price when quote changes
  useEffect(() => {
    if (quote && orderType === 'LIMIT') {
      setLimitPrice(quote.price)
      setValue('limitPrice', quote.price)
    }
  }, [quote, orderType, setValue])

  const fetchQuoteData = async (symbol: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/market/quote/${symbol}`)
      if (response.ok) {
        const quoteData = await response.json()
        setQuote(quoteData)
      }
    } catch (error) {
      console.error('Error fetching quote:', error)
    }
  }

  const fetchChartData = async (symbol: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/market/chart/${symbol}?timeframe=1D`)
      if (response.ok) {
        const chartData = await response.json()
        setChartData(chartData)
      }
    } catch (error) {
      console.error('Error fetching chart data:', error)
    }
  }

  const validateOrder = useCallback(() => {
    const errors: string[] = []
    const warnings: string[] = []

    if (!selectedSymbol) {
      errors.push('Please select a security')
    }

    if (!quantity || quantity <= 0) {
      errors.push('Quantity must be greater than 0')
    }

    if (!quote) {
      errors.push('Unable to get current quote')
      setOrderValidation({ isValid: false, errors, warnings })
      return
    }

    // Calculate estimated value inline
    let estimatedValue = 0
    if (quote && quantity) {
      let price = quote.price
      if (orderType === 'LIMIT' && limitPrice > 0) {
        price = limitPrice
      }
      estimatedValue = quantity * price
    }

    if (orderSide === 'BUY') {
      if (estimatedValue > buyingPower) {
        errors.push('Insufficient buying power')
      }
      
      if (estimatedValue > accountBalance * 0.5) {
        warnings.push('This order represents more than 50% of your account value')
      }
    }

    if (orderType === 'LIMIT') {
      if (!limitPrice || limitPrice <= 0) {
        errors.push('Limit price must be greater than 0')
      } else {
        if (orderSide === 'BUY' && limitPrice > quote.price * 1.05) {
          warnings.push('Limit price is significantly above current market price')
        }
        if (orderSide === 'SELL' && limitPrice < quote.price * 0.95) {
          warnings.push('Limit price is significantly below current market price')
        }
      }
    }

    if (orderType === 'STOP' || orderType === 'STOP_LIMIT') {
      if (!stopPrice || stopPrice <= 0) {
        errors.push('Stop price must be greater than 0')
      }
    }

    const currentPosition = currentPositions.find(p => p.symbol === selectedSymbol)
    if (orderSide === 'SELL' && (!currentPosition || currentPosition.quantity < quantity)) {
      errors.push('Insufficient shares to sell')
    }

    setOrderValidation({
      isValid: errors.length === 0,
      errors,
      warnings
    })
  }, [selectedSymbol, quantity, quote, orderSide, buyingPower, accountBalance, orderType, limitPrice, stopPrice, currentPositions])

  // Validate order
  useEffect(() => {
    validateOrder()
  }, [validateOrder])

  const getEstimatedOrderValue = useCallback((): number => {
    if (!quote || !quantity) return 0
    
    let price = quote.price
    if (orderType === 'LIMIT' && limitPrice > 0) {
      price = limitPrice
    }
    
    const value = quantity * price
    const commission = 0 // Assuming commission-free trading
    
    return value + commission
  }, [quote, quantity, orderType, limitPrice])

  const handleSymbolSelect = (symbol: string) => {
    setSelectedSymbol(symbol)
    setSearchQuery(symbol)
    setSearchResults([])
  }

  const handleOrderSubmit = async () => {
    if (!orderValidation.isValid) return

    setIsLoading(true)

    const order: Partial<Order> = {
      symbol: selectedSymbol,
      side: orderSide,
      quantity: quantity,
      orderType: orderType,
      limitPrice: orderType === 'LIMIT' || orderType === 'STOP_LIMIT' ? limitPrice : undefined,
      stopPrice: orderType === 'STOP' || orderType === 'STOP_LIMIT' ? stopPrice : undefined,
      timeInForce: timeInForce,
      estimatedValue: getEstimatedOrderValue()
    }

    try {
      if (onOrderSubmit) {
        await onOrderSubmit(order)
      } else {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/orders`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            ...order,
            user_id: userId
          })
        })

        if (response.ok) {
          const newOrder = await response.json()
          setRecentOrders(prev => [newOrder, ...prev.slice(0, 9)])
          reset()
          setQuantity(0)
          setLimitPrice(0)
          setStopPrice(0)
        } else {
          throw new Error('Failed to submit order')
        }
      }
    } catch (error) {
      console.error('Error submitting order:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const quickQuantityButtons = [10, 25, 50, 100, 500]

  return (
    <div className={cn("grid grid-cols-1 lg:grid-cols-4 gap-6", className)}>
      {/* Security Search & Selection */}
      <div className="lg:col-span-1">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Search className="h-5 w-5 mr-2" />
              Security Search
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search symbols..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="form-input w-full"
                />
                {searchResults.length > 0 && (
                  <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                    {searchResults.map((result) => (
                      <button
                        key={result.symbol}
                        onClick={() => handleSymbolSelect(result.symbol)}
                        className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center justify-between"
                      >
                        <div>
                          <p className="font-medium">{result.symbol}</p>
                          <p className="text-sm text-gray-500 truncate">{result.name}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium">{formatCurrency(result.price)}</p>
                          <p className={cn(
                            "text-sm",
                            result.change >= 0 ? "text-green-600" : "text-red-600"
                          )}>
                            {result.change >= 0 ? "+" : ""}{formatPercentage(result.changePercent)}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {selectedSymbol && quote && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 bg-muted rounded-lg"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-bold text-lg">{quote.symbol}</h3>
                    <Button variant="ghost" size="sm" onClick={() => fetchQuoteData(selectedSymbol)}>
                      <RefreshCcw className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3 truncate">{quote.name}</p>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-2xl font-bold">{formatCurrency(quote.price)}</span>
                      <span className={cn(
                        "flex items-center text-sm font-medium",
                        quote.change >= 0 ? "text-green-600" : "text-red-600"
                      )}>
                        {quote.change >= 0 ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                        {quote.change >= 0 ? "+" : ""}{formatCurrency(quote.change)} ({formatPercentage(quote.changePercent)})
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Bid:</span>
                        <span className="ml-1 font-medium">{formatCurrency(quote.bid)}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Ask:</span>
                        <span className="ml-1 font-medium">{formatCurrency(quote.ask)}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Day High:</span>
                        <span className="ml-1 font-medium">{formatCurrency(quote.dayHigh)}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Day Low:</span>
                        <span className="ml-1 font-medium">{formatCurrency(quote.dayLow)}</span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Account Info */}
              <div className="p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium flex items-center mb-2">
                  <Wallet className="h-4 w-4 mr-2" />
                  Account Balance
                </h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Cash:</span>
                    <span className="font-medium">{formatCurrency(accountBalance)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Buying Power:</span>
                    <span className="font-medium">{formatCurrency(buyingPower)}</span>
                  </div>
                </div>
                {paperTrading && (
                  <div className="mt-2 text-xs text-blue-600 font-medium">
                    📝 Paper Trading Mode
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chart & Order Form */}
      <div className="lg:col-span-2">
        <div className="space-y-6">
          {/* Chart */}
          {selectedSymbol && chartData.length > 0 && (
            <StockChart
              symbol={selectedSymbol}
              data={chartData}
              config={{
                type: 'candlestick',
                title: `${selectedSymbol} Price Chart`,
                symbol: selectedSymbol,
                showVolume: true,
                height: 300
              }}
            />
          )}

          {/* Order Form */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <ShoppingCart className="h-5 w-5 mr-2" />
                Place Order
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit(handleOrderSubmit)} className="space-y-4">
                {/* Order Side */}
                <div className="flex space-x-2">
                  <Button
                    type="button"
                    variant={orderSide === 'BUY' ? 'default' : 'outline'}
                    className={cn(
                      "flex-1",
                      orderSide === 'BUY' && "bg-green-600 hover:bg-green-700"
                    )}
                    onClick={() => setOrderSide('BUY')}
                  >
                    <TrendingUp className="h-4 w-4 mr-2" />
                    Buy
                  </Button>
                  <Button
                    type="button"
                    variant={orderSide === 'SELL' ? 'default' : 'outline'}
                    className={cn(
                      "flex-1",
                      orderSide === 'SELL' && "bg-red-600 hover:bg-red-700"
                    )}
                    onClick={() => setOrderSide('SELL')}
                  >
                    <TrendingDown className="h-4 w-4 mr-2" />
                    Sell
                  </Button>
                </div>

                {/* Order Type */}
                <div>
                  <label className="form-label">Order Type</label>
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    {orderTypes.map((type) => (
                      <Button
                        key={type.id}
                        type="button"
                        variant={orderType === type.id ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setOrderType(type.id as 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT')}
                        className="justify-start"
                      >
                        {type.icon}
                        <span className="ml-2">{type.name}</span>
                      </Button>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {orderTypes.find(t => t.id === orderType)?.description}
                  </p>
                </div>

                {/* Quantity */}
                <div>
                  <label className="form-label">Quantity</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      placeholder="0"
                      value={quantity || ''}
                      onChange={(e) => setQuantity(Number(e.target.value))}
                      className="form-input flex-1"
                      min="0"
                      step="1"
                    />
                    <div className="flex space-x-1">
                      {quickQuantityButtons.map((qty) => (
                        <Button
                          key={qty}
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setQuantity(qty)}
                        >
                          {qty}
                        </Button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Limit Price */}
                {(orderType === 'LIMIT' || orderType === 'STOP_LIMIT') && (
                  <div>
                    <label className="form-label">Limit Price</label>
                    <input
                      type="number"
                      placeholder="0.00"
                      value={limitPrice || ''}
                      onChange={(e) => setLimitPrice(Number(e.target.value))}
                      className="form-input w-full"
                      min="0"
                      step="0.01"
                    />
                  </div>
                )}

                {/* Stop Price */}
                {(orderType === 'STOP' || orderType === 'STOP_LIMIT') && (
                  <div>
                    <label className="form-label">Stop Price</label>
                    <input
                      type="number"
                      placeholder="0.00"
                      value={stopPrice || ''}
                      onChange={(e) => setStopPrice(Number(e.target.value))}
                      className="form-input w-full"
                      min="0"
                      step="0.01"
                    />
                  </div>
                )}

                {/* Time in Force */}
                <div>
                  <label className="form-label">Time in Force</label>
                  <select
                    value={timeInForce}
                    onChange={(e) => setTimeInForce(e.target.value as 'DAY' | 'GTC' | 'IOC' | 'FOK')}
                    className="form-input w-full"
                  >
                    <option value="DAY">Day</option>
                    <option value="GTC">Good Till Cancelled</option>
                    <option value="IOC">Immediate or Cancel</option>
                    <option value="FOK">Fill or Kill</option>
                  </select>
                </div>

                {/* Order Summary */}
                {quantity > 0 && quote && (
                  <div className="p-4 bg-muted rounded-lg">
                    <h4 className="font-medium mb-2">Order Summary</h4>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>Estimated Value:</span>
                        <span className="font-medium">{formatCurrency(getEstimatedOrderValue())}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Commission:</span>
                        <span className="font-medium">$0.00</span>
                      </div>
                      <div className="border-t pt-1">
                        <div className="flex justify-between font-medium">
                          <span>Total:</span>
                          <span>{formatCurrency(getEstimatedOrderValue())}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Validation Messages */}
                {orderValidation.errors.length > 0 && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-center text-red-800 text-sm font-medium mb-1">
                      <XCircle className="h-4 w-4 mr-2" />
                      Please fix the following errors:
                    </div>
                    <ul className="text-sm text-red-700 list-disc list-inside">
                      {orderValidation.errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {orderValidation.warnings.length > 0 && (
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-center text-yellow-800 text-sm font-medium mb-1">
                      <AlertTriangle className="h-4 w-4 mr-2" />
                      Please review:
                    </div>
                    <ul className="text-sm text-yellow-700 list-disc list-inside">
                      {orderValidation.warnings.map((warning, index) => (
                        <li key={index}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Submit Button */}
                <Button
                  type="submit"
                  fullWidth
                  size="lg"
                  variant={orderSide === 'BUY' ? 'success' : 'destructive'}
                  disabled={!orderValidation.isValid || isLoading}
                  loading={isLoading}
                >
                  {orderSide === 'BUY' ? 'Place Buy Order' : 'Place Sell Order'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Orders & Positions */}
      <div className="lg:col-span-1">
        <div className="space-y-6">
          {/* Recent Orders */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Recent Orders</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentOrders.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No recent orders
                  </p>
                ) : (
                  recentOrders.map((order) => (
                    <div key={order.id} className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium">{order.symbol}</span>
                          <span className={cn(
                            "text-xs px-2 py-1 rounded-full",
                            order.side === 'BUY' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          )}>
                            {order.side}
                          </span>
                        </div>
                        <span className={cn(
                          "text-xs px-2 py-1 rounded-full",
                          order.status === 'FILLED' ? 'bg-green-100 text-green-800' :
                          order.status === 'CANCELLED' ? 'bg-red-100 text-red-800' :
                          order.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        )}>
                          {order.status}
                        </span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        <p>{order.quantity} shares @ {order.orderType}</p>
                        <p>{formatCurrency(order.estimatedValue)}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Current Positions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Positions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {currentPositions.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No current positions
                  </p>
                ) : (
                  currentPositions.map((position) => (
                    <div key={position.symbol} className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium">{position.symbol}</span>
                        <span className="text-sm font-medium">
                          {formatCurrency(position.marketValue)}
                        </span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        <div className="flex justify-between">
                          <span>{position.quantity} shares</span>
                          <span className={cn(
                            position.unrealizedPL >= 0 ? "text-green-600" : "text-red-600"
                          )}>
                            {position.unrealizedPL >= 0 ? "+" : ""}{formatPercentage(position.unrealizedPLPercent)}
                          </span>
                        </div>
                        <p>Avg Cost: {formatCurrency(position.averageCost)}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
} 