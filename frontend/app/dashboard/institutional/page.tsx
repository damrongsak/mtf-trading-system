'use client';

import React, { useEffect, useState } from 'react';
import { LatencyHeatmap } from '@/components/institutional/LatencyHeatmap';
import { PerformanceGapChart } from '@/components/institutional/PerformanceGapChart';
import { RejectionAuditCard } from '@/components/institutional/RejectionAuditCard';
import { AccountHistoryGraph } from '@/components/institutional/AccountHistoryGraph';
import { HRPWeightsDisplay } from '@/components/institutional/HRPWeightsDisplay';
import { DriftAlertsFeed } from '@/components/institutional/DriftAlertsFeed';
import { SystemHealthMonitor } from '@/components/institutional/SystemHealthMonitor';
import { analyticsApi } from '@/lib/api/analytics';
import { LatencyBucket, PerformanceComparisonItem, RejectionReasonSummary, AccountHistoryItem, DriftAlert, QueueHealth, PipelineStatus } from '@/lib/api/types';
import { logger } from '@/lib/api/app-logger';
import { useAccount } from '@/context/AccountContext';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { RiskControlPanel } from '@/components/institutional/RiskControlPanel';
import { RebalanceHistoryLog } from '@/components/institutional/RebalanceHistoryLog';

export default function InstitutionalDashboard() {
  const { selectedAccount, isLoading: accountLoading } = useAccount();
  const [latencyData, setLatencyData] = useState<LatencyBucket[]>([]);
  const [performanceData, setPerformanceData] = useState<PerformanceComparisonItem[]>([]);
  const [rejections, setRejections] = useState<RejectionReasonSummary[]>([]);
  const [history, setHistory] = useState<AccountHistoryItem[]>([]);
  const [hrpWeights, setHrpWeights] = useState<Record<string, number>>({});
  const [alerts, setAlerts] = useState<DriftAlert[]>([]);
  const [queueHealth, setQueueHealth] = useState<QueueHealth>();
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [latency, performance, rejectionLogs, driftAlerts, qHealth, pStatus] = await Promise.all([
          analyticsApi.getLatencyHeatmap(),
          analyticsApi.getPerformanceComparison(),
          analyticsApi.getExecutionRejections(),
          analyticsApi.getDriftAlerts(),
          analyticsApi.getQueueHealth(),
          analyticsApi.getPipelineStatus()
        ]);
        
        setLatencyData(latency.buckets);
        setPerformanceData(performance.comparisons);
        setRejections(rejectionLogs.rejections);
        setAlerts(driftAlerts.alerts);
        setQueueHealth(qHealth.data);
        setPipelineStatus(pStatus.data);
      } catch (error) {
        logger.error('Failed to fetch institutional dashboard data', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();

    // Set up polling for health metrics (every 30s)
    const interval = setInterval(async () => {
        try {
            const [qHealth, pStatus] = await Promise.all([
                analyticsApi.getQueueHealth(),
                analyticsApi.getPipelineStatus()
            ]);
            setQueueHealth(qHealth.data);
            setPipelineStatus(pStatus.data);
        } catch (e) {
            logger.warn('Failed to poll system health', e);
        }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    async function fetchAccountSpecifics() {
      if (!selectedAccount) return;
      try {
        const [accHistory, weights] = await Promise.all([
          analyticsApi.getAccountHistory(selectedAccount.id),
          analyticsApi.getHRPWeights(selectedAccount.fund_id)
        ]);
        setHistory(accHistory.history);
        setHrpWeights(weights.weights);
      } catch (error) {
        logger.error('Failed to fetch account specific analytics', error);
      }
    }
    fetchAccountSpecifics();
  }, [selectedAccount]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-red-400 via-accent-blue to-accent-green bg-clip-text text-transparent">
            Institutional Execution Dashboard
          </h1>
          <p className="text-gray-400 mt-1">Institutional monitoring and execution health analysis.</p>
        </div>
        <div className="flex gap-3">
            <button 
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:border-gray-700 transition-colors"
            >
                Refresh Data
            </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
            <AccountHistoryGraph data={history} loading={loading || accountLoading} />
        </div>
        <div>
            <HRPWeightsDisplay weights={hrpWeights} loading={loading || accountLoading} />
        </div>
      </div>

      <Tabs defaultValue="execution" className="w-full">
        <TabsList className="bg-gray-900/50 border border-gray-800 p-1 mb-6">
          <TabsTrigger value="execution">Execution Hub</TabsTrigger>
          <TabsTrigger value="latency">Latency Matrix</TabsTrigger>
          <TabsTrigger value="performance">Performance Analytics</TabsTrigger>
          <TabsTrigger value="system">System Integrity</TabsTrigger>
          <TabsTrigger value="risk">Risk Controls</TabsTrigger>
        </TabsList>

        <TabsContent value="execution">
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
            <div className="xl:col-span-3">
              <RejectionAuditCard rejections={rejections} loading={loading} />
            </div>
            <div className="xl:col-span-1">
              <DriftAlertsFeed alerts={alerts} loading={loading} />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="latency">
           <LatencyHeatmap data={latencyData} loading={loading} />
        </TabsContent>

        <TabsContent value="performance">
           <PerformanceGapChart data={performanceData} loading={loading} />
        </TabsContent>

        <TabsContent value="system">
            <div className="space-y-6">
                <SystemHealthMonitor 
                    queueHealth={queueHealth} 
                    pipelineStatus={pipelineStatus} 
                    loading={loading} 
                />
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <DriftAlertsFeed alerts={alerts} loading={loading} />
                    <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6 flex flex-col justify-center">
                        <h3 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">Broker Sync Health</h3>
                        <div className="space-y-6">
                            <div>
                                <span className="text-[10px] text-gray-500 uppercase font-mono block mb-1">Total Latency Buckets</span>
                                <span className="text-3xl font-bold text-gray-100 font-mono">{latencyData.length}</span>
                            </div>
                            <div>
                                <span className="text-[10px] text-gray-500 uppercase font-mono block mb-1">Execution Comparisons</span>
                                <span className="text-3xl font-bold text-accent-blue font-mono">{performanceData.length}</span>
                            </div>
                        </div>
                        
                        <div className="mt-8 pt-8 border-t border-gray-800">
                            <p className="text-[10px] text-gray-500 leading-relaxed italic">
                                Sync monitoring detects and alerts on status drifts between the internal state and broker execution reports.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </TabsContent>
        <TabsContent value="risk">
           <div className="space-y-6">
             <RiskControlPanel fundId={selectedAccount?.fund_id} />
             <RebalanceHistoryLog fundId={selectedAccount?.fund_id} />
           </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
