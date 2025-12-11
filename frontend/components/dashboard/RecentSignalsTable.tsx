'use client';

import React from 'react';
import Link from 'next/link';
import { RecentSignal } from '@/lib/api/types';

interface RecentSignalsTableProps {
  signals: RecentSignal[];
  loading?: boolean;
}

export const RecentSignalsTable: React.FC<RecentSignalsTableProps> = ({ signals, loading }) => {
  if (loading) {
    return (
      <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
        <h2 className="text-xl font-bold text-gray-100 mb-4">Recent Signals</h2>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-800/30 animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (signals.length === 0) {
    return (
      <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
        <h2 className="text-xl font-bold text-gray-100 mb-4">Recent Signals</h2>
        <div className="text-center py-8">
          <div className="text-gray-500 mb-2">No signals available</div>
          <p className="text-sm text-gray-600">Signals will appear here once the strategy generates them</p>
        </div>
      </div>
    );
  }

  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'BULLISH':
        return 'bg-accent-green/10 text-accent-green border-accent-green/20';
      case 'BEARISH':
        return 'bg-red-400/10 text-red-400 border-red-400/20';
      default:
        return 'bg-gray-400/10 text-gray-400 border-gray-400/20';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-100">Recent Signals</h2>
        <Link 
          href="/signals" 
          className="text-sm text-accent-blue hover:text-accent-blue/80 transition-colors"
        >
          View All →
        </Link>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Symbol</th>
              <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Direction</th>
              <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Confidence</th>
              {/* Current column removed */}
              <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Timeframe</th>
              <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Time</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((signal) => {
              return (
              <tr key={signal.id} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors">
                <td className="py-3 px-4">
                  <span className="font-mono text-gray-200 font-medium">{signal.symbol}</span>
                </td>
                <td className="py-3 px-4">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium border ${getDirectionColor(signal.direction)}`}>
                    {signal.direction}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-800 rounded-full h-2 max-w-[100px]">
                      <div 
                        className="h-2 rounded-full bg-gradient-to-r from-accent-blue to-accent-green transition-all duration-500"
                        style={{ width: `${signal.confidence}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-300 font-mono">{signal.confidence}%</span>
                  </div>
                </td>
                {/* Current cell removed */}
                <td className="py-3 px-4">
                  <span className="text-sm text-gray-400 font-mono">{signal.timeframe}</span>
                </td>
                <td className="py-3 px-4">
                  <span className="text-sm text-gray-500">{formatTimestamp(signal.timestamp)}</span>
                </td>
              </tr>
            )})}
          </tbody>
        </table>
      </div>
    </div>
  );
};
