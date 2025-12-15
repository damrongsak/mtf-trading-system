import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { OptimizationResult, runMonteCarlo, MonteCarloResponse } from '@/lib/api/optimization';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'; // Assuming you have ui/table
import { PlayCircle, Trophy, BarChart2 } from 'lucide-react';

interface OptimizationResultsProps {
    results: OptimizationResult[] | null;
}

export function OptimizationResults({ results }: OptimizationResultsProps) {
    const [selectedResult, setSelectedResult] = useState<OptimizationResult | null>(null);
    const [mcResults, setMcResults] = useState<MonteCarloResponse | null>(null);
    const [mcLoading, setMcLoading] = useState(false);

    const handleRunMonteCarlo = async (result: OptimizationResult) => {
        setSelectedResult(result);
        setMcLoading(true);
        try {
             // In a real app we would replicate the trades locally or fetch them.
             // For this MVP, we will mock the trade data in the backend or 
             // assume the backend result structure can be passed back?
             // Actually, `run_grid_search` in backend returns metrics, not full trade list to optimize bandwidth.
             // We can't run specific MC on summary metrics.
             // We need to re-run backtest for that specific param set to get trades.
             
             // WORKAROUND: For MVP, we will just display an alert or mock it.
             // Ideally: Add a "Detailed Backtest" button which navigates to /backtest page with pre-filled params.
             console.log("Monte Carlo simulation requires trade list.");
        } catch (e) {
            console.error(e);
        } finally {
            setMcLoading(false);
        }
    };

    if (!results) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground bg-card/20 rounded-lg border border-dashed border-border">
                <BarChart2 className="w-12 h-12 mb-4 opacity-50" />
                <p>Run grid search to see optimization results</p>
            </div>
        );
    }

    return (
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Trophy className="w-5 h-5 text-yellow-500" />
                    Top Performing Sets
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Fast MA</TableHead>
                                <TableHead>Slow MA</TableHead>
                                <TableHead className="text-right">Sharpe</TableHead>
                                <TableHead className="text-right">Return %</TableHead>
                                <TableHead className="text-right">Max DD %</TableHead>
                                <TableHead className="text-right">Trades</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {results.map((res, i) => (
                                <TableRow key={i}>
                                    <TableCell className="font-medium">{res.params.fast_window}</TableCell>
                                    <TableCell>{res.params.slow_window}</TableCell>
                                    <TableCell className="text-right text-green-400 font-bold">
                                        {res.metrics.sharpe_ratio?.toFixed(2)}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        {(res.metrics.total_return * 100).toFixed(1)}%
                                    </TableCell>
                                    <TableCell className="text-right text-red-400">
                                        {(res.metrics.max_drawdown * 100).toFixed(1)}%
                                    </TableCell>
                                    <TableCell className="text-right">{res.metrics.total_trades}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    );
}
