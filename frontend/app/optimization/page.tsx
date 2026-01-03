'use client';

import React, { useState } from 'react';
import { OptimizationConfigForm } from '@/components/optimization/OptimizationConfigForm';
import { OptimizationResults } from '@/components/optimization/OptimizationResults';
import { runOptimization, OptimizationResponse } from '@/lib/api/optimization';
import { BacktestRequest } from '@/lib/api/backtest';
import { DebugConsole, LogEntry } from '@/components/backtest/DebugConsole';

export default function OptimizationPage() {
    const [results, setResults] = useState<OptimizationResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState<LogEntry[]>([]);

    const addLog = (message: string, type: LogEntry['type'] = 'info') => {
        setLogs(prev => [...prev, { timestamp: new Date(), message, type }]);
    };

    const handleRun = async (config: BacktestRequest) => {
        setLoading(true);
        setResults(null);
        setLogs([]);
        
        addLog(`Starting Grid Search for ${config.symbol}...`, 'info');
        if (config.optimization?.param_grid) {
             // const grid = config.optimization.param_grid;
             // Rough estimate
             // addLog(`Grid: Fast [${grid.fast_window}] Slow [${grid.slow_window}]`, 'info'); 
        }

        try {
            const startTime = Date.now();
            const data = await runOptimization(config);
            const duration = ((Date.now() - startTime) / 1000).toFixed(2);
            
            setResults(data);
            addLog(`Optimization completed in ${duration}s`, 'success');
            addLog(`Found ${data.results.length} results. Top Sharpe: ${data.results[0]?.metrics.sharpe_ratio?.toFixed(2)}`, 'success');
            
        } catch (error: unknown) {
            console.error("Optimization failed", error);
            addLog(`Error: ${(error as Error).message || 'Unknown error occurred'}`, 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 h-[calc(100vh-4rem)] flex gap-6">
            {/* Sidebar Configuration */}
            <div className="w-[350px] flex-shrink-0 flex flex-col gap-4 overflow-hidden">
                <div className="overflow-y-auto flex-1">
                    <OptimizationConfigForm onRun={handleRun} loading={loading} />
                </div>
                <div className="h-[250px] flex-shrink-0">
                    <DebugConsole logs={logs} className="h-full" />
                </div>
            </div>

            {/* Main Results Area */}
            <div className="flex-1 overflow-y-auto pr-2">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent">
                        Strategy Optimization
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Find the optimal parameters using Grid Search.
                    </p>
                </div>
                
                <OptimizationResults results={results ? results.results : null} />
            </div>
        </div>
    );
}
