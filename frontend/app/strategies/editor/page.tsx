"use client";

import React, { useState, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Play, Save, Terminal, Loader2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
// import { validateStrategy, saveCustomStrategy } from '@/lib/api/strategies'; // To be implemented

const DEFAULT_CODE = `import pandas as pd
# from app.indicators import calculate_ema

async def strategy(state, data_manager):
    """
    My Custom Strategy
    Write your logic here.
    """
    symbol = state.symbol
    
    # 1. Fetch Data
    df = data_manager.get_data(symbol)
    if df.empty:
        return None
        
    # 2. Logic (Example: Buy if Close > Open)
    current_close = df['close'].iloc[-1]
    current_open = df['open'].iloc[-1]
    
    if current_close > current_open:
        return {
            "direction": "BULLISH",
            "stop_loss": current_open,
            "reason": "Bullish Candle"
        }
    
    return None
`;

export default function StrategyEditor() {
    const [code, setCode] = useState(DEFAULT_CODE);
    const [output, setOutput] = useState<string[]>([]);
    const [isRunning, setIsRunning] = useState(false);
    const { user } = useAuth();
    const [title, setTitle] = useState("My Custom Strategy");

    const handleRun = async () => {
        setIsRunning(true);
        setOutput(["Running backtest simulation...", "Sending code to server..."]);
        
        try {
            // Mock API call for now until backend endpoint is ready
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Simulating a successful run log
            const mockLogs = [
                "[INFO] Compiling strategy...",
                "[INFO] Syntax Check: OK",
                "[INFO] Fetching 500 candles for XAU/USD...",
                "[INFO] Ticking...",
                "[INFO] SIGNAL: BULLISH @ 2035.50",
                "[INFO] SIGNAL: BEARISH @ 2040.10",
                "[SUCCESS] Backtest Complete. PnL: +$120.00 (Win Rate: 65%)"
            ];
            setOutput(mockLogs);
            
            // Future: Call real API
            // const res = await validateStrategy({ code, symbol: "XAU/USD" });
            // setOutput(res.logs);
            
        } catch (error) {
            setOutput([`[ERROR] Execution failed: ${(error as Error).message}`]);
        } finally {
            setIsRunning(false);
        }
    };

    const handleSave = async () => {
        // Future: Save to DB
        alert("Save functionality coming in next backend update!");
    };

    return (
        <div className="container mx-auto p-6 space-y-6 text-slate-100">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-emerald-400">Strategy Sandbox</h1>
                    <p className="text-slate-400">Write, test, and deploy custom Python algorithms.</p>
                </div>
                <div className="flex gap-4">
                    <Button onClick={handleRun} disabled={isRunning} variant="secondary" className="gap-2">
                        {isRunning ? <Loader2 className="animate-spin h-4 w-4" /> : <Play className="h-4 w-4" />}
                        Run Backtest
                    </Button>
                    <Button onClick={handleSave} className="gap-2 bg-emerald-600 hover:bg-emerald-700">
                        <Save className="h-4 w-4" />
                        Save Strategy
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[70vh]">
                {/* Editor Column */}
                <div className="lg:col-span-2 h-full">
                    <Card className="h-full bg-slate-900 border-slate-800 flex flex-col">
                        <CardHeader className="py-3 px-4 border-b border-slate-800 bg-slate-950/50">
                            <input 
                                type="text" 
                                value={title} 
                                onChange={(e) => setTitle(e.target.value)}
                                className="bg-transparent text-lg font-semibold text-white focus:outline-none w-full"
                            />
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
                                }}
                            />
                        </CardContent>
                    </Card>
                </div>

                {/* Output Column */}
                <div className="h-full">
                    <Card className="h-full bg-slate-950 border-slate-800 flex flex-col">
                        <CardHeader className="py-3 px-4 border-b border-slate-800 bg-slate-900">
                            <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-wider text-slate-400">
                                <Terminal className="h-4 w-4" />
                                Console Output
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 flex-1 font-mono text-xs overflow-auto space-y-1">
                            {output.length === 0 && (
                                <span className="text-slate-600 italic">Ready to execute...</span>
                            )}
                            {output.map((line, i) => (
                                <div key={i} className={line.includes("ERROR") ? "text-red-400" : line.includes("SUCCESS") ? "text-emerald-400" : "text-slate-300"}>
                                    {line}
                                </div>
                            ))}
                            {isRunning && (
                                <div className="text-emerald-500/50 animate-pulse">_</div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
