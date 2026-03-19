'use client';

import React from 'react';
import { RejectionReasonSummary } from '@/lib/api/types';

interface RejectionAuditCardProps {
  rejections: RejectionReasonSummary[];
  loading?: boolean;
}

export const RejectionAuditCard: React.FC<RejectionAuditCardProps> = ({ rejections, loading }) => {
  if (loading) {
    return (
      <div className="h-[300px] w-full bg-gray-950/50 rounded-xl border border-gray-800 animate-pulse flex items-center justify-center">
        <span className="text-gray-500">Loading rejection logs...</span>
      </div>
    );
  }

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl h-full flex flex-col">
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
            <h3 className="text-sm font-semibold text-gray-200">Rejection Audit Log</h3>
        </div>
        <span className="text-[10px] uppercase font-mono text-gray-400 px-2 py-0.5 bg-gray-900 rounded border border-gray-800">
            Real-time Monitoring
        </span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 font-mono text-[11px] space-y-3">
        {rejections.length === 0 ? (
          <div className="text-gray-600 text-center py-10 italic">
            No execution rejections recorded. System integrity at 100%.
          </div>
        ) : (
          rejections.map((error, idx) => (
            <div key={idx} className="bg-gray-900/40 p-3 rounded border border-gray-800/50 hover:border-red-500/30 transition-colors">
              <div className="flex justify-between items-start mb-1">
                <span className="text-red-400 font-bold">[REJECTED]</span>
                <span className="text-gray-500 text-[10px]">
                  {new Date(error.latest_at).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-gray-300 mb-1 leading-relaxed">{error.reason}</p>
              <div className="flex items-center gap-2 text-gray-500">
                <span>Frequency:</span>
                <span className="bg-gray-800 px-1.5 py-0.5 rounded text-gray-300 font-bold">{error.count}</span>
              </div>
            </div>
          ))
        )}
      </div>
      
      <div className="p-3 bg-red-950/10 border-t border-gray-800 flex items-center justify-center gap-2">
          <svg className="w-3 h-3 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-[10px] text-gray-400">Total System Rejections: <strong className="text-red-400">{rejections.reduce((acc, curr) => acc + curr.count, 0)}</strong></span>
      </div>
    </div>
  );
};
