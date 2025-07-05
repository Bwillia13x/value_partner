'use client'

import React, { useEffect, useRef, useState } from 'react'
import { createChart, IChartApi, ISeriesApi, LineStyle, CrosshairMode, UTCTimestamp } from 'lightweight-charts'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  LineChart, 
  CandlestickChart,
  Maximize2,
  Download,
} from 'lucide-react'

export interface ChartDataPoint {
  time: UTCTimestamp
  value: number
  open?: number
  high?: number
  low?: number
  close?: number
  volume?: number
}

export interface ChartConfig {
  type: 'line' | 'area' | 'candlestick' | 'histogram' | 'baseline'
  title: string
  symbol?: string
  timeframe?: string
  showVolume?: boolean
  showGrid?: boolean
  showCrosshair?: boolean
  height?: number
  theme?: 'light' | 'dark'
}

interface AdvancedChartProps {
  data: ChartDataPoint[]
  config: ChartConfig
  className?: string
  onDataPointClick?: (dataPoint: ChartDataPoint) => void
  realTimeUpdates?: boolean
  loading?: boolean
}

export function AdvancedChart({
  data,
  config,
  className,
  onDataPointClick,
  realTimeUpdates = false,
  loading = false
}: AdvancedChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [chartType, setChartType] = useState(config.type)

  useEffect(() => {
    if (!chartContainerRef.current) return

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: config.height || 400,
      layout: {
        background: { color: 'transparent' },
        textColor: config.theme === 'dark' ? '#d1d5db' : '#374151',
      },
      grid: {
        vertLines: { 
          color: config.theme === 'dark' ? '#374151' : '#e5e7eb',
          visible: config.showGrid !== false
        },
        horzLines: { 
          color: config.theme === 'dark' ? '#374151' : '#e5e7eb',
          visible: config.showGrid !== false
        },
      },
      crosshair: {
        mode: config.showCrosshair !== false ? CrosshairMode.Normal : CrosshairMode.Hidden,
        vertLine: {
          color: '#9CA3AF',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: '#1f2937',
        },
        horzLine: {
          color: '#9CA3AF',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: '#1f2937',
        },
      },
      rightPriceScale: {
        borderColor: config.theme === 'dark' ? '#374151' : '#e5e7eb',
        textColor: config.theme === 'dark' ? '#d1d5db' : '#374151',
      },
      timeScale: {
        borderColor: config.theme === 'dark' ? '#374151' : '#e5e7eb',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    })

    chartRef.current = chart

    // Create main series based on chart type
    let series: any
    
    switch (chartType) {
      case 'line':
        series = chart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 2,
        })
        break
      case 'area':
        series = chart.addAreaSeries({
          topColor: 'rgba(59, 130, 246, 0.4)',
          bottomColor: 'rgba(59, 130, 246, 0.0)',
          lineColor: '#3b82f6',
          lineWidth: 2,
        })
        break
      case 'candlestick':
        series = chart.addCandlestickSeries({
          upColor: '#10b981',
          downColor: '#ef4444',
          borderDownColor: '#ef4444',
          borderUpColor: '#10b981',
          wickDownColor: '#ef4444',
          wickUpColor: '#10b981',
        })
        break
      case 'histogram':
        series = chart.addHistogramSeries({
          color: '#8b5cf6',
          priceFormat: {
            type: 'volume',
          },
        })
        break
      case 'baseline':
        series = chart.addBaselineSeries({
          baseValue: { type: 'price', price: data[0]?.value || 0 },
          topFillColor1: 'rgba(16, 185, 129, 0.28)',
          topFillColor2: 'rgba(16, 185, 129, 0.05)',
          topLineColor: '#10b981',
          bottomFillColor1: 'rgba(239, 68, 68, 0.28)',
          bottomFillColor2: 'rgba(239, 68, 68, 0.05)',
          bottomLineColor: '#ef4444',
        })
        break
      default:
        series = chart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 2,
        })
    }

    seriesRef.current = series

    // Add volume series if enabled
    if (config.showVolume && data.some(d => d.volume)) {
      const volumeSeries = chart.addHistogramSeries({
        color: '#9ca3af',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'volume',
      })
      
      chart.priceScale('volume').applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      })
      
      volumeSeriesRef.current = volumeSeries
      
      const volumeData = data
        .filter(d => d.volume)
        .map(d => ({
          time: d.time,
          value: d.volume!,
          color: d.close && d.open ? 
            (d.close >= d.open ? '#10b981' : '#ef4444') : '#9ca3af'
        }))
      
      volumeSeries.setData(volumeData)
    }

    // Set data
    const chartData = data.map(d => {
      if (chartType === 'candlestick') {
        return {
          time: d.time,
          open: d.open || d.value,
          high: d.high || d.value,
          low: d.low || d.value,
          close: d.close || d.value,
        }
      } else {
        return {
          time: d.time,
          value: d.close || d.value,
        }
      }
    })

    series.setData(chartData)

    // Handle click events
    if (onDataPointClick) {
      chart.subscribeCrosshairMove((param) => {
        if (param.time && param.point) {
          const dataPoint = data.find(d => d.time === param.time)
          if (dataPoint) {
            onDataPointClick(dataPoint)
          }
        }
      })
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [data, config, chartType])

  // Real-time updates
  useEffect(() => {
    if (!realTimeUpdates || !seriesRef.current || data.length === 0) return

    const lastDataPoint = data[data.length - 1]
    const chartData = chartType === 'candlestick' ? {
      time: lastDataPoint.time,
      open: lastDataPoint.open || lastDataPoint.value,
      high: lastDataPoint.high || lastDataPoint.value,
      low: lastDataPoint.low || lastDataPoint.value,
      close: lastDataPoint.close || lastDataPoint.value,
    } : {
      time: lastDataPoint.time,
      value: lastDataPoint.close || lastDataPoint.value,
    }

    seriesRef.current.update(chartData)

    if (volumeSeriesRef.current && lastDataPoint.volume) {
      volumeSeriesRef.current.update({
        time: lastDataPoint.time,
        value: lastDataPoint.volume,
        color: lastDataPoint.close && lastDataPoint.open ? 
          (lastDataPoint.close >= lastDataPoint.open ? '#10b981' : '#ef4444') : '#9ca3af'
      })
    }
  }, [data, realTimeUpdates, chartType])

  const handleExport = () => {
    if (!chartRef.current) return
    
    const canvas = chartContainerRef.current?.querySelector('canvas')
    if (canvas) {
      const link = document.createElement('a')
      link.download = `${config.symbol || 'chart'}-${config.timeframe || 'data'}.png`
      link.href = canvas.toDataURL()
      link.click()
    }
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
    setTimeout(() => {
      if (chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current?.clientWidth || 800,
          height: isFullscreen ? 400 : 600,
        })
      }
    }, 100)
  }

  const getLatestPrice = () => {
    if (data.length === 0) return null
    const latest = data[data.length - 1]
    return latest.close || latest.value
  }

  const getPriceChange = () => {
    if (data.length < 2) return null
    const latest = data[data.length - 1]
    const previous = data[data.length - 2]
    const currentPrice = latest.close || latest.value
    const previousPrice = previous.close || previous.value
    const change = currentPrice - previousPrice
    const changePercent = (change / previousPrice) * 100
    return { change, changePercent }
  }

  const latestPrice = getLatestPrice()
  const priceChange = getPriceChange()

  if (loading) {
    return (
      <Card className={cn("", className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">{config.title}</CardTitle>
              <div className="flex items-center space-x-2 mt-1">
                <div className="h-4 w-20 bg-gray-200 rounded animate-pulse"></div>
                <div className="h-4 w-16 bg-gray-200 rounded animate-pulse"></div>
              </div>
            </div>
            <div className="flex space-x-2">
              <div className="h-8 w-8 bg-gray-200 rounded animate-pulse"></div>
              <div className="h-8 w-8 bg-gray-200 rounded animate-pulse"></div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-gray-100 rounded animate-pulse"></div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn("relative", className, isFullscreen && "fixed inset-4 z-50")}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">{config.title}</CardTitle>
            {config.symbol && (
              <div className="flex items-center space-x-2 mt-1">
                <span className="text-sm text-muted-foreground">{config.symbol}</span>
                {config.timeframe && (
                  <span className="text-xs bg-muted px-2 py-1 rounded">
                    {config.timeframe}
                  </span>
                )}
                {latestPrice && (
                  <span className="text-lg font-bold">
                    ${latestPrice.toFixed(2)}
                  </span>
                )}
                {priceChange && (
                  <span className={cn(
                    "text-sm font-medium flex items-center",
                    priceChange.change >= 0 ? "text-green-600" : "text-red-600"
                  )}>
                    {priceChange.change >= 0 ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                    {priceChange.change >= 0 ? "+" : ""}{priceChange.change.toFixed(2)} ({priceChange.changePercent.toFixed(2)}%)
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex space-x-2">
            <div className="flex bg-muted rounded-md p-1">
              <Button
                size="sm"
                variant={chartType === 'line' ? 'default' : 'ghost'}
                onClick={() => setChartType('line')}
                className="h-6 px-2"
              >
                <LineChart className="h-3 w-3" />
              </Button>
              <Button
                size="sm"
                variant={chartType === 'area' ? 'default' : 'ghost'}
                onClick={() => setChartType('area')}
                className="h-6 px-2"
              >
                <BarChart3 className="h-3 w-3" />
              </Button>
              <Button
                size="sm"
                variant={chartType === 'candlestick' ? 'default' : 'ghost'}
                onClick={() => setChartType('candlestick')}
                className="h-6 px-2"
              >
                <CandlestickChart className="h-3 w-3" />
              </Button>
            </div>
            <Button size="sm" variant="ghost" onClick={handleExport}>
              <Download className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="ghost" onClick={toggleFullscreen}>
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div 
          ref={chartContainerRef} 
          className={cn(
            "w-full", 
            isFullscreen ? "h-[calc(100vh-200px)]" : `h-[${config.height || 400}px]`
          )}
        />
        {realTimeUpdates && (
          <div className="mt-2 flex items-center text-sm text-muted-foreground">
            <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
            Live data feed active
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Specialized chart components
export function StockChart({ symbol, data, ...props }: { symbol: string, data: ChartDataPoint[] } & Partial<AdvancedChartProps>) {
  return (
    <AdvancedChart
      data={data}
      config={{
        type: 'candlestick',
        title: `${symbol} Stock Price`,
        symbol,
        showVolume: true,
        ...props.config
      }}
      {...props}
    />
  )
}

export function PortfolioChart({ data, ...props }: { data: ChartDataPoint[] } & Partial<AdvancedChartProps>) {
  return (
    <AdvancedChart
      data={data}
      config={{
        type: 'area',
        title: 'Portfolio Performance',
        showGrid: true,
        showCrosshair: true,
        ...props.config
      }}
      {...props}
    />
  )
}

export function ComparisonChart({ 
  datasets, 
  title = "Performance Comparison",
  ...props 
}: { 
  datasets: { name: string, data: ChartDataPoint[], color: string }[]
  title?: string
} & Partial<AdvancedChartProps>) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current || datasets.length === 0) return

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: 'transparent' },
        textColor: '#374151',
      },
      grid: {
        vertLines: { color: '#e5e7eb' },
        horzLines: { color: '#e5e7eb' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#e5e7eb',
      },
      timeScale: {
        borderColor: '#e5e7eb',
        timeVisible: true,
      },
    })

    chartRef.current = chart

    datasets.forEach((dataset) => {
      const series = chart.addLineSeries({
        color: dataset.color,
        lineWidth: 2,
        title: dataset.name,
      })

      const seriesData = dataset.data.map(d => ({
        time: d.time,
        value: d.close || d.value,
      }))

      series.setData(seriesData)
    })

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [datasets])

  return (
    <Card className={props.className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <div className="flex flex-wrap gap-4 mt-2">
          {datasets.map((dataset, index) => (
            <div key={index} className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: dataset.color }}
              />
              <span className="text-sm text-muted-foreground">{dataset.name}</span>
            </div>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <div ref={chartContainerRef} className="w-full h-96" />
      </CardContent>
    </Card>
  )
} 