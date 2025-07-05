'use client'

import { useEffect, useState } from 'react'

interface PlaidLinkProps {
  userId: number
  onSuccess: (publicToken: string) => void
  onError?: (error: Error | unknown) => void
}

export default function PlaidLink({ userId, onSuccess, onError }: PlaidLinkProps) {
  const [linkToken, setLinkToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const createLinkToken = async () => {
      try {
        setLoading(true)
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/portfolio/link/token?user_id=${userId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error('Failed to create link token')
        }

        const data = await response.json()
        setLinkToken(data.link_token)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to initialize Plaid')
        if (onError) onError(err)
      } finally {
        setLoading(false)
      }
    }

    createLinkToken()
  }, [userId, onError])

  const handleLinkAccount = async () => {
    if (!linkToken) return

    try {
      // In a real implementation, you would use the Plaid Link SDK
      // For now, we'll simulate the flow
      
      // This is where you would integrate with Plaid Link:
      // const linkHandler = Plaid.create({
      //   token: linkToken,
      //   onSuccess: (public_token, metadata) => {
      //     onSuccess(public_token)
      //   },
      //   onExit: (err, metadata) => {
      //     if (err && onError) onError(err)
      //   }
      // })
      // linkHandler.open()
      
      // For demo purposes, we'll show a placeholder
      alert('In a real implementation, this would open Plaid Link to connect your bank account.')
      
    } catch (err) {
      if (onError) onError(err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Initializing bank connection...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Connect Your Bank Account</h3>
      <p className="text-sm text-gray-600 mb-6">
        Securely connect your bank account to start tracking your portfolio. 
        We use bank-level security to protect your data.
      </p>
      
      <div className="space-y-4">
        <div className="flex items-center">
          <svg className="h-5 w-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm text-gray-700">256-bit SSL encryption</span>
        </div>
        <div className="flex items-center">
          <svg className="h-5 w-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm text-gray-700">Read-only access</span>
        </div>
        <div className="flex items-center">
          <svg className="h-5 w-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm text-gray-700">Used by millions of users</span>
        </div>
      </div>
      
      <button
        onClick={handleLinkAccount}
        className="w-full mt-6 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
      >
        Connect Bank Account
      </button>
      
      <p className="mt-4 text-xs text-gray-500 text-center">
        Powered by Plaid • Your data is encrypted and secure
      </p>
    </div>
  )
}