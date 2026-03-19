'use client';

import React, { useMemo } from 'react';
import { LatencyBucket } from '@/lib/api/types';

interface LatencyHeatmapProps {
  data: LatencyBucket[];
  loading?: boolean;
}

export const LatencyHeatmap: React.FC<LatencyHeatmapProps> = ({ data, loading }) => {
  const symbols = useMemo(() => Array.from(new Set(data.map((b) => b.symbol))).sort(), [data]);
  const hours = Array.from({ length: 24 }, (_, i) => i);

  const getLatencyColor = (latency: number) => {
    if (latency < 50) return 'bg-green-500/40';
    if (latency < 150) return 'bg-yellow-500/40';
    if (latency < 300) return 'bg-orange-500/40';
    return 'bg-red-500/40';
  };

  const gridData = useMemo(() => {
    const grid: Record<string, Record<number, number>> = {};
    symbols.forEach((s) => {
      grid[s] = {};
    });
    data.forEach((b) => {
      if (grid[b.symbol]) {
        grid[b.symbol][b.hour] = b.avg_latency_ms;
      }
    });
    return grid;
  }, [data, symbols]);

  if (loading) {
    return (
      <div className="h-[400px] w-full bg-gray-950/50 rounded-xl border border-gray-800 animate-pulse flex items-center justify-center">
        <span className="text-gray-500">Loading latency data...</span>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="h-[400px] w-full bg-gray-950/50 rounded-xl border border-gray-800 flex items-center justify-center">
        <span className="text-gray-400">No latency data available for the selected period.</span>
      </div>
    );
  }

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 overflow-x-auto">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-200">Execution Latency Heatmap (ms)</h3>
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500/40 rounded-sm"></div>
            <span className="text-gray-400">&lt; 50ms</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-yellow-500/40 rounded-sm"></div>
            <span className="text-gray-400">50-150ms</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-500/40 rounded-sm"></div>
            <span className="text-gray-400">&gt; 300ms</span>
          </div>
        </div>
      </div>

      <div className="min-w-[800px]">
        {/* Header (Hours) */}
        <div className="grid grid-cols-[100px_repeat(24,1fr)] mb-2">
          <div className="text-xs text-gray-500 font-medium">Symbol</div>
          {hours.map((h) => (
            <div key={h} className="text-[10px] text-gray-500 text-center">
              {h}h
            </div>
          ))}
        </div>

        {/* Rows (Symbols) */}
        <div className="space-y-1">
          {symbols.map((symbol) => (
            <div key={symbol} className="grid grid-cols-[100px_repeat(24,1fr)] items-center">
              <div className="text-xs font-mono text-gray-300 truncate pr-2">{symbol}</div>
              {hours.map((hour) => {
                const latency = gridData[symbol]?.[hour];
                return (
                  <div
                    key={hour}
                    className={`h-6 border border-gray-900/50 flex items-center justify-center group relative ${
                      latency ? getLatencyColor(latency) : 'bg-gray-900/20'
                    }`}
                  >
                    {latency && (
                      <div className="opacity-0 group-hover:opacity-100 absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-800 text-[10px] text-white px-2 py-1 rounded shadow-lg z-10 whitespace-nowrap pointer-events-none transition-opacity">
                        {latency.toFixed(1)} ms
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
