'use client';

import React, { useEffect, useState } from 'react';
import { SignalCard } from '@/components/SignalCard';

interface Signal {
  symbol: string;
  direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  timeframe: string;
  confidence: number;
  timestamp: string;
  reasoning?: string;
}

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSignals = async () => {
      try {
        // In a real scenario, this would fetch from the API Gateway
        // const res = await fetch('http://localhost:8000/signal/latest');
        // const data = await res.json();
        
        // Mock data for now as the API might not have data yet
        const mockData: Signal[] = [
          {
            symbol: 'XAU/USD',
            direction: 'BULLISH',
            timeframe: '1h',
            confidence: 0.85,
            timestamp: new Date().toISOString(),
            reasoning: 'Price rejected from 4H Order Block with bullish engulfing on 1h. RSI divergence present.'
          },
          {
            symbol: 'EUR/USD',
            direction: 'BEARISH',
            timeframe: '4h',
            confidence: 0.72,
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            reasoning: 'Break of structure to the downside. Retest of bearish FVG.'
          },
          {
            symbol: 'BTC/USD',
            direction: 'NEUTRAL',
            timeframe: '1d',
            confidence: 0.50,
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            reasoning: 'Consolidating within daily range. No clear bias.'
          }
        ];
        
        setSignals(mockData);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch signals');
        setLoading(false);
      }
    };

    fetchSignals();
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0F19] p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-10">
          <h1 className="text-3xl font-bold text-gray-100 tracking-tight mb-2">
            Market Signals
          </h1>
          <p className="text-gray-400">
            Real-time trading opportunities detected by AI and MTF analysis.
          </p>
        </header>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-blue"></div>
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400">
            {error}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {signals.map((signal, index) => (
              <SignalCard key={index} {...signal} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
