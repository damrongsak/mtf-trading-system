'use client';

import React, { useEffect, useState } from 'react';
import { LatencyHeatmap } from '@/components/institutional/LatencyHeatmap';
import { PerformanceGapChart } from '@/components/institutional/PerformanceGapChart';
import { RejectionAuditCard } from '@/components/institutional/RejectionAuditCard';
import { analyticsApi } from '@/lib/api/analytics';
import { LatencyBucket, PerformanceComparisonItem, RejectionReasonSummary } from '@/lib/api/types';
import { logger } from '@/lib/api/app-logger';

export default function InstitutionalDashboard() {
  const [latencyData, setLatencyData] = useState<LatencyBucket[]>([]);
  const [performanceData, setPerformanceData] = useState<PerformanceComparisonItem[]>([]);
  const [rejections, setRejections] = useState<RejectionReasonSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [latency, performance, rejectionLogs] = await Promise.all([
          analyticsApi.getLatencyHeatmap(),
          analyticsApi.getPerformanceComparison(),
          analyticsApi.getExecutionRejections(),
        ]);
        
        setLatencyData(latency.buckets);
        setPerformanceData(performance.comparisons);
        setRejections(rejectionLogs.rejections);
      } catch (error) {
        logger.error('Failed to fetch institutional dashboard data', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-red-400 via-accent-blue to-accent-green bg-clip-text text-transparent">
            Institutional Execution Dashboard
          </h1>
          <p className="text-gray-400 mt-1">High-fidelity monitoring of execution quality and system reliability</p>
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

      {/* Primary Row: Heatmap & Rejections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
            <LatencyHeatmap data={latencyData} loading={loading} />
        </div>
        <div className="h-full">
            <RejectionAuditCard rejections={rejections} loading={loading} />
        </div>
      </div>

      {/* Secondary Row: Performance Gap & Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
            <PerformanceGapChart data={performanceData} loading={loading} />
        </div>
        <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 flex flex-col justify-center">
            <h3 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">Dashboard Metrics</h3>
            <div className="space-y-6">
                <div>
                    <span className="text-[10px] text-gray-500 uppercase font-mono block mb-1">Total Latency Buckets</span>
                    <span className="text-3xl font-bold text-gray-100 font-mono">{latencyData.length}</span>
                </div>
                <div>
                    <span className="text-[10px] text-gray-500 uppercase font-mono block mb-1">Execution Comparisons</span>
                    <span className="text-3xl font-bold text-accent-blue font-mono">{performanceData.length}</span>
                </div>
                <div>
                    <span className="text-[10px] text-gray-500 uppercase font-mono block mb-1">Peak Rejection Category</span>
                    <span className="text-xl font-bold text-red-400 truncate block">
                        {rejections.length > 0 ? rejections.sort((a,b) => b.count - a.count)[0].reason : 'None'}
                    </span>
                </div>
            </div>
            
            <div className="mt-8 pt-8 border-t border-gray-800">
                <p className="text-[10px] text-gray-500 leading-relaxed italic">
                    Note: Latency is measured from signal generation (ns) to broker confirmation (ns). 
                    Performance gap compares Shadow vs Live P&L for identical signal IDs.
                </p>
            </div>
        </div>
      </div>
    </div>
  );
}
