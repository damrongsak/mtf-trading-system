'use client';

import React from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';

interface EquityPoint {
  date: string;
  equity: number;
  daily_pnl: number;
}

interface EquityChartProps {
  data: EquityPoint[];
  loading?: boolean;
}

const TOOLTIP_CONTENT_STYLE = { 
  backgroundColor: '#1f2937', 
  borderColor: '#374151',
  color: '#f3f4f6'
};

const TOOLTIP_ITEM_STYLE = { color: '#60a5fa' };

const formatCurrency = (value: number) => `$${value.toFixed(0)}`;
const formatTooltipValue = (value: number) => [`$${value.toFixed(2)}`, 'Equity'];
const formatTooltipLabel = (label: string) => new Date(label).toLocaleDateString();
const formatXAxisDate = (value: string) => {
    const date = new Date(value);
    return `${date.getMonth() + 1}/${date.getDate()}`;
};

export const EquityChart = React.memo(function EquityChart({ data, loading }: EquityChartProps) {
  if (loading) {
    return (
      <div className="h-[300px] w-full bg-gray-800/30 rounded-xl animate-pulse flex items-center justify-center">
        <span className="text-gray-500">Loading chart data...</span>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-[300px] w-full bg-gray-800/30 rounded-xl flex items-center justify-center border border-gray-800">
        <div className="text-center">
          <p className="text-gray-400 mb-2">No equity data available</p>
          <p className="text-xs text-gray-500">Complete some trades to see your performance curve</p>
        </div>
      </div>
    );
  }

  // Calculate min/max for Y-axis scaling
  const minEquity = Math.min(...data.map(d => d.equity));
  const maxEquity = Math.max(...data.map(d => d.equity));
  const padding = (maxEquity - minEquity) * 0.1;

  return (
    <div className="w-full h-[300px] bg-gray-900/50 rounded-xl border border-gray-800 p-4">
      <h3 className="text-lg font-semibold text-gray-200 mb-4">Equity Curve</h3>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#9ca3af" 
            tick={{ fontSize: 12 }}
            tickFormatter={formatXAxisDate}
          />
          <YAxis 
            stroke="#9ca3af" 
            tick={{ fontSize: 12 }}
            domain={[minEquity - padding, maxEquity + padding]}
            tickFormatter={formatCurrency}
          />
          <Tooltip
            contentStyle={TOOLTIP_CONTENT_STYLE}
            itemStyle={TOOLTIP_ITEM_STYLE}
            formatter={formatTooltipValue}
            labelFormatter={formatTooltipLabel}
          />
          <Area 
            type="monotone" 
            dataKey="equity" 
            stroke="#3b82f6" 
            strokeWidth={2}
            fillOpacity={1} 
            fill="url(#colorEquity)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}, (prevProps, nextProps) => {
    // Custom comparison to ensure we don't re-render unless necessary
    return prevProps.loading === nextProps.loading && 
           prevProps.data === nextProps.data; 
           // Note: assumes data reference changes on update, which it does from DashboardPage state setter
});
