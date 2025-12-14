import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { BacktestRequest } from '@/lib/api/backtest';
import { Play, Settings2 } from 'lucide-react';

interface BacktestConfigFormProps {
    onRun: (config: BacktestRequest) => void;
    loading: boolean;
}

export function BacktestConfigForm({ onRun, loading }: BacktestConfigFormProps) {
    const [symbol, setSymbol] = useState('XAU_USD');
    const [timeframe, setTimeframe] = useState('H1');
    const [startDate, setStartDate] = useState('2024-01-01');
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
    const [capital, setCapital] = useState(10000);
    const [fees, setFees] = useState(0.0001);
    const [slippage, setSlippage] = useState(0.0001);
    const [params, setParams] = useState('{\n  "fast_ema": 20,\n  "slow_ema": 50,\n  "rsi_period": 14\n}');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        
        let parsedParams = {};
        try {
            parsedParams = JSON.parse(params);
        } catch (e) {
            alert("Invalid JSON params");
            return;
        }

        onRun({
            symbol,
            timeframe,
            start_date: new Date(startDate).toISOString(),
            end_date: new Date(endDate).toISOString(),
            initial_capital: Number(capital),
            fees: Number(fees),
            slippage: Number(slippage),
            strategy_params: parsedParams
        });
    };

    return (
        <Card className="h-full border-border/50 bg-card/50 backdrop-blur-sm">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Settings2 className="w-5 h-5 text-primary" />
                    Configuration
                </CardTitle>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
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
                                <SelectItem value="USD_JPY">USD/JPY</SelectItem>
                                <SelectItem value="BTC_USD">BTC/USD</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Timeframe</label>
                        <Select value={timeframe} onValueChange={setTimeframe}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="M15">M15</SelectItem>
                                <SelectItem value="H1">H1</SelectItem>
                                <SelectItem value="H4">H4</SelectItem>
                                <SelectItem value="D1">D1</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Start Date</label>
                            <input 
                                type="date" 
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">End Date</label>
                            <input 
                                type="date" 
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Initial Capital ($)</label>
                        <input 
                            type="number" 
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                            value={capital}
                            onChange={(e) => setCapital(Number(e.target.value))}
                            min="100"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Fees (%)</label>
                            <input 
                                type="number" 
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                                value={fees * 100}
                                onChange={(e) => setFees(Number(e.target.value) / 100)}
                                step="0.01"
                                min="0"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Slippage (%)</label>
                            <input 
                                type="number" 
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                                value={slippage * 100}
                                onChange={(e) => setSlippage(Number(e.target.value) / 100)}
                                step="0.01"
                                min="0"
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Strategy Parameters (JSON)</label>
                        <textarea 
                            className="w-full h-32 rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background"
                            value={params}
                            onChange={(e) => setParams(e.target.value)}
                        />
                    </div>

                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading ? 'Running...' : (
                            <>
                                <Play className="w-4 h-4 mr-2" />
                                Run Backtest
                            </>
                        )}
                    </Button>
                </form>
            </CardContent>
        </Card>
    );
}
