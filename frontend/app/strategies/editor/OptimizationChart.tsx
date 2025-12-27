import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import { OptimizationResult } from '@/lib/api/types';

interface OptimizationChartProps {
    results?: OptimizationResult[];
}

export function OptimizationChart({ results }: OptimizationChartProps) {
    if (!results || results.length === 0) {
        return (
            <div className="flex h-full items-center justify-center text-slate-500">
                No optimization results available. Run optimization first.
            </div>
        );
    }

    // Determine parameters to plot
    // We'll pick the first two numeric parameters found in the results for X and Y axis
    // If only one param, we use it for X and Sharpe for Y
    const sample = results[0];
    const paramKeys = Object.keys(sample.params).filter(k => typeof sample.params[k] === 'number');

    let xKey = 'param1';
    let yKey = 'sharpe';
    let xLabel = 'Parameter 1';
    let yLabel = 'Sharpe Ratio';

    const data = results.map((r, idx) => {
        const item: Record<string, unknown> = { 
            id: idx,
            sharpe: r.metrics.sharpe_ratio,
            return: r.metrics.total_return_percent,
            ...r.params 
        };
        return item;
    });

    if (paramKeys.length >= 2) {
        xKey = paramKeys[0];
        yKey = paramKeys[1];
        xLabel = xKey;
        yLabel = yKey;
    } else if (paramKeys.length === 1) {
        xKey = paramKeys[0];
        xLabel = xKey;
        yLabel = 'Sharpe Ratio';
    }

    // Sort data for better visualization if needed, but scatter doesn't strictly need it
    
    return (
        <Card className="h-full bg-slate-950 border-slate-800 flex flex-col">
            <CardHeader className="py-2 px-4 border-b border-slate-800">
                <CardTitle className="text-sm font-medium text-slate-400">
                    Optimization Landscape ({xLabel} vs {yLabel})
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px] p-2">
                <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                        <XAxis 
                            type="number" 
                            dataKey={xKey} 
                            name={xLabel} 
                            stroke="#64748b" 
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                            label={{ value: xLabel, position: 'insideBottom', offset: -10, fill: '#94a3b8' }}
                        />
                        <YAxis 
                            type="number" 
                            dataKey={yKey} 
                            name={yLabel} 
                            stroke="#64748b" 
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                            label={{ value: yLabel, angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
                        />
                        <ZAxis type="number" dataKey="sharpe" range={[50, 400]} name="Sharpe Ratio" />
                        <Tooltip 
                            cursor={{ strokeDasharray: '3 3' }}
                            content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                    const data = payload[0].payload;
                                    return (
                                        <div className="bg-slate-900 border border-slate-700 p-2 rounded shadow-xl text-xs">
                                            <p className="font-bold text-slate-200 mb-1">Result #{data.index}</p>
                                            {Object.keys(data).map(key => {
                                                if (key === 'id' || key === 'index') return null;
                                                return (
                                                    <div key={key} className="flex justify-between gap-4">
                                                        <span className="text-slate-500 capitalize">{key}:</span>
                                                        <span className="text-emerald-400 font-mono">
                                                            {typeof data[key] === 'number' ? data[key].toFixed(4) : data[key]}
                                                        </span>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <Scatter 
                            name="Results" 
                            data={data} 
                            fill="#10b981" 
                            shape="circle"
                        />
                    </ScatterChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
