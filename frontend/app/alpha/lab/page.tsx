"use client";

import React from 'react';
import AlphaEditor from '@/components/alpha/MonacoEditor';
import FeatureMatrix from '@/components/alpha/FeatureMatrix';
import { useAlphaStore } from '@/lib/stores/useAlphaStore';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Play } from 'lucide-react';

const AlphaLabPage = () => {
    const { runAlpha, isRunning, result, error } = useAlphaStore();

    return (
        <div className="h-[calc(100vh-4rem)] p-4 gap-4 grid grid-cols-12 grid-rows-6">
            {/* Header / Toolbar - Span 12, Row 1 (Auto height) */}
            <div className="col-span-12 row-span-1 flex items-center justify-between bg-slate-900/50 p-4 rounded-lg border border-slate-800">
                <div>
                     <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Athena Alpha Lab</h1>
                     <p className="text-slate-400 text-sm">Design, Backtest, and Deploy Statistical Alpha</p>
                </div>
                <Button 
                    onClick={() => runAlpha('full')} 
                    disabled={isRunning}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-6"
                >
                    <Play className="w-4 h-4 mr-2" />
                    {isRunning ? 'Running...' : 'Run Backtest'}
                </Button>
            </div>

            {/* Editor Area - Span 8, Rows 2-4 */}
            <div className="col-span-8 row-span-3">
                <AlphaEditor />
            </div>

            {/* Sidebar / Feature Matrix - Span 4, Rows 2-6 */}
            <div className="col-span-4 row-span-5">
                <FeatureMatrix />
            </div>

            {/* Metrics / Results - Span 8, Rows 5-6 */}
            <div className="col-span-8 row-span-2">
                <Card className="h-full bg-slate-900 border-slate-800 p-4">
                    <h3 className="text-sm font-semibold text-slate-400 mb-2 uppercase">Backtest Results</h3>
                    
                    {error && (
                        <div className="p-4 bg-red-900/20 text-red-400 rounded border border-red-900/50 font-mono">
                            Error: {error}
                        </div>
                    )}
                    
                    {result && !error && (
                         <div className="grid grid-cols-4 gap-4">
                            <MetricCard label="Sharpe Ratio" value={result.metrics.sharpe?.toFixed(2) ?? '-'} color="text-blue-400" />
                            <MetricCard label="Information Coeff (IC)" value={result.metrics.ic?.toFixed(3) ?? '-'} color="text-purple-400" />
                            <MetricCard label="Turnover" value={result.metrics.turnover?.toFixed(2) ?? '-'} />
                            <MetricCard label="Total Return" value={result.metrics.total_return ? `${(result.metrics.total_return * 100).toFixed(1)}%` : '-'} color="text-green-400" />
                        
                            {/* Simple Sparkline Placeholder for signal series */}
                            <div className="col-span-4 mt-4 h-24 bg-slate-950/50 rounded flex items-center justify-center border border-slate-800 border-dashed">
                                <span className="text-slate-500 text-sm">Signal/Equity Curve Visualization (Coming Phase 3)</span>
                            </div>
                        </div>
                    )}

                    {!result && !error && (
                        <div className="h-full flex items-center justify-center text-slate-600">
                            Run a strategy to see metrics
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
};

const MetricCard = ({ label, value, color = 'text-white' }: { label: string, value: string, color?: string }) => (
    <div className="bg-slate-950 p-3 rounded border border-slate-800">
        <div className="text-xs text-slate-500 mb-1">{label}</div>
        <div className={`text-xl font-bold font-mono ${color}`}>{value}</div>
    </div>
);

export default AlphaLabPage;
