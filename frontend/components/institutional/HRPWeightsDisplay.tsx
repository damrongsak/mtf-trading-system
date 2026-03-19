'use client';

import React, { useState } from 'react';
import {
    PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
    BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';
import { LayoutGrid, BarChart2 } from 'lucide-react';

interface HRPWeightsDisplayProps {
    weights: Record<string, number>;
    loading?: boolean;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export const HRPWeightsDisplay: React.FC<HRPWeightsDisplayProps> = ({ weights, loading }) => {
    const [view, setView] = useState<'pie' | 'bar'>('pie');

    const data = Object.entries(weights)
        .map(([name, value]) => ({
            name,
            value: parseFloat((value * 100).toFixed(2)),
        }))
        .sort((a, b) => b.value - a.value);

    if (loading) {
        return (
            <div className="h-[350px] w-full bg-gray-950/50 rounded-xl border border-gray-800 animate-pulse flex items-center justify-center">
                <span className="text-gray-500 font-medium">Loading risk weights...</span>
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div className="h-[350px] w-full bg-gray-950/50 rounded-xl border border-gray-800 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-12 h-12 bg-gray-900 rounded-full flex items-center justify-center mb-4">
                    <span className="text-gray-600 text-xl font-bold">!</span>
                </div>
                <h4 className="text-gray-300 font-semibold mb-1">No Risk Parity Data</h4>
                <p className="text-gray-500 text-xs">Risk Parity may be disabled for this fund or no active strategies found.</p>
            </div>
        );
    }

    const maxValue = Math.max(...data.map(d => d.value));

    return (
        <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 h-full flex flex-col">
            <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold text-gray-200">HRP Risk Allocation</h3>
                {/* View Toggle */}
                <div className="flex items-center gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
                    <button
                        onClick={() => setView('pie')}
                        className={`p-1.5 rounded transition-colors ${view === 'pie' ? 'bg-accent-blue/20 text-accent-blue' : 'text-gray-500 hover:text-gray-300'}`}
                        title="Pie view"
                    >
                        <LayoutGrid className="w-3.5 h-3.5" />
                    </button>
                    <button
                        onClick={() => setView('bar')}
                        className={`p-1.5 rounded transition-colors ${view === 'bar' ? 'bg-accent-blue/20 text-accent-blue' : 'text-gray-500 hover:text-gray-300'}`}
                        title="Bar view"
                    >
                        <BarChart2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>
            <p className="text-[10px] text-gray-500 mb-4 uppercase tracking-wider">Strategy Weights (%)</p>

            <div className="flex-1 min-h-[200px]">
                {view === 'pie' ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                cx="50%"
                                cy="50%"
                                innerRadius={55}
                                outerRadius={75}
                                paddingAngle={4}
                                dataKey="value"
                            >
                                {data.map((_, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="transparent" />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
                                itemStyle={{ color: '#f3f4f6', fontSize: '12px' }}
                                formatter={(v: number) => [`${v}%`, 'Weight']}
                            />
                            <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '10px', color: '#9ca3af' }} />
                        </PieChart>
                    </ResponsiveContainer>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 20, top: 4, bottom: 4 }}>
                            <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="rgba(75,85,99,0.2)" />
                            <XAxis
                                type="number"
                                domain={[0, Math.ceil(maxValue * 1.1)]}
                                tick={{ fontSize: 9, fill: '#6b7280' }}
                                tickFormatter={(v) => `${v}%`}
                            />
                            <YAxis
                                type="category"
                                dataKey="name"
                                tick={{ fontSize: 9, fill: '#9ca3af' }}
                                width={80}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
                                formatter={(v: number) => [`${v}%`, 'Weight']}
                            />
                            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                                {data.map((_, index) => (
                                    <Cell key={`bar-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                )}
            </div>

            {/* Ranked Summary */}
            <div className="mt-4 pt-4 border-t border-gray-800 space-y-1.5">
                {data.slice(0, 4).map((item, idx) => (
                    <div key={item.name} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="text-[9px] text-gray-600 w-4 text-right font-mono">#{idx + 1}</span>
                            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                            <span className="text-[10px] text-gray-500 truncate max-w-[100px]">{item.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            {/* Weight bar */}
                            <div className="w-16 h-1 bg-gray-800 rounded-full overflow-hidden">
                                <div
                                    className="h-full rounded-full"
                                    style={{
                                        width: `${(item.value / maxValue) * 100}%`,
                                        backgroundColor: COLORS[idx % COLORS.length]
                                    }}
                                />
                            </div>
                            <span className="text-xs font-bold text-gray-200 font-mono w-10 text-right">{item.value}%</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
