import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BacktestResponse } from '@/lib/api/backtest';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react';

interface BacktestResultsProps {
    results: BacktestResponse | null;
}

export function BacktestResults({ results }: BacktestResultsProps) {
    if (!results) {
        return (
            <div className="h-full flex items-center justify-center text-muted-foreground border border-dashed rounded-lg border-border/50 bg-card/10">
                Run a backtest to see results
            </div>
        );
    }

    const { metrics, trades: rawTrades, equity_curve: rawEquity } = results;
    const trades = rawTrades || [];
    const equity_curve = rawEquity || [];

    return (
        <div className="space-y-6 animate-fade-in">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <KPICard 
                    title="Total Return" 
                    value={`${(metrics?.total_return_percent ?? 0).toFixed(2)}%`}
                    subValue={`$${(metrics?.total_return ?? 0).toFixed(2)}`}
                    icon={DollarSign}
                    trend={metrics?.total_return && metrics.total_return > 0 ? 'up' : 'down'}
                />
                <KPICard 
                    title="Benchmark (Buy & Hold)" 
                    value={`${(metrics?.benchmark_return ?? 0).toFixed(2)}%`}
                    subValue="Market Return"
                    icon={TrendingUp}
                    trend={metrics?.benchmark_return && metrics.benchmark_return > 0 ? 'up' : 'down'}
                />
                 <KPICard 
                    title="Win Rate" 
                    value={`${(metrics?.win_rate ?? 0).toFixed(1)}%`}
                    subValue={`${metrics?.winning_trades ?? 0}/${metrics?.total_trades ?? 0} Trades`}
                    icon={Activity}
                />
                <KPICard 
                    title="Max Drawdown" 
                    value={`${(metrics?.max_drawdown_percent ?? 0).toFixed(2)}%`}
                    subValue={`$${(metrics?.max_drawdown ?? 0).toFixed(2)}`}
                    icon={TrendingDown}
                    trend="down"
                    inverse 
                />
                <KPICard 
                    title="Sharpe Ratio" 
                    value={(metrics?.sharpe_ratio ?? 0).toFixed(2)}
                    subValue="Risk Adjusted Return"
                    icon={TrendingUp}
                />
            </div>

            {/* Equity Curve */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader>
                    <CardTitle>Equity Curve</CardTitle>
                </CardHeader>
                <CardContent className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={equity_curve}>
                            <defs>
                                <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
                            <XAxis 
                                dataKey="timestamp" 
                                tickFormatter={(str) => new Date(str).toLocaleDateString()}
                                stroke="#666"
                                fontSize={12}
                            />
                            <YAxis stroke="#666" fontSize={12} />
                            <Tooltip 
                                contentStyle={{ backgroundColor: '#1e293b', border: 'none' }}
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                labelFormatter={(label: any) => new Date(label).toLocaleDateString()}
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                formatter={(value: any) => [typeof value === 'number' ? `$${value.toFixed(2)}` : 'N/A', 'Equity']}
                            />
                            <Area 
                                type="monotone" 
                                dataKey="value" 
                                stroke="#22c55e" 
                                fillOpacity={1} 
                                fill="url(#colorEquity)" 
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            {/* Trades Table */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader>
                    <CardTitle>Trade Report ({trades.length})</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-muted-foreground border-b border-border/50">
                                <tr>
                                    <th className="py-2">Entry Time</th>
                                    <th className="py-2">Type</th>
                                    <th className="py-2 text-right">Entry</th>
                                    <th className="py-2 text-right">Exit</th>
                                    <th className="py-2 text-right">PnL</th>
                                    <th className="py-2 text-right">Return %</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trades.slice(0, 50).map((trade, idx) => (
                                    <tr key={idx} className="border-b border-border/10 hover:bg-muted/10">
                                        <td className="py-2">{new Date(trade.entry_time).toLocaleString()}</td>
                                        <td className={`py-2 font-medium ${trade.direction === 'LONG' ? 'text-green-500' : 'text-red-500'}`}>
                                            {trade.direction}
                                        </td>
                                        <td className="py-2 text-right">{trade.entry_price.toFixed(4)}</td>
                                        <td className="py-2 text-right">{trade.exit_price.toFixed(4)}</td>
                                        <td className={`py-2 text-right ${trade.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                            ${trade.pnl.toFixed(2)}
                                        </td>
                                        <td className={`py-2 text-right ${trade.pnl_percent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                            {(trade.pnl_percent * 100).toFixed(2)}%
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {trades.length > 50 && (
                            <div className="text-center py-4 text-muted-foreground text-xs">
                                Showing first 50 trades of {trades.length}
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

interface KPICardProps {
    title: string;
    value: string | number;
    subValue?: string;
    icon?: React.ElementType;
    trend?: 'up' | 'down';
    inverse?: boolean;
}

function KPICard({ title, value, subValue, icon: Icon, trend, inverse }: KPICardProps) {
    const isPositive = trend === 'up';
    
    // Logic: 
    // If inverse (e.g. Drawdown), Negative is Red (Bad), Positive is Green (Good). 
    // Normal: Positive is Green (Good), Negative is Red (Bad).
    
    let colorClass = "text-foreground";
    if (trend) {
        if (inverse) {
             colorClass = "text-red-500"; // Drawdown is always bad if it exists
        } else {
            colorClass = isPositive ? "text-green-500" : "text-red-500";
        }
    }

    return (
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
            <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                    <p className="text-sm font-medium text-muted-foreground">{title}</p>
                    {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
                </div>
                <div className="flex flex-col">
                    <div className={`text-2xl font-bold ${colorClass}`}>{value}</div>
                    {subValue && <p className="text-xs text-muted-foreground mt-1">{subValue}</p>}
                </div>
            </CardContent>
        </Card>
    );
}
