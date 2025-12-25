"use client";

import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Play, Save, Terminal, Loader2, Settings2, Trash2, Copy, Check } from 'lucide-react';
import { runCustomBacktest } from '@/lib/api/backtest';
import { getPreferences } from '@/lib/api/settings';
import { UserPreferences } from '@/lib/api/types';

// Map frontend/legacy timeframes to backend standard (DB uses uppercase)
const TIMEFRAME_MAP: Record<string, string> = {
    '1m': 'M1', 'm1': 'M1',
    '5m': 'M5', 'm5': 'M5',
    '15m': 'M15', 'm15': 'M15',
    '30m': 'M30', 'm30': 'M30',
    '1h': 'H1', 'h1': 'H1',
    '4h': 'H4', 'h4': 'H4',
    '1d': 'D', 'd': 'D',
    '1w': 'W', 'w': 'W',
    '1mn': 'M', 'm': 'M', 'M': 'M'
};

const NORMALIZE_TF = (tf: string) => TIMEFRAME_MAP[tf.toLowerCase()] || tf.toUpperCase();

const DEFAULT_CODE = `import vectorbt as vbt
import pandas as pd
import numpy as np

def strategy(data):
    """
    Vectorized Strategy
    data: pd.DataFrame with columns: open, high, low, close, volume (lowercase)
    Returns: entries, exits (boolean pd.Series)
    """
    # data index is datetime
    close = data['close']
    
    # 1. Calculate Indicators
    fast_ma = vbt.MA.run(close, 10, short_name='fast')
    slow_ma = vbt.MA.run(close, 20, short_name='slow')
    
    # 2. Generate Signals
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    
    return entries, exits
`;

export default function StrategyEditor() {
    interface LogEntry {
        id: string;
        timestamp: Date;
        level: 'INFO' | 'DEBUG' | 'ERROR' | 'SUCCESS';
        message: string;
    }

    const [code, setCode] = useState(DEFAULT_CODE);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isRunning, setIsRunning] = useState(false);
    const [title, setTitle] = useState("My Custom Strategy");
    const [isConfigOpen, setIsConfigOpen] = useState(true);
    const [isCopied, setIsCopied] = useState(false);

    // Configuration State
    const [preferences, setPreferences] = useState<UserPreferences | null>(null);
    const [symbol, setSymbol] = useState("XAU_USD");
    const [timeframe, setTimeframe] = useState("H1");
    const [startDate, setStartDate] = useState(new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
    const [initialCapital, setInitialCapital] = useState(10000);
    const [fees, setFees] = useState(0.0001);
    const [slippage, setSlippage] = useState(0.0001);

    useEffect(() => {
        const fetchPreferences = async () => {
            try {
                const prefs = await getPreferences();
                setPreferences(prefs);
                if (prefs.default_symbol) {
                     // Normalize symbol XAU/USD -> XAU_USD
                     setSymbol(prefs.default_symbol.replace('/', '_'));
                }
                if (prefs.preferred_timeframes && prefs.preferred_timeframes.length > 0) {
                    setTimeframe(NORMALIZE_TF(prefs.preferred_timeframes[0]));
                }
            } catch (error) {
                console.error("Failed to fetch preferences:", error);
            }
        };
        fetchPreferences();
    }, []);

    const addLog = (level: LogEntry['level'], message: string) => {
        setLogs(prev => [{
            id: Math.random().toString(36).substring(7),
            timestamp: new Date(),
            level,
            message
        }, ...prev]);
    };

    const handleRun = async () => {
        setIsRunning(true);
        addLog('INFO', "Starting backtest simulation...");
        addLog('DEBUG', `Parameters: ${symbol} | ${timeframe} | ${startDate} to ${endDate}`);
        addLog('DEBUG', `Capital: $${initialCapital} | Fees: ${fees} | Slippage: ${slippage}`);
        
        try {
            // Validate dates
            if (!startDate || !endDate) {
                throw new Error("Please select both start and end dates.");
            }

            const payload = {
                code: code,
                symbol: symbol,
                timeframe: timeframe,
                // Append time to ensure valid ISO 8601 for backend
                start_date: new Date(startDate).toISOString(), 
                end_date: new Date(endDate).toISOString(),
                initial_capital: initialCapital,
                fees: fees,
                slippage: slippage
            };

            addLog('INFO', "Sending code to server...");
            addLog('DEBUG', `Request Payload: ${JSON.stringify(payload)}`);

            const res = await runCustomBacktest(payload);
            
            addLog('SUCCESS', "Backtest Complete!");
            addLog('INFO', `----------------------------------------`);
            addLog('INFO', `Total Return: $${res.metrics.total_return.toFixed(2)} (${res.metrics.total_return_percent.toFixed(2)}%)`);
            addLog('INFO', `Win Rate:     ${res.metrics.win_rate.toFixed(1)}%`);
            addLog('INFO', `Sharpe Ratio: ${res.metrics.sharpe_ratio?.toFixed(2)}`);
            addLog('INFO', `Max Drawdown: $${res.metrics.max_drawdown.toFixed(2)} (${res.metrics.max_drawdown_percent.toFixed(2)}%)`);
            addLog('INFO', `Total Trades: ${res.metrics.total_trades} (W: ${res.metrics.winning_trades} / L: ${res.metrics.losing_trades})`);
            addLog('INFO', `Data Points:  ${res.metrics.candle_count || 0}`);
            addLog('INFO', `----------------------------------------`);
            addLog('DEBUG', `Server Response ID: ${res.id} | Status: ${res.status}`);
            
            if (res.trades && res.trades.length > 0) {
                 const lastTrade = res.trades[res.trades.length - 1];
                 addLog('INFO', `Last Trade: ${lastTrade.direction} @ ${lastTrade.entry_price.toFixed(4)} (${lastTrade.exit_time})`);
            }
            
        } catch (error) {

            addLog('ERROR', `Execution failed: ${(error as any).message || error}`);
        } finally {
            setIsRunning(false);
        }
    };

    const handleSave = async () => {
        alert("Save functionality coming in next backend update!");
    };

    const handleClearLogs = () => {
        setLogs([]);
    };

    const handleCopyLogs = () => {
        const text = logs.map(l => `[${l.timestamp.toISOString()}] [${l.level}] ${l.message}`).join('\n');
        navigator.clipboard.writeText(text);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    return (
        <div className="container mx-auto p-4 space-y-4 text-slate-100 h-[calc(100vh-4rem)] flex flex-col">
            {/* Header */}
            <div className="flex justify-between items-center bg-slate-950/50 p-4 rounded-xl border border-slate-800 backdrop-blur-sm">
                <div>
                     <input 
                        type="text" 
                        value={title} 
                        onChange={(e) => setTitle(e.target.value)}
                        className="bg-transparent text-2xl font-bold text-emerald-400 focus:outline-none w-full placeholder-emerald-400/50"
                        placeholder="Strategy Name"
                    />
                    <p className="text-slate-400 text-sm">Write, test, and deploy custom Python algorithms.</p>
                </div>
                <div className="flex gap-3">
                     <Button 
                        onClick={() => setIsConfigOpen(!isConfigOpen)} 
                        variant="ghost" 
                        size="icon"
                        className={isConfigOpen ? "text-emerald-400 bg-emerald-400/10" : "text-slate-400"}
                    >
                        <Settings2 className="h-5 w-5" />
                    </Button>
                    <div className="h-8 w-[1px] bg-slate-700 mx-1" />
                    <Button onClick={handleRun} disabled={isRunning} variant="outline" className="gap-2 border-emerald-500/30 hover:bg-emerald-500/10 hover:text-emerald-400">
                        {isRunning ? <Loader2 className="animate-spin h-4 w-4" /> : <Play className="h-4 w-4" />}
                        Run Backtest
                    </Button>
                    <Button onClick={handleSave} className="gap-2 bg-emerald-600 hover:bg-emerald-700 shadow-lg shadow-emerald-900/20">
                        <Save className="h-4 w-4" />
                        Save
                    </Button>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex gap-4 min-h-0">
                {/* Editor & Output Column */}
                <div className="flex-1 flex flex-col gap-4 min-w-0">
                    <Card className="flex-1 bg-slate-900/50 border-slate-800 flex flex-col overflow-hidden backdrop-blur-sm">
                        <CardHeader className="py-2 px-4 border-b border-slate-800 bg-slate-950/30 flex flex-row items-center justify-between">
                            <span className="text-xs font-mono text-slate-500">main.py</span>
                        </CardHeader>
                        <CardContent className="p-0 flex-1 relative">
                            <Editor
                                height="100%"
                                defaultLanguage="python"
                                theme="vs-dark"
                                value={code}
                                onChange={(value) => setCode(value || "")}
                                options={{
                                    minimap: { enabled: false },
                                    fontSize: 14,
                                    scrollBeyondLastLine: false,
                                    padding: { top: 16 },
                                    fontFamily: 'JetBrains Mono, Menlo, Monaco, monospace',
                                }}
                            />
                        </CardContent>
                    </Card>

                    <Card className="h-48 bg-slate-950 border-slate-800 flex flex-col shrink-0">
                        <CardHeader className="py-2 px-4 border-b border-slate-800 bg-slate-900/50 flex flex-row items-center justify-between">
                            <CardTitle className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-400 font-medium">
                                <Terminal className="h-3.5 w-3.5" />
                                Console Output
                            </CardTitle>
                            <div className="flex gap-1">
                                <Button 
                                    variant="ghost" 
                                    size="icon" 
                                    className="h-6 w-6 text-slate-500 hover:text-emerald-400 hover:bg-emerald-400/10"
                                    onClick={handleCopyLogs}
                                    title="Copy Logs"
                                >
                                    {isCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                                </Button>
                                <Button 
                                    variant="ghost" 
                                    size="icon" 
                                    className="h-6 w-6 text-slate-500 hover:text-red-400 hover:bg-red-400/10"
                                    onClick={handleClearLogs}
                                    title="Clear Logs"
                                >
                                    <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                            </div>
                        </CardHeader>

                        <CardContent className="p-4 flex-1 font-mono text-xs overflow-auto space-y-2">
                            {isRunning && (
                                <div className="text-emerald-500/50 animate-pulse mb-2">
                                    Running...
                                </div>
                            )}
                            {logs.length === 0 && !isRunning && (
                                <span className="text-slate-600 italic">Ready to execute...</span>
                            )}
                            {logs.map((log) => (
                                <div 
                                    key={log.id} 
                                    className="flex gap-2 items-start animate-in fade-in slide-in-from-top-1 duration-300"
                                >
                                    <span className="text-slate-600 shrink-0 select-none">
                                        {log.timestamp.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                    </span>
                                    <span className={`
                                        shrink-0 font-bold px-1 rounded select-none
                                        ${log.level === 'INFO' ? 'text-blue-400 bg-blue-400/10' : ''}
                                        ${log.level === 'DEBUG' ? 'text-slate-400 bg-slate-400/10' : ''}
                                        ${log.level === 'SUCCESS' ? 'text-emerald-400 bg-emerald-400/10' : ''}
                                        ${log.level === 'ERROR' ? 'text-red-400 bg-red-400/10' : ''}
                                    `}>
                                        {log.level}
                                    </span>
                                    <span className={`
                                        break-all whitespace-pre-wrap
                                        ${log.level === 'ERROR' ? 'text-red-300' : 'text-slate-300'}
                                    `}>
                                        {log.message}
                                    </span>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                </div>

                {/* Configuration Sidebar */}
                <div 
                    className={`
                        bg-slate-950/80 backdrop-blur-xl border border-slate-800 rounded-xl transition-all duration-300 ease-in-out overflow-hidden flex flex-col
                        ${isConfigOpen ? 'w-80 opacity-100 translate-x-0' : 'w-0 opacity-0 translate-x-10 p-0 border-0'}
                    `}
                >
                    <div className="p-4 border-b border-slate-800">
                        <h3 className="font-semibold text-slate-200">Configuration</h3>
                    </div>
                    
                    <div className="p-4 space-y-6 overflow-y-auto flex-1">
                        {/* Symbol & Timeframe */}
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label className="text-xs text-slate-400">Symbol</Label>
                                <Select value={symbol} onValueChange={setSymbol}>
                                    <SelectTrigger className="bg-slate-900 border-slate-700">
                                        <SelectValue placeholder="Select symbol" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {(preferences?.supported_symbols || ["XAU_USD", "EUR_USD", "BTC_USD"]).map((s) => (
                                            <SelectItem key={s} value={s.replace('/', '_')}>{s.replace('_', '/')}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-xs text-slate-400">Timeframe</Label>
                                <Select value={timeframe} onValueChange={setTimeframe}>
                                    <SelectTrigger className="bg-slate-900 border-slate-700">
                                        <SelectValue placeholder="Select timeframe" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {(preferences?.preferred_timeframes || ["M1", "M5", "M15", "H1", "H4", "D"]).map((tf) => {
                                            const normalized = NORMALIZE_TF(tf);
                                            return <SelectItem key={tf} value={normalized}>{normalized}</SelectItem>;
                                        })}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Date Range */}
                        <div className="space-y-4 pt-4 border-t border-slate-800">
                             <div className="space-y-2">
                                <Label className="text-xs text-slate-400">Start Date</Label>
                                <Input 
                                    type="date" 
                                    value={startDate} 
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="bg-slate-900 border-slate-700"
                                />
                            </div>
                             <div className="space-y-2">
                                <Label className="text-xs text-slate-400">End Date</Label>
                                <Input 
                                    type="date" 
                                    value={endDate} 
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="bg-slate-900 border-slate-700"
                                />
                            </div>
                        </div>

                         {/* Capital & Fees */}
                         <div className="space-y-4 pt-4 border-t border-slate-800">
                             <div className="space-y-2">
                                <Label className="text-xs text-slate-400">Initial Capital ($)</Label>
                                <Input 
                                    type="number" 
                                    value={initialCapital} 
                                    onChange={(e) => setInitialCapital(Number(e.target.value))}
                                    className="bg-slate-900 border-slate-700"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-xs text-slate-400">Fees (%)</Label>
                                    <Input 
                                        type="number" 
                                        step="0.0001"
                                        value={fees} 
                                        onChange={(e) => setFees(Number(e.target.value))}
                                        className="bg-slate-900 border-slate-700"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-xs text-slate-400">Slippage (%)</Label>
                                    <Input 
                                        type="number" 
                                        step="0.0001"
                                        value={slippage} 
                                        onChange={(e) => setSlippage(Number(e.target.value))}
                                        className="bg-slate-900 border-slate-700"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
