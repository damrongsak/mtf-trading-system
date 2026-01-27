"use client";

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { format, parseISO } from 'date-fns';

interface SignalChartProps {
  data: number[];
  timestamps: string[];
}

const SignalChart = ({ data, timestamps }: SignalChartProps) => {
  // Combine signal and timestamps for Recharts
  const chartData = timestamps.map((ts, i) => ({
    timestamp: ts,
    value: data[i],
    // For tooltip formatting
    formattedTime: format(parseISO(ts), 'MMM d, HH:mm')
  }));

  return (
    <div className="w-full h-full min-h-[200px] bg-slate-950/50 rounded-lg p-2 border border-slate-800">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis 
            dataKey="timestamp" 
            hide 
          />
          <YAxis 
            domain={['auto', 'auto']}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
            itemStyle={{ color: '#60a5fa' }}
            labelStyle={{ display: 'none' }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any, name: any, props: any) => [
                typeof value === 'number' ? value.toFixed(4) : 'N/A', 
                `Signal (${props.payload.formattedTime})`
            ]}
          />
          <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke="#3b82f6" 
            strokeWidth={2} 
            dot={false}
            activeDot={{ r: 4, fill: '#3b82f6' }}
            animationDuration={1000}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SignalChart;
