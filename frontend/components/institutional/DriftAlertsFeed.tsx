'use client';

import React from 'react';
import { DriftAlert } from '@/lib/api/types';
import { AlertTriangle, ShieldAlert, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface DriftAlertsFeedProps {
  alerts: DriftAlert[];
  loading?: boolean;
}

export const DriftAlertsFeed: React.FC<DriftAlertsFeedProps> = ({ alerts, loading }) => {
  if (loading) {
    return (
      <div className="h-[300px] w-full bg-gray-950/50 rounded-xl border border-gray-800 animate-pulse flex items-center justify-center">
        <span className="text-gray-500">Loading system alerts...</span>
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="h-[300px] w-full bg-gray-950/50 rounded-xl border border-gray-800 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-10 h-10 bg-green-500/10 rounded-full flex items-center justify-center mb-3">
            <ShieldAlert className="w-5 h-5 text-green-500" />
        </div>
        <h4 className="text-gray-300 font-medium text-sm">System Healthy</h4>
        <p className="text-gray-500 text-[10px]">No active drift alerts detected between brokers.</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-5 overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-md font-semibold text-gray-200 flex items-center gap-2">
            System Integrity Feed
        </h3>
        <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-500 text-[10px] rounded-full font-mono">
            {alerts.length} Active
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 custom-scrollbar">
        {alerts.map((alert, idx) => {
          const isCritical = alert.severity === 'CRITICAL';
          return (
            <div 
              key={`${alert.timestamp}-${idx}`}
              className={`p-3 rounded-lg border ${
                isCritical ? 'bg-red-500/5 border-red-500/20' : 'bg-orange-500/5 border-orange-500/20'
              } transition-colors hover:bg-white/5`}
            >
              <div className="flex gap-3">
                <div className={`mt-0.5 ${isCritical ? 'text-red-500' : 'text-orange-500'}`}>
                  {isCritical ? <ShieldAlert className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-start mb-1">
                    <span className={`text-[11px] font-bold uppercase tracking-tight ${isCritical ? 'text-red-400' : 'text-orange-400'}`}>
                      {alert.type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-[9px] text-gray-500 flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" />
                      {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-300 leading-snug">
                    {alert.broker && <b className="text-gray-200">{alert.broker}: </b>}
                    Significant drift detected in {alert.symbol || 'portfolio'}. 
                    {alert.relative_drift && ` Impact: ${(alert.relative_drift * 100).toFixed(2)}%`}
                  </p>
                  {alert.details && (
                    <div className="mt-2 text-[10px] bg-black/40 p-1.5 rounded font-mono text-gray-400 overflow-x-auto">
                        <pre>{JSON.stringify(alert.details, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
