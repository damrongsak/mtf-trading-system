import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { OptimizationResult } from '@/lib/api/backtest';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Trophy, BarChart2 } from 'lucide-react';

interface OptimizationResultsProps {
    results: OptimizationResult[] | null;
}

export function OptimizationResults({ results }: OptimizationResultsProps) {


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
