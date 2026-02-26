'use client';

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';
import { Brain, Zap } from 'lucide-react';
import { logger } from '@/lib/api/app-logger';

export function CachedSentimentPulse() {
  const [data, setData] = useState<{symbol: string, sentiment: {score: number, reason: string}} | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSentiment = async () => {
    try {
      const response = await apiClient.get('/api/v1/analysis/sentiment/cached');
      if (response.data?.data) {
        setData(response.data.data);
      }
    } catch (err) {
      logger.error('Failed to fetch sentiment pulse:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSentiment();
    const intervalId = setInterval(fetchSentiment, 15000); // Poll every 15s to catch the 15m bg update
    return () => clearInterval(intervalId);
  }, []);

  if (loading) return <div className="animate-pulse bg-gray-800/30 h-16 w-full rounded-md" />;

  const isBullish = data && data.sentiment.score > 0.3;
  const isBearish = data && data.sentiment.score < -0.3;
  const colorClass = isBullish ? 'text-green-400' : isBearish ? 'text-red-400' : 'text-gray-400';

  return (
    <div className="bg-gradient-to-r from-gray-900/80 to-gray-950 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-full bg-gray-800 shadow-inner`}>
          <Brain className={`w-6 h-6 ${colorClass}`} />
        </div>
        <div>
          <h4 className="text-gray-200 font-semibold flex items-center gap-2">
            AI Sentiment Pulse
            <span className="flex items-center text-[10px] text-accent-blue bg-accent-blue/10 px-2 py-0.5 rounded-full uppercase tracking-wider">
              <Zap className="w-3 h-3 mr-1" />
              {'< 1ms'}
            </span>
          </h4>
          <p className="text-sm text-gray-500 max-w-md truncate">
            {data?.sentiment.reason || 'Syncing context...'}
          </p>
        </div>
      </div>
      
      <div className="text-right">
        <span className={`text-2xl font-bold font-mono ${colorClass}`}>
          {data ? data.sentiment.score.toFixed(2) : '0.00'}
        </span>
        <div className="text-xs text-gray-600 uppercase tracking-widest mt-1">
          {isBullish ? 'BULLISH' : isBearish ? 'BEARISH' : 'NEUTRAL'}
        </div>
      </div>
    </div>
  );
}
