'use client';

import React, { useEffect, useState } from 'react';
import { SignalCard } from '@/components/SignalCard';
import { SkippedTradesTable } from '@/components/analysis/SkippedTradesTable';

import { getRecentSignals } from '@/lib/api/dashboard';

import { RecentSignal } from '@/lib/api/types';

export default function SignalsPage() {
  const [signals, setSignals] = useState<RecentSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const data = await getRecentSignals(10); // Fetch up to 10
        setSignals(data);
        setLoading(false);
      } catch {
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
        
        <div className="mt-12">
             <SkippedTradesTable />
        </div>
      </div>
    </div>
  );
}

