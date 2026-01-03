'use client';

import React, { useState } from 'react';
import { BacktestConfigForm } from '@/components/backtest/BacktestConfigForm';
import { BacktestResults } from '@/components/backtest/BacktestResults';
import { runBacktest, BacktestRequest, BacktestResponse } from '@/lib/api/backtest';

import { DebugConsole, LogEntry } from '@/components/backtest/DebugConsole';

export default function BacktestPage() {
    const [results, setResults] = useState<BacktestResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState<LogEntry[]>([]);

    const addLog = (message: string, type: LogEntry['type'] = 'info') => {
        setLogs(prev => [...prev, { timestamp: new Date(), message, type }]);
    };

    const handleRun = async (config: BacktestRequest) => {
        setLoading(true);
        setResults(null);
        setLogs([]); // Clear previous logs
        
        addLog(`Starting backtest for ${config.symbol} on ${config.timeframe}...`, 'info');
        addLog(`Date Range: ${config.start_date} to ${config.end_date}`, 'info');
        addLog(`Initial Capital: $${config.initial_capital}`, 'info');

        try {
            const startTime = Date.now();
            const data = await runBacktest(config);
            const duration = ((Date.now() - startTime) / 1000).toFixed(2);
            
            setResults(data);
            
            if (data.status === 'COMPLETED') {
                addLog(`Backtest completed in ${duration}s`, 'success');
                addLog(`Total Return: ${data.metrics?.total_return_percent.toFixed(2)}%`, 'success');
                addLog(`Total Trades: ${data.metrics?.total_trades}`, 'info');
            } else {
                addLog(`Backtest finished with status: ${data.status}`, 'warning');
            }
        } catch (error) {
            console.error("Backtest failed", error);
            const msg = error instanceof Error ? error.message : 'Unknown error occurred';
            addLog(`Error: ${msg}`, 'error');
            alert("Backtest failed. Check console.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 h-[calc(100vh-4rem)] flex gap-6">
            {/* Sidebar Configuration */}
            <div className="w-[350px] flex-shrink-0 flex flex-col gap-4 overflow-hidden">
                <div className="overflow-y-auto flex-1">
                    <BacktestConfigForm onRun={handleRun} loading={loading} />
                </div>
                <div className="h-[250px] flex-shrink-0">
                    <DebugConsole logs={logs} className="h-full" />
                </div>
            </div>

            {/* Main Results Area */}
            <div className="flex-1 overflow-y-auto pr-2">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
                        Backtest Engine
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Validate strategies against historical data using Vectorbt.
                    </p>
                </div>
                
                <BacktestResults results={results} />
            </div>
        </div>
    );
}
