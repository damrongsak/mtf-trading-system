'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell
} from 'recharts';
import { PerformanceComparisonItem } from '@/lib/api/types';

interface PerformanceGapChartProps {
  data: PerformanceComparisonItem[];
  loading?: boolean;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-gray-900/90 border border-gray-700 p-3 rounded-lg shadow-xl backdrop-blur-sm">
        <p className="text-gray-200 font-mono text-xs mb-2">Signal: {label.substring(0, 8)}</p>
        <div className="space-y-1">
          <div className="flex justify-between gap-4">
            <span className="text-gray-400 text-xs">Symbol:</span>
            <span className="text-gray-200 text-xs font-semibold">{data.symbol}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-gray-400 text-xs">Slippage:</span>
            <span className={`text-xs font-semibold ${data.slippage_usd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${data.slippage_usd?.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-gray-400 text-xs">Latency Gap:</span>
            <span className="text-gray-200 text-xs font-semibold">{data.latency_gap_ms?.toFixed(1)} ms</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export const PerformanceGapChart: React.FC<PerformanceGapChartProps> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="h-[300px] w-full bg-gray-950/50 rounded-xl border border-gray-800 animate-pulse flex items-center justify-center">
        <span className="text-gray-500">Loading comparison data...</span>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="h-[300px] w-full bg-gray-950/50 rounded-xl border border-gray-800 flex items-center justify-center">
        <span className="text-gray-400">No performance comparison data available.</span>
      </div>
    );
  }

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-gray-200 mb-6">Execution Quality (Shadow vs Live Slippage)</h3>
      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
            <XAxis 
              dataKey="signal_id" 
              hide 
            />
            <YAxis 
              stroke="#9ca3af" 
              tick={{ fontSize: 10 }}
              tickFormatter={(val) => `$${val}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="#4B5563" />
            <Bar dataKey="slippage_usd">
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.slippage_usd && entry.slippage_usd >= 0 ? '#10b981' : '#ef4444'} 
                  fillOpacity={0.6}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-gray-500 mt-4 text-center">
        Positive values indicate better-than-shadow execution (rare), negative values indicate slippage.
      </p>
    </div>
  );
};
