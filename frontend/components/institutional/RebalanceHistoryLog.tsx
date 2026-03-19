'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { History, Brain, AlertTriangle, User, Bot, RefreshCw } from 'lucide-react';
import { analyticsApi } from '@/lib/api/analytics';
import { RebalanceHistoryItem } from '@/lib/api/types';
import { logger } from '@/lib/api/app-logger';

interface RebalanceHistoryLogProps {
    fundId?: string;
}

const TRIGGER_LABELS: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    MANUAL: { label: 'Manual', color: 'text-accent-blue', icon: <User className="w-3 h-3" /> },
    AUTONOMOUS: { label: 'Autonomous', color: 'text-amber-400', icon: <Bot className="w-3 h-3" /> },
    SENTIMENT_DRIFT: { label: 'Sentiment Drift', color: 'text-red-400', icon: <AlertTriangle className="w-3 h-3" /> },
};

export function RebalanceHistoryLog({ fundId }: RebalanceHistoryLogProps) {
    const [history, setHistory] = useState<RebalanceHistoryItem[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchHistory = useCallback(async () => {
        try {
            setLoading(true);
            const res = await analyticsApi.getRebalanceHistory(fundId, 10);
            if (res.data) {
                setHistory(res.data);
            }
        } catch (e) {
            logger.error('Failed to fetch rebalance history', e);
        } finally {
            setLoading(false);
        }
    }, [fundId]);

    useEffect(() => {
        fetchHistory();
    }, [fetchHistory]);

    if (!history.length && !loading) {
        return (
            <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-gray-800 rounded-lg">
                        <History className="w-5 h-5 text-gray-500" />
                    </div>
                    <h3 className="font-semibold text-gray-100">Rebalance History</h3>
                </div>
                <p className="text-xs text-gray-600 text-center py-8">No rebalancing events recorded yet.</p>
            </div>
        );
    }

    return (
        <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-accent-blue/10 rounded-lg">
                        <History className="w-5 h-5 text-accent-blue" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-gray-100">Rebalance History</h3>
                        <p className="text-[10px] text-gray-500 mt-0.5">AI-driven risk adjustment audit trail</p>
                    </div>
                </div>
                <button onClick={fetchHistory} disabled={loading} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
                    <RefreshCw className={`w-4 h-4 text-gray-500 ${loading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            {loading && !history.length ? (
                <div className="flex justify-center py-8">
                    <RefreshCw className="w-6 h-6 text-accent-blue animate-spin opacity-30" />
                </div>
            ) : (
                <div className="relative">
                    {/* Timeline line */}
                    <div className="absolute left-[17px] top-2 bottom-2 w-px bg-gray-800" />

                    <div className="space-y-4">
                        {history.map((item) => {
                            const trigger = TRIGGER_LABELS[item.trigger_type] || TRIGGER_LABELS.MANUAL;
                            const prevDD = item.previous_config?.max_drawdown_threshold;
                            const newDD = item.applied_config?.max_drawdown_threshold;
                            const prevRisk = item.previous_config?.risk_percentage;
                            const newRisk = item.applied_config?.risk_percentage;

                            return (
                                <div key={item.id} className="relative pl-10 group">
                                    {/* Timeline dot */}
                                    <div className={`absolute left-[11px] top-2 w-[13px] h-[13px] rounded-full border-2 border-gray-800 bg-gray-950 flex items-center justify-center ${trigger.color}`}>
                                        <div className={`w-[5px] h-[5px] rounded-full ${item.trigger_type === 'SENTIMENT_DRIFT' ? 'bg-red-400' : item.trigger_type === 'AUTONOMOUS' ? 'bg-amber-400' : 'bg-accent-blue'}`} />
                                    </div>

                                    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-colors">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <span className={`flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider ${trigger.color}`}>
                                                    {trigger.icon}
                                                    {trigger.label}
                                                </span>
                                                {item.drift_score !== null && (
                                                    <span className="text-[9px] text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
                                                        drift: {item.drift_score.toFixed(2)}
                                                    </span>
                                                )}
                                            </div>
                                            <span className="text-[9px] text-gray-600 font-mono">
                                                {new Date(item.created_at).toLocaleString()}
                                            </span>
                                        </div>

                                        <p className="text-[11px] text-gray-400 leading-relaxed mb-3 line-clamp-2">
                                            {item.reasoning}
                                        </p>

                                        <div className="grid grid-cols-2 gap-2">
                                            <div className="flex items-center gap-2 text-[10px]">
                                                <span className="text-gray-600">DD:</span>
                                                <span className="text-gray-500 line-through">{prevDD}%</span>
                                                <span className="text-gray-200 font-bold">{newDD}%</span>
                                            </div>
                                            <div className="flex items-center gap-2 text-[10px]">
                                                <span className="text-gray-600">Risk:</span>
                                                <span className="text-gray-500 line-through">{typeof prevRisk === 'number' ? (prevRisk * 100).toFixed(2) : prevRisk}%</span>
                                                <span className="text-gray-200 font-bold">{typeof newRisk === 'number' ? (newRisk * 100).toFixed(2) : newRisk}%</span>
                                            </div>
                                        </div>

                                        <div className="mt-2 flex items-center gap-1 text-[9px] text-gray-600">
                                            <Brain className="w-3 h-3" />
                                            <span>Applied by: {item.applied_by === 'SYSTEM' ? 'Autonomous AI' : item.applied_by.substring(0, 8) + '...'}</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
