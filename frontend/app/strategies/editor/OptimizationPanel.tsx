import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Trash2, Plus, Play, Loader2 } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface ParamRange {
    name: string;
    start: number;
    stop: number;
    step: number;
}

import { OptimizationResult } from '@/lib/api/types';

interface OptimizationPanelProps {
    onRunOptimization: (ranges: Record<string, unknown>) => Promise<OptimizationResult[]>;
    isLoading: boolean;
}

export function OptimizationPanel({ onRunOptimization, isLoading }: OptimizationPanelProps) {
    const [ranges, setRanges] = useState<ParamRange[]>([
        { name: 'fast_window', start: 5, stop: 30, step: 5 },
        { name: 'slow_window', start: 40, stop: 100, step: 20 }
    ]);
    const [results, setResults] = useState<OptimizationResult[]>([]);

    const addRange = () => {
        setRanges([...ranges, { name: '', start: 0, stop: 0, step: 0 }]);
    };

    const removeRange = (index: number) => {
        setRanges(ranges.filter((_, i) => i !== index));
    };

    const updateRange = (index: number, field: keyof ParamRange, value: string | number) => {
        const newRanges = [...ranges];
        if (field === 'name') {
            newRanges[index].name = value as string;
        } else {
            newRanges[index][field] = Number(value);
        }
        setRanges(newRanges);
    };

    const handleRun = async () => {
        // Convert array to dict format expected by backend: {'param': {'start': 1, 'stop': 10, 'step': 1}}
        const paramGrid: Record<string, unknown> = {};
        for (const r of ranges) {
            if (r.name.trim()) {
                paramGrid[r.name] = {
                    start: r.start,
                    stop: r.stop,
                    step: r.step
                };
            }
        }
        
        try {
            const res = await onRunOptimization(paramGrid);
            setResults(res);
        } catch (error) {
            console.error("Optimization failed:", error);
        }
    };

    return (
        <div className="space-y-4 h-full flex flex-col">
            <Card className="bg-slate-950 border-slate-800 shrink-0">
                <CardHeader className="py-3">
                    <CardTitle className="text-sm font-medium text-slate-400">Parameter Ranges</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                    {ranges.map((range, index) => (
                        <div key={index} className="flex gap-2 items-center">
                            <Input 
                                placeholder="Param Name (e.g. window)" 
                                value={range.name} 
                                onChange={(e) => updateRange(index, 'name', e.target.value)}
                                className="bg-slate-900 border-slate-700 h-8 text-xs w-1/3"
                            />
                            <div className="flex gap-1 items-center bg-slate-900/50 p-1 rounded border border-slate-800">
                                <Input 
                                    type="number" 
                                    placeholder="Start" 
                                    value={range.start} 
                                    onChange={(e) => updateRange(index, 'start', e.target.value)}
                                    className="bg-transparent border-0 h-6 text-xs w-12 px-1 text-center"
                                />
                                <span className="text-slate-600 text-[10px]">-</span>
                                <Input 
                                    type="number" 
                                    placeholder="Stop" 
                                    value={range.stop} 
                                    onChange={(e) => updateRange(index, 'stop', e.target.value)}
                                    className="bg-transparent border-0 h-6 text-xs w-12 px-1 text-center"
                                />
                                <span className="text-slate-600 text-[10px]">/</span>
                                <Input 
                                    type="number" 
                                    placeholder="Step" 
                                    value={range.step} 
                                    onChange={(e) => updateRange(index, 'step', e.target.value)}
                                    className="bg-transparent border-0 h-6 text-xs w-12 px-1 text-center"
                                />
                            </div>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500 hover:text-red-400" onClick={() => removeRange(index)}>
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}
                    <Button variant="outline" size="sm" onClick={addRange} className="w-full border-dashed border-slate-700 text-slate-400 hover:text-slate-200">
                        <Plus className="h-3 w-3 mr-2" /> Add Parameter
                    </Button>
                    
                    <Button onClick={handleRun} disabled={isLoading} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white mt-4">
                        {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
                        Run Optimization
                    </Button>
                </CardContent>
            </Card>

            <div className="flex-1 overflow-auto rounded-md border border-slate-800 bg-slate-950/50">
                <Table>
                    <TableHeader className="bg-slate-900 sticky top-0 z-10">
                        <TableRow>
                            <TableHead className="text-xs">Parameters</TableHead>
                            <TableHead className="text-xs text-right">Return %</TableHead>
                            <TableHead className="text-xs text-right">Sharpe</TableHead>
                            <TableHead className="text-xs text-right">DD %</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {results.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={4} className="text-center text-slate-500 text-xs py-8">
                                    No results yet. Define ranges and run optimization.
                                </TableCell>
                            </TableRow>
                        ) : (
                            results.map((res, i) => (
                                <TableRow key={i} className="hover:bg-slate-900/50 text-xs">
                                    <TableCell className="font-mono text-slate-300">
                                        {Object.entries(res.params).map(([k, v]) => (
                                            <div key={k}>{k}: <span className="text-emerald-400">{String(v)}</span></div>
                                        ))}
                                    </TableCell>
                                    <TableCell className="text-right font-medium">
                                        {(res.metrics.total_return * 100).toFixed(2)}%
                                    </TableCell>
                                    <TableCell className="text-right text-slate-400">
                                        {(res.metrics.sharpe_ratio || 0).toFixed(2)}
                                    </TableCell>
                                    <TableCell className="text-right text-red-400">
                                        {(res.metrics.max_drawdown * 100).toFixed(2)}%
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
