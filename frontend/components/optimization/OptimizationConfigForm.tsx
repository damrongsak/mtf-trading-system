import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { BacktestRequest } from '@/lib/api/backtest';
import { ScanSearch, Settings2 } from 'lucide-react';

interface OptimizationConfigFormProps {
    onRun: (config: BacktestRequest) => void;
    loading: boolean;
}

export function OptimizationConfigForm({ onRun, loading }: OptimizationConfigFormProps) {
    // Base Config
    const [symbol, setSymbol] = useState('XAU_USD');
    const [timeframe, setTimeframe] = useState('H1');
    const [startDate, setStartDate] = useState('2024-01-01');
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
    const [capital, setCapital] = useState(10000);
    const [fees, setFees] = useState(0.0001);

    // Optimization Ranges
    const [fastStart, setFastStart] = useState(10);
    const [fastEnd, setFastEnd] = useState(50);
    const [fastStep, setFastStep] = useState(10);

    const [slowStart, setSlowStart] = useState(50);
    const [slowEnd, setSlowEnd] = useState(200);
    const [slowStep, setSlowStep] = useState(50);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        // Generate param grid arrays
        const fastWindows = [];
        for (let i = fastStart; i <= fastEnd; i += fastStep) fastWindows.push(i);

        const slowWindows = [];
        for (let i = slowStart; i <= slowEnd; i += slowStep) slowWindows.push(i);

        onRun({
            symbol,
            timeframe,
            start_date: new Date(startDate).toISOString(),
            end_date: new Date(endDate).toISOString(),
            initial_capital: Number(capital),
            fees: Number(fees),
            slippage: 0,
            strategy_params: {}, // Will be overridden by optimization grid
            optimization: {
                method: "GRID",
                param_grid: {
                    fast_window: fastWindows,
                    slow_window: slowWindows
                }
            }
        });
    };

    return (
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Settings2 className="w-5 h-5 text-primary" />
                    Grid Search Config
                </CardTitle>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Basic Settings */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Symbol</label>
                        <Select value={symbol} onValueChange={setSymbol}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="XAU_USD">XAU/USD (Gold)</SelectItem>
                                <SelectItem value="EUR_USD">EUR/USD</SelectItem>
                                <SelectItem value="GBP_USD">GBP/USD</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Start Date</label>
                            <input 
                                type="date" 
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">End Date</label>
                            <input 
                                type="date" 
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <hr className="border-border/50" />
                    
                    {/* Parameter Ranges */}
                    <div className="space-y-2">
                        <label className="text-sm font-semibold text-primary">Fast MA Window</label>
                        <div className="grid grid-cols-3 gap-2">
                            <div className="space-y-1">
                                <span className="text-xs text-muted-foreground">Start</span>
                                <input type="number" className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
                                    value={fastStart} onChange={(e) => setFastStart(Number(e.target.value))} />
                            </div>
                            <div className="space-y-1">
                                <span className="text-xs text-muted-foreground">End</span>
                                <input type="number" className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
                                    value={fastEnd} onChange={(e) => setFastEnd(Number(e.target.value))} />
                            </div>
                            <div className="space-y-1">
                                <span className="text-xs text-muted-foreground">Step</span>
                                <input type="number" className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
                                    value={fastStep} onChange={(e) => setFastStep(Number(e.target.value))} />
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-semibold text-primary">Slow MA Window</label>
                         <div className="grid grid-cols-3 gap-2">
                            <div className="space-y-1">
                                <span className="text-xs text-muted-foreground">Start</span>
                                <input type="number" className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
                                    value={slowStart} onChange={(e) => setSlowStart(Number(e.target.value))} />
                            </div>
                            <div className="space-y-1">
                                <span className="text-xs text-muted-foreground">End</span>
                                <input type="number" className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
                                    value={slowEnd} onChange={(e) => setSlowEnd(Number(e.target.value))} />
                            </div>
                            <div className="space-y-1">
                                <span className="text-xs text-muted-foreground">Step</span>
                                <input type="number" className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
                                    value={slowStep} onChange={(e) => setSlowStep(Number(e.target.value))} />
                            </div>
                        </div>
                    </div>

                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading ? 'Optimizing...' : (
                            <>
                                <ScanSearch className="w-4 h-4 mr-2" />
                                Run Grid Search
                            </>
                        )}
                    </Button>

                    <p className="text-xs text-muted-foreground text-center">
                        Total Permutations: {Math.floor((fastEnd - fastStart + fastStep)/fastStep) * Math.floor((slowEnd - slowStart + slowStep)/slowStep)}
                    </p>
                </form>
            </CardContent>
        </Card>
    );
}
