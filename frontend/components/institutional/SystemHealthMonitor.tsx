'use client';

import React from 'react';
import { QueueHealth, PipelineStatus } from '@/lib/api/types';
import { Activity, Server, Database, Zap, AlertCircle, CheckCircle2 } from 'lucide-react';

interface SystemHealthMonitorProps {
    queueHealth?: QueueHealth;
    pipelineStatus?: PipelineStatus;
    loading: boolean;
}

export function SystemHealthMonitor({ queueHealth, pipelineStatus, loading }: SystemHealthMonitorProps) {
    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse">
                {[1, 2].map((i) => (
                    <div key={i} className="h-64 bg-gray-900/50 border border-gray-800 rounded-xl" />
                ))}
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Queue Health Card */}
            <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-accent-blue/10 rounded-lg">
                            <Activity className="w-5 h-5 text-accent-blue" />
                        </div>
                        <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">Execution Queue</h3>
                    </div>
                    {queueHealth?.system_halted ? (
                        <span className="flex items-center gap-1.5 px-2 py-1 bg-red-400/10 text-red-400 text-[10px] font-bold rounded-full border border-red-400/20">
                            <AlertCircle className="w-3 h-3" /> HALTED
                        </span>
                    ) : (
                        <span className="flex items-center gap-1.5 px-2 py-1 bg-accent-green/10 text-accent-green text-[10px] font-bold rounded-full border border-accent-green/20">
                            <CheckCircle2 className="w-3 h-3" /> ACTIVE
                        </span>
                    )}
                </div>

                <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-1">
                        <span className="text-[10px] text-gray-500 uppercase font-mono block">Priority</span>
                        <span className={`text-2xl font-bold font-mono ${queueHealth?.priority_queue ? 'text-accent-blue' : 'text-gray-400'}`}>
                            {queueHealth?.priority_queue ?? 0}
                        </span>
                    </div>
                    <div className="space-y-1">
                        <span className="text-[10px] text-gray-500 uppercase font-mono block">Commands</span>
                        <span className="text-2xl font-bold text-gray-100 font-mono">
                            {queueHealth?.default_queue ?? 0}
                        </span>
                    </div>
                    <div className="space-y-1">
                        <span className="text-[10px] text-gray-500 uppercase font-mono block">Dead Letter</span>
                        <span className={`text-2xl font-bold font-mono ${queueHealth?.dead_letter_queue ? 'text-red-400' : 'text-gray-400'}`}>
                            {queueHealth?.dead_letter_queue ?? 0}
                        </span>
                    </div>
                </div>

                <div className="mt-8 pt-6 border-t border-gray-800">
                    <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">Recently Processed</span>
                        <span className="text-accent-blue font-mono font-bold">{queueHealth?.recently_processed ?? 0} orders</span>
                    </div>
                </div>
            </div>

            {/* Pipeline Status Card */}
            <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-400/10 rounded-lg">
                            <Zap className="w-5 h-5 text-purple-400" />
                        </div>
                        <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">AI Orchestration</h3>
                    </div>
                    <span className="text-[10px] text-gray-500 font-mono">
                        {pipelineStatus?.overall_status ?? 'UNKNOWN'}
                    </span>
                </div>

                <div className="space-y-4">
                    {pipelineStatus?.stages.map((stage) => (
                        <div key={stage.name} className="flex items-center justify-between group">
                            <div className="flex items-center gap-3">
                                <div className={`w-1.5 h-1.5 rounded-full ${
                                    stage.status === 'COMPLETED' ? 'bg-accent-green shadow-[0_0_8px_rgba(74,222,128,0.5)]' :
                                    stage.status === 'RUNNING' ? 'bg-accent-blue animate-pulse shadow-[0_0_8px_rgba(96,165,250,0.5)]' :
                                    stage.status === 'FAILED' ? 'bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.5)]' :
                                    'bg-gray-700'
                                }`} />
                                <span className="text-xs text-gray-300 group-hover:text-white transition-colors">{stage.name}</span>
                            </div>
                            <span className="text-[10px] text-gray-500 font-mono">
                                {stage.duration_ms ? `${stage.duration_ms}ms` : '-'}
                            </span>
                        </div>
                    )) ?? (
                        <div className="flex flex-col items-center justify-center h-full py-8 text-gray-600">
                            <Server className="w-8 h-8 mb-2 opacity-20" />
                            <p className="text-xs italic">No pipeline metrics available</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
