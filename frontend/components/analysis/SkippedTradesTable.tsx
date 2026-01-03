'use client';

import React, { useEffect, useState } from 'react';
import { OpportunityLog } from '@/lib/api/types';
import { getOpportunities } from '@/lib/api/analysis';

export function SkippedTradesTable() {
    const [logs, setLogs] = useState<OpportunityLog[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchLogs = async () => {
        try {
            setLoading(true);
            const data = await getOpportunities(50);
            setLogs(data);
        } catch (error) {
            console.error('Failed to fetch opportunity logs:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
        const interval = setInterval(fetchLogs, 30000); // Poll every 30s
        return () => clearInterval(interval);
    }, []);

    if (loading && logs.length === 0) {
        return <div className="animate-pulse h-32 bg-gray-800/30 rounded-xl" />;
    }

    if (logs.length === 0) {
        return (
            <div className="text-center py-8 text-gray-500 bg-gray-800/30 rounded-xl border border-gray-700/50">
                No skipped trades recorded yet.
            </div>
        );
    }

    return (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
             <div className="flex justify-between items-center p-4 border-b border-gray-800">
                <h3 className="text-lg font-medium text-gray-200">Filtered Opportunities (Skipped Trades)</h3>
                <button onClick={fetchLogs} className="text-sm text-accent-blue hover:text-white transition-colors">
                    Refresh
                </button>
            </div>
            
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-400">
                    <thead className="bg-gray-900 text-gray-500 uppercase font-medium">
                        <tr>
                            <th className="px-6 py-3">Time</th>
                            <th className="px-6 py-3">Symbol</th>
                            <th className="px-6 py-3">Direction</th>
                             <th className="px-6 py-3">Filter Reason</th>
                            <th className="px-6 py-3 text-right">Value / Threshold</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                        {logs.map((log) => (
                            <tr key={log.id} className="hover:bg-gray-800/30 transition-colors">
                                <td className="px-6 py-3 whitespace-nowrap text-gray-300">
                                    {new Date(log.timestamp).toLocaleString(undefined, {
                                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                    })}
                                </td>
                                <td className="px-6 py-3 font-medium text-white">{log.symbol}</td>
                                <td className={`px-6 py-3 font-medium ${log.direction === 'BULLISH' ? 'text-green-400' : 'text-red-400'}`}>
                                    {log.direction}
                                </td>
                                <td className="px-6 py-3">
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-400/10 text-red-400 border border-red-400/20">
                                        {log.filter_name}
                                    </span>
                                    {log.reason && <div className="text-xs text-gray-500 mt-1">{log.reason}</div>}
                                </td>
                                <td className="px-6 py-3 text-right font-mono">
                                    <div className="text-gray-300">{log.filter_value?.toFixed(4) ?? 'N/A'}</div>
                                    <div className="text-xs text-gray-500">
                                        vs {log.threshold_value?.toFixed(4) ?? 'N/A'}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
