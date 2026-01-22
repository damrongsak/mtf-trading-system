"use client";

import React, { useEffect, useState } from 'react';
import { getDriftAnalysis, DriftAnalysisResponse, getOpportunities } from '@/lib/api/analysis';
import { OpportunityLog } from '@/lib/api/types';
import { AlertTriangle, CheckCircle, Activity, ShieldAlert, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { logger } from '@/lib/api/app-logger';

export const DriftDashboard: React.FC = () => {
    const [data, setData] = useState<DriftAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        try {
            const result = await getDriftAnalysis(24);
            setData(result);
            setError(null);
        } catch (error) {
            logger.error("Failed to fetch drift analysis", error);
            setError("Failed to load analysis");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 60000); // Refresh every minute
        return () => clearInterval(interval);
    }, []);

    if (loading && !data) {
        return <div className="p-8 text-center text-gray-500">Analyze System Drift...</div>;
    }

    if (error) {
        return (
            <div className="p-4 border border-red-900/50 bg-red-900/20 text-red-500 rounded-lg text-center">
                {error}
                <Button variant="ghost" size="sm" onClick={() => fetchData()} className="ml-4">Retry</Button>
            </div>
        );
    }

    if (!data) return null;

    const isDrifting = data.status === 'DRIFT_WARNING';
    const isHealthy = data.status === 'HEALTHY';
    
    // Calculate color based on filter rate
    const filterRate = data.filter_rate ?? 0;
    const rateColor = filterRate > 0.8 ? 'text-red-500' : filterRate > 0.5 ? 'text-yellow-500' : 'text-green-500';

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex justify-between items-center mb-6">
                <div>
                   <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                       System Drift Monitor
                   </h2>
                   <p className="text-sm text-gray-500">Automated Strategy Feedback Loop (24h Window)</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => fetchData()} disabled={loading}>
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Status Card */}
                <Card className={`border-l-4 ${isHealthy ? 'border-l-green-500' : isDrifting ? 'border-l-red-500' : 'border-l-yellow-500'} bg-gray-900/50`}>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-gray-400">System Status</CardTitle>
                        {isHealthy ? <CheckCircle className="h-4 w-4 text-green-500" /> : <AlertTriangle className="h-4 w-4 text-yellow-500" />}
                    </CardHeader>
                    <CardContent>
                        <div className={`text-2xl font-bold ${isHealthy ? 'text-green-400' : isDrifting ? 'text-red-400' : 'text-yellow-400'}`}>
                            {data.status}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            {isDrifting ? "Strategy parameters may be obsolete." : "Strategy matches market regime."}
                        </p>
                    </CardContent>
                </Card>

                {/* Filter Rate Card */}
                <Card className="bg-gray-900/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-gray-400">Rejection Rate</CardTitle>
                        <Activity className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className={`text-2xl font-bold ${rateColor}`}>
                            {(filterRate * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                            <span className="text-white">{data.opportunity_count || 0}</span> skipped / <span className="text-white">{(data.signal_count || 0) + (data.opportunity_count || 0)}</span> total
                        </div>
                        <div className="w-full bg-gray-700 h-1.5 rounded-full mt-3 overflow-hidden">
                            <div 
                                className={`h-full ${filterRate > 0.8 ? 'bg-red-500' : 'bg-blue-500'}`} 
                                style={{ width: `${Math.min(filterRate * 100, 100)}%` }}
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* Top Blocker Card */}
                <Card className="bg-gray-900/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-gray-400">Primary Blocker</CardTitle>
                        <ShieldAlert className="h-4 w-4 text-orange-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-xl font-bold text-gray-200 truncate" title={data.top_rejection_reason}>
                            {data.top_rejection_reason || "None"}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Most frequent reason for skipped trades.
                        </p>
                    </CardContent>
                </Card>
            </div>
            
            {/* Context Explanation */}
            <div className="mt-8 p-4 rounded-lg bg-blue-500/5 border border-blue-500/10">
                <h4 className="text-sm font-semibold text-blue-400 mb-2">What is Drift?</h4>
                <p className="text-xs text-gray-400 leading-relaxed">
                    System Drift occurs when the strategy logic (the &quot;Edge&quot;) becomes misaligned with the current market behavior (the &quot;Regime&quot;).
                    A high <strong>Rejection Rate (&gt;80%)</strong> means the bot is finding technical setups but refusing to take them due to filters (Volatility, Sentiment, RRR).
                    If Drift persists, consider re-optimizing the strategy parameters or switching regimes.
                </p>
            </div>
        </div>
    );
};
