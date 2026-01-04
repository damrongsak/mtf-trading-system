"use client";

import { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { getOpenInterestSnapshots, getOpenInterestAnalysis, OpenInterestSnapshot, OpenInterestAnalysis } from '@/lib/api/data';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { format } from 'date-fns';
import { Loader2, TrendingUp, BarChart2, Activity, ArrowDown, ArrowUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

export function OpenInterestAnalytics() {
    const [snapshots, setSnapshots] = useState<OpenInterestSnapshot[]>([]);
    const [selectedSnapshot, setSelectedSnapshot] = useState<string>("");
    const [analysis, setAnalysis] = useState<OpenInterestAnalysis | null>(null);
    const [loading, setLoading] = useState(false);

    // Initial Load of Snapshots
    useEffect(() => {
        getOpenInterestSnapshots(10).then(data => {
            setSnapshots(data);
            if (data.length > 0) {
                setSelectedSnapshot(data[0].snapshot_at);
            }
        });
    }, []);

    // Listen for refresh events
    useEffect(() => {
        const handleRefresh = () => {
             getOpenInterestSnapshots(10).then(data => {
                setSnapshots(data);
                if (data.length > 0 && !selectedSnapshot) {
                    setSelectedSnapshot(data[0].snapshot_at);
                }
            });
        }
        window.addEventListener('refresh_oi_history', handleRefresh);
        return () => window.removeEventListener('refresh_oi_history', handleRefresh);
    }, [selectedSnapshot]);

    // Fetch Analysis when Snapshot changes
    useEffect(() => {
        if (!selectedSnapshot) return;

        setLoading(true);
        getOpenInterestAnalysis(selectedSnapshot)
            .then(data => setAnalysis(data))
            .catch(err => console.error(err))
            .finally(() => setLoading(false));
    }, [selectedSnapshot]);

    if(loading || !analysis) {
        return (
             <Card className="w-full border-gray-800 bg-gray-950/50 backdrop-blur shadow-xl mt-6 min-h-[400px] flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-gray-500" />
            </Card>
        )
    }

    const { summary, distribution } = analysis;

    return (
        <div className="space-y-6 mt-6">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold">Analytics Dashboard</h2>
                <div className="w-[250px]">
                    <Select value={selectedSnapshot} onValueChange={setSelectedSnapshot}>
                        <SelectTrigger className="bg-gray-900 border-gray-800 text-gray-300">
                            <SelectValue placeholder="Select Snapshot" />
                        </SelectTrigger>
                        <SelectContent>
                            {snapshots.map((s, idx) => (
                                <SelectItem key={idx} value={s.snapshot_at}>
                                    {format(new Date(s.snapshot_at), 'PPP p')}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="bg-gray-900/50 border-gray-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-400">Put/Call Ratio</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold flex items-center gap-2">
                            {summary.pcr.toFixed(2)}
                            {summary.pcr > 1 ? <ArrowUp className="w-4 h-4 text-red-500" /> : <ArrowDown className="w-4 h-4 text-green-500" />}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            {summary.pcr > 0.7 ? "Bearish Sentiment" : "Bullish Sentiment"}
                        </p>
                    </CardContent>
                </Card>
                <Card className="bg-gray-900/50 border-gray-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-400">Total Market OI</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {((summary.total_call_oi + summary.total_put_oi) / 1000).toFixed(1)}k
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Contracts
                        </p>
                    </CardContent>
                </Card>
                <Card className="bg-gray-900/50 border-gray-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-400">Max Call (Resistance)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-red-400">
                            {summary.max_call_strike}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            High Resistance Level
                        </p>
                    </CardContent>
                </Card>
                <Card className="bg-gray-900/50 border-gray-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-400">Max Put (Support)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-400">
                            {summary.max_put_strike}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Strong Support Level
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Distribution Chart */}
            <Card className="w-full border-gray-800 bg-gray-950/50 backdrop-blur shadow-xl">
                <CardHeader>
                     <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-lg">
                            <BarChart2 className="w-6 h-6 text-blue-500" />
                        </div>
                        <div>
                            <CardTitle className="text-xl">Open Interest Distribution</CardTitle>
                            <CardDescription>Call vs Put Volume by Strike Price</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="h-[500px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            data={distribution}
                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                            <XAxis dataKey="strike" stroke="#888" />
                            <YAxis stroke="#888" />
                            <Tooltip 
                                contentStyle={{ backgroundColor: '#111', borderColor: '#333' }}
                                itemStyle={{ color: '#fff' }}
                            />
                            <Legend />
                            <ReferenceLine x={summary.max_call_strike} stroke="red" label="Res" />
                            <ReferenceLine x={summary.max_put_strike} stroke="green" label="Sup" />
                            <Bar dataKey="call_oi" name="Call OI" fill="#ef4444" stackId="a" />
                            <Bar dataKey="put_oi" name="Put OI" fill="#22c55e" stackId="a" />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </div>
    );
}
