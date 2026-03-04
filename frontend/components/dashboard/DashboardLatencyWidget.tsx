"use client";

import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Zap, Activity, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

interface TraceStep {
  step: string;
  duration_ms: number;
}

interface TraceData {
  trace_id: string;
  steps: TraceStep[];
  total_ms: number;
}

export const DashboardLatencyWidget: React.FC = () => {
  const [currentTrace, setCurrentTrace] = useState<TraceData | null>(null);
  const [history, setHistory] = useState<TraceData[]>([]);

  useEffect(() => {
    const eventSource = new EventSource('/api/v1/execution/traces/stream');

    eventSource.onmessage = (event) => {
      try {
        const rawData = JSON.parse(event.data);
        const { trace_id, step, duration_ms } = rawData;

        setCurrentTrace((prev) => {
          if (prev?.trace_id === trace_id) {
            const updatedSteps = [...prev.steps, { step, duration_ms }];
            return {
              ...prev,
              steps: updatedSteps,
              total_ms: updatedSteps.reduce((acc, s) => acc + s.duration_ms, 0),
            };
          } else {
            // New trace started
            if (prev) {
              setHistory((h) => [prev, ...h].slice(0, 5));
            }
            return {
              trace_id,
              steps: [{ step, duration_ms }],
              total_ms: duration_ms,
            };
          }
        });
      } catch (err) {
        console.error('Failed to parse trace data', err);
      }
    };

    return () => eventSource.close();
  }, []);

  const getBarColor = (duration: number) => {
    if (duration < 10) return '#10b981'; // Emerald
    if (duration < 50) return '#3b82f6'; // Blue
    return '#f59e0b'; // Amber
  };

  return (
    <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-md overflow-hidden">
      <CardHeader className="pb-2 border-b border-slate-800/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-500 fill-yellow-500" />
            Live Execution Latency (HFT-lite)
          </CardTitle>
          {currentTrace && (
            <div className="flex items-center gap-2">
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                currentTrace.total_ms < 100 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
              }`}>
                {currentTrace.total_ms.toFixed(2)}ms
              </span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-4 h-[200px]">
        {currentTrace ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={currentTrace.steps}>
              <XAxis 
                dataKey="step" 
                hide 
              />
              <YAxis 
                hide 
                domain={[0, 'auto']} 
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                itemStyle={{ color: '#94a3b8', fontSize: '12px' }}
                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                labelStyle={{ display: 'none' }}
                formatter={(value: number, name: string, props: any) => [
                  `${value.toFixed(2)}ms`, 
                  props.payload.step.replace(/_/g, ' ')
                ]}
              />
              <Bar dataKey="duration_ms">
                {currentTrace.steps.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(entry.duration_ms)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-2">
            <Activity className="w-8 h-8 animate-pulse text-slate-700" />
            <span className="text-xs">Waiting for orders...</span>
          </div>
        )}
      </CardContent>
      {currentTrace && (
        <div className="px-4 pb-3 flex items-center justify-between text-[10px] text-slate-500">
            <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Latest Trace: {currentTrace.trace_id.split(':').pop()}
            </div>
            <div className="flex gap-2">
                <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500"/> Fast</span>
                <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-blue-500"/> Normal</span>
            </div>
        </div>
      )}
    </Card>
  );
};
