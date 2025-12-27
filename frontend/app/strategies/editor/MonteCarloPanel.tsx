
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Play, Activity } from 'lucide-react';

import { BacktestTrade, MonteCarloResponse } from '@/lib/api/types';

interface MonteCarloPanelProps {
    trades: BacktestTrade[];
    onRunSimulation: (trades: BacktestTrade[], iterations: number) => Promise<MonteCarloResponse>;
    isLoading: boolean;
}

export function MonteCarloPanel({ trades, onRunSimulation, isLoading }: MonteCarloPanelProps) {
    const [iterations, setIterations] = useState(1000);
    const [results, setResults] = useState<MonteCarloResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleRun = async () => {
        if (!trades || trades.length < 10) {
            setError("Need at least 10 trades to run simulation.");
            return;
        }
        setError(null);
        try {
            const res = await onRunSimulation(trades, iterations);
            setResults(res);
        } catch (err) {
            setError((err as Error).message || "Simulation failed");
        }
    };

    if (!trades || trades.length === 0) {
        return (
            <div className="h-full flex items-center justify-center text-slate-500 flex-col gap-2 p-8 text-center">
                <Activity className="h-12 w-12 opacity-50" />
                <p>Run a backtest first to generate trades for simulation.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4 h-full flex flex-col">
            <Card className="bg-slate-950 border-slate-800 shrink-0">
                <CardHeader className="py-3">
                    <CardTitle className="text-sm font-medium text-slate-400">Monte Carlo Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label className="text-xs text-slate-400">Iterations (Simulations)</Label>
                        <Input 
                            type="number" 
                            min="100"
                            max="5000"
                            step="100"
                            value={iterations} 
                            onChange={(e) => setIterations(Number(e.target.value))}
                            className="bg-slate-900 border-slate-700 font-mono"
                        />
                        <p className="text-[10px] text-slate-500">
                             Simulates {iterations} market scenarios by shuffling your {trades.length} trades.
                        </p>
                    </div>
                    
                    {error && <div className="text-red-400 text-xs bg-red-400/10 p-2 rounded">{error}</div>}

                    <Button onClick={handleRun} disabled={isLoading} className="w-full bg-purple-600 hover:bg-purple-700 text-white">
                        {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
                        Run Simulation
                    </Button>
                </CardContent>
            </Card>

            {results && (
                <div className="flex-1 overflow-auto rounded-md border border-slate-800 bg-slate-950/50">
                    <div className="p-4 space-y-6">
                        <div>
                            <h4 className="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">Drawdown Risk (95% CI)</h4>
                            <div className="grid grid-cols-2 gap-2">
                                <Card className="bg-slate-900 border-slate-800 p-3">
                                    <div className="text-[10px] text-slate-500 uppercase">Median DD</div>
                                    <div className="text-lg font-mono text-slate-200">
                                        {(results.max_drawdown.median * 100).toFixed(2)}%
                                    </div>
                                </Card>
                                <Card className="bg-slate-900 border-red-500/20 p-3">
                                    <div className="text-[10px] text-red-400 uppercase font-bold">Worst Case (p95)</div>
                                    <div className="text-lg font-mono text-red-400">
                                        {(results.max_drawdown.p95 * 100).toFixed(2)}%
                                    </div>
                                    <div className="text-[9px] text-slate-600 mt-1">
                                        95% chance DD won&apos;t exceed this
                                    </div>
                                </Card>
                            </div>
                        </div>

                        <div>
                            <h4 className="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">Return Expectations</h4>
                            <div className="grid grid-cols-2 gap-2">
                                <Card className="bg-slate-900 border-slate-800 p-3">
                                    <div className="text-[10px] text-slate-500 uppercase">Median Return</div>
                                    <div className="text-lg font-mono text-emerald-400">
                                        {(results.total_return.median * 100).toFixed(2)}%
                                    </div>
                                </Card>
                                 <Card className="bg-slate-900 border-slate-800 p-3">
                                    <div className="text-[10px] text-slate-500 uppercase">Worst Case (p95)</div>
                                    <div className="text-lg font-mono text-slate-200">
                                        {(results.total_return.p95 * 100).toFixed(2)}%
                                    </div>
                                </Card>
                            </div>
                        </div>

                        <div>
                            <h4 className="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">Sharpe Ratio</h4>
                            <div className="grid grid-cols-2 gap-2">
                                <Card className="bg-slate-900 border-slate-800 p-3">
                                    <div className="text-[10px] text-slate-500 uppercase">Median</div>
                                    <div className="text-lg font-mono text-blue-400">
                                        {results.sharpe_ratio.median.toFixed(2)}
                                    </div>
                                </Card>
                                <Card className="bg-slate-900 border-slate-800 p-3">
                                    <div className="text-[10px] text-slate-500 uppercase">Range (p5-Best)</div>
                                    <div className="text-sm font-mono text-slate-300 flex items-center h-7">
                                        {results.sharpe_ratio.p95.toFixed(2)} - {results.sharpe_ratio.best?.toFixed(2)}
                                    </div>
                                </Card>
                            </div>
                        </div>

                        <div>
                            <h4 className="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">Survival Analysis</h4>
                            <Card className={`bg-slate-900 border p-3 ${results.ruin_probability > 0.05 ? 'border-red-500/50 bg-red-500/5' : 'border-emerald-500/20'}`}>
                                <div className="flex justify-between items-center">
                                    <div>
                                        <div className="text-[10px] text-slate-500 uppercase">Ruin Probability ({">"}50% DD)</div>
                                        <div className={`text-lg font-mono ${results.ruin_probability > 0.05 ? 'text-red-400' : 'text-emerald-400'}`}>
                                            {(results.ruin_probability * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                    {results.ruin_probability > 0.10 && (
                                        <div className="text-xs text-red-400 max-w-[120px] text-right">
                                            High risk of ruin!
                                        </div>
                                    )}
                                </div>
                            </Card>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
