"use client";

import { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { getOpenInterestSnapshots, getOpenInterestAnalysis, getOpenInterestContracts, OpenInterestSnapshot, OpenInterestAnalysis } from '@/lib/api/data';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { format } from 'date-fns';
import { Loader2, TrendingUp, BarChart2, Activity, ArrowDown, ArrowUp, Filter } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

export function OpenInterestAnalytics() {
    const [snapshots, setSnapshots] = useState<OpenInterestSnapshot[]>([]);
    const [selectedSnapshot, setSelectedSnapshot] = useState<string>("");
    
    // Filters
    const [contracts, setContracts] = useState<string[]>([]);
    const [selectedContract, setSelectedContract] = useState<string>("");
    const [minOi, setMinOi] = useState<number[]>([0]); // Initialize with 0

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

    // Fetch Contracts when Snapshot changes
    useEffect(() => {
        if (!selectedSnapshot) return;
        
        getOpenInterestContracts(selectedSnapshot).then(data => {
            setContracts(data);
            // Auto-select first contract (expiry) if available, or "ALL" if preferred. 
            // For rigorous quant analysis, selecting the front-month is usually default.
            if (data.length > 0) {
                setSelectedContract(data[0]);
            } else {
                setSelectedContract("");
            }
        });
    }, [selectedSnapshot]);

    // Fetch Analysis when Snapshot or Filters change
    useEffect(() => {
        if (!selectedSnapshot) return;

        setLoading(true);
        // Debounce handling could be good here if slider is drag-heavy, but for now simple effect is fine.
        const minOiVal = minOi.length > 0 ? minOi[0] : 0;
        
        getOpenInterestAnalysis(selectedSnapshot, selectedContract, minOiVal)
            .then(data => setAnalysis(data))
            .catch(err => console.error(err))
            .finally(() => setLoading(false));
    }, [selectedSnapshot, selectedContract, minOi]);

    if(loading && !analysis) { // Only show full loader if no data exists yet
        return (
             <Card className="w-full border-gray-800 bg-gray-950/50 backdrop-blur shadow-xl mt-6 min-h-[400px] flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-gray-500" />
            </Card>
        )
    }

    if (!analysis) return null;

    const { summary, distribution } = analysis;

    return (
        <div className="space-y-6 mt-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <h2 className="text-2xl font-bold">Analytics Dashboard</h2>
                
                {/* Premium Filter Toolbar */}
                <div className="flex flex-col md:flex-row items-center gap-4 bg-slate-900/50 backdrop-blur-md p-4 rounded-xl border border-slate-800 shadow-xl w-full">
                    
                    {/* Left Group: Selectors */}
                    <div className="flex gap-4 w-full md:w-auto">
                        {/* Snapshot Selector */}
                        <div className="flex-1 md:w-[220px]">
                            <label className="text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5 ">
                                <BarChart2 className="w-3.5 h-3.5" />
                                Snapshot Time
                            </label>
                            <Select value={selectedSnapshot} onValueChange={setSelectedSnapshot}>
                                <SelectTrigger className="h-10 bg-slate-950 border-slate-700 hover:border-slate-600 transition-colors">
                                    <SelectValue placeholder="Select Snapshot" />
                                </SelectTrigger>
                                <SelectContent className="max-h-[300px]">
                                    {snapshots.map((s, idx) => (
                                        <SelectItem key={idx} value={s.snapshot_at}>
                                            {format(new Date(s.snapshot_at), 'MMM dd, HH:mm')} 
                                            <span className="ml-2 text-xs text-slate-500">({s.count})</span>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Contract Selector */}
                        <div className="flex-1 md:w-[180px]">
                            <label className="text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
                                <TrendingUp className="w-3.5 h-3.5" />
                                Expiry
                            </label>
                            <Select value={selectedContract} onValueChange={setSelectedContract} disabled={contracts.length === 0}>
                                <SelectTrigger className="h-10 bg-slate-950 border-slate-700 hover:border-slate-600 transition-colors">
                                    <SelectValue placeholder={contracts.length === 0 ? "Loading..." : "All Contracts"} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="ALL_CONTRACTS_VALUE_RESET">All Contracts</SelectItem>
                                    {contracts.map((c, idx) => (
                                        <SelectItem key={idx} value={c}>
                                            {c}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Divider (Desktop only) */}
                    <div className="hidden md:block w-px h-10 bg-slate-800 mx-2"></div>

                    {/* Right Group: Slider */}
                    <div className="flex-1 w-full flex flex-col justify-center px-2">
                        <div className="flex justify-between items-center mb-3">
                            <label className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                                <Filter className="w-3.5 h-3.5 text-blue-400" />
                                Noise Filter <span className="text-slate-600 font-normal ml-1">(Min OI)</span>
                            </label>
                            <div className="text-sm font-mono font-bold text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded border border-blue-400/20">
                                {minOi[0] || 0}
                            </div>
                        </div>
                        
                        <div className="relative flex items-center gap-3">
                             <span className="text-[10px] font-mono text-slate-600">0</span>
                             <Slider 
                                defaultValue={[0]} 
                                value={minOi}
                                onValueChange={setMinOi}
                                max={5000} 
                                step={100}
                                className="flex-1 py-1 cursor-pointer"
                            />
                             <span className="text-[10px] font-mono text-slate-600">5k</span>
                        </div>
                    </div>
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
                            <CardDescription>
                                {selectedContract ? `${selectedContract} Expiry` : "All Contracts"} | Min OI: {minOi[0] || 0}
                            </CardDescription>
                        </div>
                        {loading && <Loader2 className="w-4 h-4 animate-spin ml-auto text-gray-500" />}
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
