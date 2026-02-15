"use client";

import React, { useState, useEffect, use } from 'react';
import { logger } from '@/lib/api/app-logger';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, ArrowLeft, Terminal, Activity, Calendar } from 'lucide-react';
import { getDeployment, getDeploymentLogs } from '@/lib/api/deployments';
import { Deployment, StrategyLog } from '@/lib/api/types';
import { format } from 'date-fns';
import Link from 'next/link';

// Helper for JSON Display
const JsonViewer = ({ data }: { data: any }) => (
    <pre className="bg-slate-950 p-4 rounded-md overflow-x-auto text-xs font-mono text-slate-300 border border-slate-800 scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent max-h-[400px]">
        {JSON.stringify(data, null, 2)}
    </pre>
);

export default function DeploymentDetailsPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const [deployment, setDeployment] = useState<Deployment | null>(null);
    const [logs, setLogs] = useState<StrategyLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingLogs, setIsLoadingLogs] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Initial Load
    useEffect(() => {
        const loadData = async () => {
             try {
                 const dep = await getDeployment(id);
                 setDeployment(dep);
                 
                 // Enable polling for logs if active
                 if (dep.status === 'ACTIVE') {
                     // Initial fetch
                     await fetchLogs(id);
                 } else {
                     await fetchLogs(id);
                 }
             } catch (err: any) {
                 setError("Failed to load deployment details.");
                 logger.error(err);
             } finally {
                 setIsLoading(false);
             }
        };
        loadData();
    }, [id]);

    const fetchLogs = async (depId: string) => {
        setIsLoadingLogs(true);
        try {
            const logData = await getDeploymentLogs(depId, 1, 50); // Fetch last 50
            setLogs(logData.data);
        } catch (e) {
            logger.error("Failed to load logs", e);
        } finally {
            setIsLoadingLogs(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
            </div>
        );
    }

    if (error || !deployment) {
        return (
             <div className="container mx-auto p-6">
                <div className="mb-6">
                    <Link href="/deployments" className="text-slate-400 hover:text-white flex items-center gap-2">
                        <ArrowLeft className="h-4 w-4" /> Back to Fleet
                    </Link>
                </div>
                <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-8 rounded-md text-center">
                    <h2 className="text-xl font-bold mb-2">Error</h2>
                    <p>{error || "Deployment not found"}</p>
                </div>
             </div>
        );
    }

    return (
        <div className="container mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                     <Link href="/deployments" className="text-slate-400 hover:text-white flex items-center gap-2 mb-2 text-sm">
                        <ArrowLeft className="h-3 w-3" /> Back to Fleet
                    </Link>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        {deployment.strategy_name || "Unknown Strategy"}
                        <Badge variant={deployment.is_live ? "destructive" : "secondary"}>
                            {deployment.is_live ? "LIVE" : "PAPER"}
                        </Badge>
                    </h1>
                    <div className="flex items-center gap-4 text-slate-400 mt-1 text-sm">
                        <span className="font-mono bg-slate-800 px-2 py-0.5 rounded text-xs">{deployment.id.split('-')[0]}</span>
                        <span>{deployment.stock_symbol} ({deployment.timeframe})</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs ${
                             deployment.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-300'
                        }`}>
                            {deployment.status}
                        </span>
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-sm text-slate-400 mb-1">Total PnL</div>
                    <div className={`text-2xl font-mono font-bold ${
                        (deployment.total_pnl_usd || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                        ${(deployment.total_pnl_usd || 0).toFixed(2)}
                    </div>
                </div>
            </div>

            <Tabs defaultValue="overview" className="w-full">
                <TabsList className="bg-slate-900 border-slate-800 p-1">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="logs" className="flex items-center gap-2">
                        <Terminal className="h-3 w-3" /> Execution Logs
                    </TabsTrigger>
                    <TabsTrigger value="config">Configuration</TabsTrigger>
                </TabsList>

                {/* Overview Content */}
                <TabsContent value="overview" className="mt-6 space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                         <Card className="bg-slate-950 border-slate-800">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-slate-400">Started At</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl text-white">
                                    {format(new Date(deployment.started_at), 'MMM dd')}
                                </div>
                                <div className="text-xs text-slate-500">
                                     {format(new Date(deployment.started_at), 'HH:mm:ss')}
                                </div>
                            </CardContent>
                        </Card>
                         <Card className="bg-slate-950 border-slate-800">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-slate-400">Timeframe</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl text-white">{deployment.timeframe}</div>
                            </CardContent>
                        </Card>
                        <Card className="bg-slate-950 border-slate-800">
                             <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-slate-400">Last Error</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {deployment.last_error ? (
                                    <div className="text-red-400 text-sm">{deployment.last_error}</div>
                                ) : (
                                    <div className="text-emerald-500 text-sm">None</div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                    
                    {/* Activity Feed Placeholder */}
                    <div className="mt-6">
                         <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
                             <Activity className="h-4 w-4" /> Activity Feed
                         </h3>
                         <div className="bg-slate-950 border border-slate-800 rounded-lg p-6 text-center text-slate-500">
                             Coming Soon: Live Trade Application Logs
                         </div>
                    </div>
                </TabsContent>

                {/* Logs Content */}
                <TabsContent value="logs" className="mt-6">
                    <Card className="bg-slate-950 border-slate-800">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle>Strategy Execution Logs</CardTitle>
                                <CardDescription>Real-time calculation logs from Strategy Core.</CardDescription>
                            </div>
                            <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={() => fetchLogs(id)}
                                disabled={isLoadingLogs}
                                className="border-slate-700 hover:bg-slate-800 text-slate-300"
                            >
                                {isLoadingLogs ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Refresh'}
                            </Button>
                        </CardHeader>
                        <CardContent>
                             {logs.length === 0 ? (
                                 <div className="text-center py-12 text-slate-500">
                                     No logs found.
                                 </div>
                             ) : (
                                 <div className="space-y-4">
                                     {logs.map((log) => (
                                         <div key={log.id} className="border border-slate-800 rounded-lg p-4 bg-slate-900/50">
                                             <div className="flex justify-between items-start mb-3">
                                                 <div className="flex items-center gap-2">
                                                     <Badge variant="outline" className="border-slate-700 text-slate-400 font-mono">
                                                         {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
                                                     </Badge>
                                                     <span className="text-xs text-slate-500 font-mono">{log.id.split('-')[0]}</span>
                                                 </div>
                                             </div>
                                             
                                             <div className="space-y-2">
                                                 <JsonViewer data={log.essential_output} />
                                             </div>
                                         </div>
                                     ))}
                                 </div>
                             )}
                        </CardContent>
                    </Card>
                </TabsContent>

                 {/* Config Content */}
                 <TabsContent value="config" className="mt-6">
                    <Card className="bg-slate-950 border-slate-800">
                        <CardHeader>
                            <CardTitle>Configuration Snapshot</CardTitle>
                            <CardDescription>Configuration used when this deployment started.</CardDescription>
                        </CardHeader>
                        <CardContent>
                             <JsonViewer data={deployment.config_snapshot} />
                        </CardContent>
                    </Card>
                 </TabsContent>
            </Tabs>
        </div>
    );
}
