'use client'

import { useState, useEffect, Suspense } from 'react'
import { motion } from 'framer-motion'
import { 
  TrendingUp, 
  BarChart3, 
  PieChart, 
  Activity, 
  AlertTriangle,
  Loader2,
  RefreshCcw
} from 'lucide-react'
import PlaidLink from '../../components/PlaidLink'
import { RealTimeDashboard } from '../../components/dashboard/RealTimeDashboard'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'

interface AccountSetupProps {
  userId: number
  onSuccess: () => void
}

function AccountSetup({ userId, onSuccess }: AccountSetupProps) {
  const [isConnecting, setIsConnecting] = useState(false)

  const handlePlaidSuccess = async (publicToken: string) => {
    try {
      setIsConnecting(true)
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/portfolio/link/exchange`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          public_token: publicToken,
          user_id: userId,
        }),
      })

      if (response.ok) {
        // Wait a moment for sync to start, then notify success
        setTimeout(() => {
          onSuccess()
          setIsConnecting(false)
        }, 2000)
      } else {
        throw new Error('Failed to exchange token')
      }
    } catch (err) {
      console.error('Error exchanging token:', err)
      setIsConnecting(false)
    }
  }

  if (isConnecting) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="min-h-[60vh] flex items-center justify-center"
      >
        <Card className="w-full max-w-md mx-auto">
          <CardContent className="p-8 text-center">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              className="inline-block mb-4"
            >
              <Loader2 className="h-12 w-12 text-primary" />
            </motion.div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Connecting Your Account</h2>
            <p className="text-gray-600 mb-4">
              We&apos;re securely connecting your bank account and syncing your data...
            </p>
            <div className="space-y-2 text-sm text-gray-500">
              <div className="flex items-center justify-center space-x-2">
                <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                <span>Establishing secure connection</span>
              </div>
              <div className="flex items-center justify-center space-x-2">
                <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse delay-75"></div>
                <span>Syncing account data</span>
              </div>
              <div className="flex items-center justify-center space-x-2">
                <div className="h-2 w-2 bg-purple-500 rounded-full animate-pulse delay-150"></div>
                <span>Analyzing your portfolio</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="min-h-[60vh] flex items-center justify-center"
    >
      <Card className="w-full max-w-2xl mx-auto">
        <CardHeader className="text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 150 }}
            className="mx-auto mb-4 h-20 w-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center"
          >
            <TrendingUp className="h-10 w-10 text-white" />
          </motion.div>
          <CardTitle className="text-3xl font-bold text-gradient">
            Welcome to Value Partner
          </CardTitle>
          <p className="text-lg text-muted-foreground mt-2">
            Connect your investment accounts to get started with advanced portfolio analytics
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="text-center p-4"
            >
              <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center mx-auto mb-3">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="font-semibold mb-1">Real-Time Analytics</h3>
              <p className="text-sm text-muted-foreground">
                Track your portfolio performance with live market data and advanced metrics
              </p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="text-center p-4"
            >
              <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-3">
                <PieChart className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="font-semibold mb-1">Smart Insights</h3>
              <p className="text-sm text-muted-foreground">
                AI-powered recommendations and risk analysis for better investment decisions
              </p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
              className="text-center p-4"
            >
              <div className="h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center mx-auto mb-3">
                <Activity className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="font-semibold mb-1">Automated Monitoring</h3>
              <p className="text-sm text-muted-foreground">
                Set up alerts and automated rebalancing for optimal portfolio management
              </p>
            </motion.div>
          </div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="max-w-md mx-auto"
          >
            <PlaidLink
              userId={userId}
              onSuccess={handlePlaidSuccess}
              onError={(error) => console.error('Plaid error:', error)}
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="text-center"
          >
            <div className="inline-flex items-center space-x-2 text-sm text-muted-foreground bg-muted px-4 py-2 rounded-full">
              <svg className="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-7-4z" clipRule="evenodd" />
              </svg>
              <span>Bank-level security with 256-bit encryption</span>
            </div>
          </motion.div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

interface PortfolioLoadingProps {
  onRetry: () => void
}

function PortfolioLoading({ }: PortfolioLoadingProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-[60vh] flex items-center justify-center"
    >
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="p-8 text-center">
          <motion.div
            animate={{ 
              scale: [1, 1.1, 1],
              opacity: [0.5, 1, 0.5]
            }}
            transition={{ 
              duration: 2, 
              repeat: Infinity, 
              ease: "easeInOut" 
            }}
            className="inline-block mb-4"
          >
            <BarChart3 className="h-12 w-12 text-primary" />
          </motion.div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Loading Portfolio</h2>
          <p className="text-gray-600 mb-6">
            Gathering your investment data and calculating performance metrics...
          </p>
          <div className="space-y-2">
            {['Account balances', 'Holdings analysis', 'Performance metrics'].map((item, index) => (
              <motion.div
                key={item}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.2 }}
                className="flex items-center space-x-3"
              >
                <div className="h-2 w-2 bg-primary rounded-full animate-pulse" 
                     style={{ animationDelay: `${index * 200}ms` }} />
                <span className="text-sm text-muted-foreground">{item}</span>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function PortfolioError({ onRetry }: PortfolioLoadingProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="min-h-[60vh] flex items-center justify-center"
    >
      <Card className="w-full max-w-md mx-auto">
        <CardContent className="p-8 text-center">
          <motion.div
            animate={{ rotate: [0, 10, -10, 0] }}
            transition={{ duration: 0.5, repeat: 2 }}
            className="inline-block mb-4"
          >
            <AlertTriangle className="h-12 w-12 text-yellow-500" />
          </motion.div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Unable to Load Portfolio</h2>
          <p className="text-gray-600 mb-6">
            We&apos;re having trouble loading your portfolio data. Please check your connection and try again.
          </p>
          <Button onClick={onRetry} className="w-full">
            <RefreshCcw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default function PortfolioPage() {
  const [userId] = useState(1) // In real app, get from auth context
  const [hasAccounts, setHasAccounts] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    checkForAccounts()
  }, [userId, checkForAccounts])

  async function checkForAccounts() {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/portfolio/accounts?user_id=${userId}`)
      
      if (response.ok) {
        const accounts = await response.json()
        setHasAccounts(accounts.length > 0)
      } else {
        throw new Error('Failed to check accounts')
      }
    } catch (err) {
      console.error('Error checking accounts:', err)
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleAccountConnected = () => {
    setHasAccounts(true)
  }

  if (loading && hasAccounts === null) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <PortfolioLoading onRetry={checkForAccounts} />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-red-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <PortfolioError onRetry={checkForAccounts} />
        </div>
      </div>
    )
  }

  if (!hasAccounts) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <AccountSetup userId={userId} onSuccess={handleAccountConnected} />
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50/30"
    >
      <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Suspense fallback={<PortfolioLoading onRetry={checkForAccounts} />}>
          <RealTimeDashboard 
            userId={userId}
            enableNotifications={true}
            refreshInterval={5000}
          />
        </Suspense>
      </div>
    </motion.div>
  )
}