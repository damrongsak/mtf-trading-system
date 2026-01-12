"use client";

import React from 'react';
import AlphaEditor from '@/components/alpha/MonacoEditor';
import FeatureMatrix from '@/components/alpha/FeatureMatrix';
import SignalChart from '@/components/alpha/SignalChart';
import { useAlphaStore } from '@/lib/stores/useAlphaStore';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DatePickerNative } from "@/components/ui/date-picker-native";
import { Play, Rocket, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useState } from 'react';
import { deployAlphaStrategy } from '@/lib/api/alpha';

const AlphaLabPage = () => {
    const { runAlpha, isRunning, result, error, code, symbol, setSymbol, timeframe, setTimeframe, startDate, setStartDate, endDate, setEndDate } = useAlphaStore();
    
    // Deployment State
    const [isDeployOpen, setIsDeployOpen] = useState(false);
    const [isDeploying, setIsDeploying] = useState(false);
    const [deployConfig, setDeployConfig] = useState({
        name: '',
        description: '',
    });

    const handleDeploy = async () => {
        if (!deployConfig.name || !code) {
            toast.error("Please enter a name and ensure strategy code is present.");
            return;
        }

        setIsDeploying(true);
        try {
            await deployAlphaStrategy({
                name: deployConfig.name,
                template_id: "ALPHA_ENGINE_V1",
                fund_id: "00000000-0000-0000-0000-000000000000", // Placeholder / Default Fund
                broker_account_id: "00000000-0000-0000-0000-000000000000", // Placeholder
                config_json: {
                    formula: code, // Assuming 'code' in store is the formula string
                    meta_description: deployConfig.description
                },
                risk_settings: {}
            });
            toast.success("Strategy Deployed Successfully!");
            setIsDeployOpen(false);
        } catch (e) {
            console.error("Deploy failed", e);
            toast.error("Failed to deploy strategy: " + (e as any).message);
        }
        finally {
            setIsDeploying(false);
        }
    };

    return (
        <div className="h-[calc(100vh-4rem)] p-4 gap-4 grid grid-cols-12 grid-rows-6">
            {/* Header / Toolbar - Span 12, Row 1 (Auto height) */}
            <div className="col-span-12 row-span-1 flex items-center justify-between bg-slate-900/50 p-4 rounded-lg border border-slate-800">
                <div>
                     <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Athena Alpha Lab</h1>
                     <p className="text-slate-400 text-sm">Design, Backtest, and Deploy Statistical Alpha</p>
                </div>
                
                <div className="flex items-center gap-4">
                    {/* Settings: Symbol & Timeframe */}
                    <div className="flex gap-2 items-center">
                        <Select value={symbol} onValueChange={setSymbol}>
                            <SelectTrigger className="w-[140px] border-slate-700 bg-slate-950">
                                <SelectValue placeholder="Symbol" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-900 border-slate-800">
                                <SelectItem value="XAU_USD">XAU_USD (Gold)</SelectItem>
                                <SelectItem value="EUR_USD">EUR_USD</SelectItem>
                                <SelectItem value="GBP_USD">GBP_USD</SelectItem>
                                <SelectItem value="BTC_USD">BTC_USD</SelectItem>
                                <SelectItem value="SPX500_USD">SPX500</SelectItem>
                            </SelectContent>
                        </Select>

                        <Select value={timeframe} onValueChange={setTimeframe}>
                            <SelectTrigger className="w-[100px] border-slate-700 bg-slate-950">
                                <SelectValue placeholder="Timeframe" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-900 border-slate-800">
                                <SelectItem value="M1">M1</SelectItem>
                                <SelectItem value="M5">M5</SelectItem>
                                <SelectItem value="M15">M15</SelectItem>
                                <SelectItem value="H1">H1</SelectItem>
                                <SelectItem value="H4">H4</SelectItem>
                                <SelectItem value="D">Daily</SelectItem>
                            </SelectContent>
                        </Select>

                        <div className="w-[180px]">
                             <DatePickerNative 
                                value={startDate} 
                                onChange={setStartDate} 
                                placeholder="Start Date"
                             />
                        </div>
                        <div className="w-[180px]">
                             <DatePickerNative 
                                value={endDate} 
                                onChange={setEndDate} 
                                placeholder="End Date"
                             />
                        </div>
                    </div>

                    <div className="h-8 w-[1px] bg-slate-800 mx-2" />

                    <div className="flex gap-2">
                        <Dialog open={isDeployOpen} onOpenChange={setIsDeployOpen}>
                            <DialogTrigger asChild>
                                <Button variant="outline" className="border-blue-500/50 text-blue-400 hover:bg-blue-900/20">
                                    <Rocket className="w-4 h-4 mr-2" />
                                    Deploy
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="bg-slate-900 border-slate-800 text-slate-200">
                                <DialogHeader>
                                    <DialogTitle>Deploy Alpha Strategy</DialogTitle>
                                    <DialogDescription>
                                        Deploy this formula to the live trading engine.
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="grid gap-4 py-4">
                                    <div className="grid grid-cols-4 items-center gap-4">
                                        <Label htmlFor="name" className="text-right">Name</Label>
                                        <Input 
                                            id="name" 
                                            value={deployConfig.name} 
                                            onChange={(e) => setDeployConfig({...deployConfig, name: e.target.value})}
                                            className="col-span-3 bg-slate-950 border-slate-700" 
                                            placeholder="e.g. Mumtaz Momentum"
                                        />
                                    </div>
                                    <div className="grid grid-cols-4 items-center gap-4">
                                        <Label htmlFor="desc" className="text-right">Description</Label>
                                        <Textarea 
                                            id="desc" 
                                            value={deployConfig.description} 
                                            onChange={(e) => setDeployConfig({...deployConfig, description: e.target.value})}
                                            className="col-span-3 bg-slate-950 border-slate-700" 
                                            placeholder="Describe the strategy intent..."
                                        />
                                    </div>
                                </div>
                                <DialogFooter>
                                    <Button onClick={handleDeploy} disabled={isDeploying} className="bg-purple-600 hover:bg-purple-500">
                                        {isDeploying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Confirm Deployment
                                    </Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>

                        <Button 
                            onClick={() => runAlpha('full')} 
                            disabled={isRunning}
                            className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-6"
                        >
                            <Play className="w-4 h-4 mr-2" />
                            {isRunning ? 'Running...' : 'Run Backtest'}
                        </Button>
                    </div>
                </div>
            </div>

            {/* Editor Area - Span 8, Rows 2-4 */}
            <div className="col-span-8 row-span-3">
                <AlphaEditor />
            </div>

            {/* Sidebar / Feature Matrix - Span 4, Rows 2-6 */}
            <div className="col-span-4 row-span-5">
                <FeatureMatrix />
            </div>

            {/* Metrics / Results - Span 8, Rows 5-6 */}
            <div className="col-span-8 row-span-2">
                <Card className="h-full bg-slate-900 border-slate-800 p-4">
                    <h3 className="text-sm font-semibold text-slate-400 mb-2 uppercase">Backtest Results</h3>
                    
                    {error && (
                        <div className="p-4 bg-red-900/20 text-red-400 rounded border border-red-900/50 font-mono">
                            Error: {error}
                        </div>
                    )}
                    
                    {result && !error && (
                         <div className="grid grid-cols-4 gap-4">
                            <MetricCard label="Sharpe Ratio" value={(result.metrics.sharpe as number)?.toFixed(2) ?? '-'} color="text-blue-400" />
                            <MetricCard label="Information Coeff (IC)" value={(result.metrics.ic as number)?.toFixed(3) ?? '-'} color="text-purple-400" />
                            <MetricCard label="Turnover" value={(result.metrics.turnover as number)?.toFixed(2) ?? '-'} />
                            <MetricCard label="Total Return" value={(result.metrics.total_return as number) ? `${((result.metrics.total_return as number) * 100).toFixed(1)}%` : '-'} color="text-green-400" />
                        
                            {/* Live Signal Chart */}
                            <div className="col-span-4 mt-4 h-48">
                                <SignalChart data={result.signal} timestamps={result.timestamps} />
                            </div>
                        </div>
                    )}

                    {!result && !error && (
                        <div className="h-full flex items-center justify-center text-slate-600">
                            Run a strategy to see metrics
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
};

const MetricCard = ({ label, value, color = 'text-white' }: { label: string, value: string, color?: string }) => (
    <div className="bg-slate-950 p-3 rounded border border-slate-800">
        <div className="text-xs text-slate-500 mb-1">{label}</div>
        <div className={`text-xl font-bold font-mono ${color}`}>{value}</div>
    </div>
);

export default AlphaLabPage;
