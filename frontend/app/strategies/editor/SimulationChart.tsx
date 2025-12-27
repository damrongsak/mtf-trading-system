import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

interface SimulationChartProps {
    equityCurves?: number[][];
}

export function SimulationChart({ equityCurves }: SimulationChartProps) {
    if (!equityCurves || equityCurves.length === 0) {
        return (
            <div className="flex h-full items-center justify-center text-slate-500">
                No simulation data available. Run Monte Carlo simulation first.
            </div>
        );
    }

    // Transform data for Recharts
    // We need an array of objects where each object represents a time step (index)
    // and keys are like 'sim0', 'sim1', etc.
    // Assuming all curves have roughly same length (n_trades + 1)
    
    // Find max length
    const maxLength = Math.max(...equityCurves.map(c => c.length));
    
    const chartData = Array.from({ length: maxLength }, (_, i) => {
        const point: Record<string, number> = { index: i };
        equityCurves.forEach((curve, simIdx) => {
            if (i < curve.length) {
                // Convert to percentage return (1.0 = 0%)
                point[`sim${simIdx}`] = (curve[i] - 1.0) * 100; 
            }
        });
        return point;
    });

    return (
        <Card className="h-full bg-slate-950 border-slate-800 flex flex-col">
            <CardHeader className="py-2 px-4 border-b border-slate-800">
                <CardTitle className="text-sm font-medium text-slate-400">
                    Monte Carlo Scenarios ({equityCurves.length} runs sampled)
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px] p-2">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                        <XAxis 
                            dataKey="index" 
                            stroke="#64748b" 
                            fontSize={12} 
                            tickLine={false}
                            axisLine={false}
                            label={{ value: 'Trades', position: 'insideBottomRight', offset: -5 }}
                        />
                        <YAxis 
                            stroke="#64748b" 
                            fontSize={12} 
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(val) => `${val.toFixed(0)}%`}
                            width={40}
                        />
                        <Tooltip 
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', fontSize: '12px' }}
                            itemStyle={{ color: '#94a3b8' }}
                            labelStyle={{ color: '#e2e8f0' }}
                            formatter={(value: number) => [`${value.toFixed(2)}%`, 'Return']}
                            labelFormatter={(label) => `Trade #${label}`}
                        />
                        {/* Render lines for each simulation */}
                        {equityCurves.map((_, idx) => (
                            <Line 
                                key={`sim${idx}`}
                                type="monotone" 
                                dataKey={`sim${idx}`} 
                                stroke={idx === 0 ? '#10b981' : '#6366f1'} // Highlight first one, others purple
                                strokeWidth={1}
                                strokeOpacity={0.3}
                                dot={false}
                                activeDot={false}
                                isAnimationActive={false} // Disable animation for performance with many lines
                            />
                        ))}
                        {/* Add a zero line */}
                         <Line 
                            dataKey={() => 0} 
                            stroke="#94a3b8" 
                            strokeDasharray="3 3" 
                            strokeWidth={1} 
                            dot={false} 
                            activeDot={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
