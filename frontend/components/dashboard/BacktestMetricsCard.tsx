'use client';

import React from 'react';
import { BacktestMetrics } from '@/lib/api/types';
import { TrendingUp, Shield, Activity, BarChart2, Target, Percent } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface BacktestMetricsCardProps {
    metrics: BacktestMetrics;
}

export function BacktestMetricsCard({ metrics }: BacktestMetricsCardProps) {
    const formatPercent = (val: number) => `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
    const formatNumber = (val: number | undefined, decimals = 2) => val?.toFixed(decimals) ?? 'N/A';
    
    // Helper for color coding returns/alpha
    const getColor = (val: number | undefined) => {
        if (val === undefined) return 'text-slate-400';
        return val > 0 ? 'text-emerald-400' : val < 0 ? 'text-rose-400' : 'text-slate-400';
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {/* 1. Performance */}
            <Card className="bg-slate-950/50 border-slate-800 backdrop-blur-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-emerald-500" />
                        Performance
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex justify-between items-baseline">
                        <span className="text-sm text-slate-400">Total Return</span>
                        <div className="text-right">
                            <div className={`text-2xl font-bold ${getColor(metrics.total_return_percent)}`}>
                                {formatPercent(metrics.total_return_percent)}
                            </div>
                            <div className="text-xs text-slate-500">${metrics.total_return.toFixed(2)}</div>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800/50">
                         <div>
                            <span className="text-xs text-slate-500 block mb-1">Win Rate</span>
                            <span className={`text-lg font-mono ${metrics.win_rate >= 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                {metrics.win_rate.toFixed(1)}%
                            </span>
                         </div>
                         <div className="text-right">
                            <span className="text-xs text-slate-500 block mb-1">Total Trades</span>
                            <span className="text-lg font-mono text-slate-200">{metrics.total_trades}</span>
                         </div>
                    </div>
                </CardContent>
            </Card>

            {/* 2. Risk Profile */}
            <Card className="bg-slate-950/50 border-slate-800 backdrop-blur-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-2">
                        <Shield className="h-4 w-4 text-amber-500" />
                        Risk Profile
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                     <div className="flex justify-between items-baseline">
                        <span className="text-sm text-slate-400">Max Drawdown</span>
                        <div className="text-right">
                            <div className="text-2xl font-bold text-rose-400">
                                {metrics.max_drawdown_percent.toFixed(2)}%
                            </div>
                            <div className="text-xs text-slate-500">${Math.abs(metrics.max_drawdown).toFixed(2)}</div>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800/50">
                         <div>
                            <span className="text-xs text-slate-500 block mb-1">Sharpe Ratio</span>
                            <span className={`text-lg font-mono ${ (metrics.sharpe_ratio || 0) > 1.0 ? 'text-emerald-400' : 'text-slate-300' }`}>
                                {formatNumber(metrics.sharpe_ratio)}
                            </span>
                         </div>
                         <div className="text-right">
                            <span className="text-xs text-slate-500 block mb-1">Sortino Ratio</span>
                            <span className={`text-lg font-mono ${ (metrics.sortino_ratio || 0) > 1.5 ? 'text-emerald-400' : 'text-slate-300' }`}>
                                {formatNumber(metrics.sortino_ratio)}
                            </span>
                         </div>
                    </div>
                </CardContent>
            </Card>

            {/* 3. Benchmark Comparison */}
            <Card className="bg-slate-950/50 border-slate-800 backdrop-blur-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-2">
                        <Activity className="h-4 w-4 text-blue-500" />
                        Vs XAU/USD
                    </CardTitle>
                </CardHeader>
                 <CardContent className="space-y-4">
                     <div className="flex justify-between items-baseline">
                        <span className="text-sm text-slate-400">Benchmark Return</span>
                        <div className="text-right">
                             <div className={`text-2xl font-bold ${getColor(metrics.benchmark_return)}`}>
                                {formatPercent(metrics.benchmark_return || 0)}
                            </div>
                        </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/50">
                         <div>
                            <span className="text-xs text-slate-500 block mb-1">Alpha</span>
                            <span className={`text-lg font-mono ${getColor(metrics.alpha)}`}>
                                {formatNumber(metrics.alpha, 4)}
                            </span>
                         </div>
                         <div className="text-center">
                            <span className="text-xs text-slate-500 block mb-1">Beta</span>
                            <span className="text-lg font-mono text-slate-300">
                                {formatNumber(metrics.beta)}
                            </span>
                         </div>
                         <div className="text-right">
                            <span className="text-xs text-slate-500 block mb-1">Info Ratio</span>
                            <span className="text-lg font-mono text-slate-300">
                                {formatNumber(metrics.information_ratio)}
                            </span>
                         </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
