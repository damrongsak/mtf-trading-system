import React, { useEffect, useState } from 'react';
import { getDetectedSignals, approveSignal, rejectSignal } from '@/lib/api/signals';
import { Signal, SignalStatus } from '@/lib/api/types';
import { CheckCircle2, XCircle, Clock } from 'lucide-react';
import { logger } from '@/lib/api/app-logger';

export function PendingSignalsList() {
    const [signals, setSignals] = useState<Signal[]>([]);
    const [loading, setLoading] = useState(true);
    const [processingId, setProcessingId] = useState<string | null>(null);

    const fetchPending = async () => {
        try {
            // Fetch signals with PENDING_APPROVAL status
            // Note: The getDetectedSignals API might need backend update to support filtering by status properly
            // If backend doesn't filter, we filter client side for now.
            const allSignals = await getDetectedSignals(50);
            const pending = allSignals.filter(s => s.status === SignalStatus.PENDING_APPROVAL);
            setSignals(pending);
        } catch (error) {
            logger.error("Failed to fetch pending signals", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPending();
        // Poll every 10 seconds
        const interval = setInterval(fetchPending, 10000);
        return () => clearInterval(interval);
    }, []);

    const handleApprove = async (id: string) => {
        if (!id) return;
        setProcessingId(id);
        try {
            await approveSignal(id);
            setSignals(prev => prev.filter(s => s.id !== id));
        } catch (e) {
            alert(`Failed to approve signal: ${e}`);
        } finally {
            setProcessingId(null);
        }
    };

    const handleReject = async (id: string) => {
        if (!id) return;
        setProcessingId(id);
        try {
            await rejectSignal(id);
            setSignals(prev => prev.filter(s => s.id !== id));
        } catch (e) {
            alert("Failed to reject signal: " + e);
        } finally {
            setProcessingId(null);
        }
    };

    if (loading && signals.length === 0) return null;
    if (signals.length === 0) return null;

    return (
        <div className="mb-8">
            <h2 className="text-xl font-semibold text-amber-400 mb-4 flex items-center gap-2">
                <Clock className="w-6 h-6" />
                Pending Approvals ({signals.length})
            </h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {signals.map(signal => (
                    <div key={signal.id} className="bg-gray-800/80 border border-amber-500/30 rounded-lg p-4 shadow-lg backdrop-blur">
                        <div className="flex justify-between items-start mb-2">
                            <div>
                                <h3 className="font-bold text-lg text-white">{signal.symbol}</h3>
                                <div className={`text-sm font-bold ${signal.direction === 'BULLISH' ? 'text-green-400' : 'text-red-400'}`}>
                                    {signal.direction}
                                </div>
                            </div>
                            <div className="text-xs text-gray-400 bg-gray-700 px-2 py-1 rounded">
                                {signal.timeframe}
                            </div>
                        </div>
                        
                        <div className="text-sm text-gray-300 mb-2 space-y-1">
                            <p>Price: <span className="font-mono">{signal.entry_price}</span></p>
                            <p>Strategy: <span className="text-blue-300">{signal.strategy_name?.replace('Strategy-', '')}</span></p>
                            <p className="text-xs italic mt-2 opacity-70">&quot;{signal.reason}&quot;</p>
                        </div>

                        {/* Rich Metadata Display */}
                        {signal.metadata && (
                            <div className="mb-4 p-2 rounded bg-black/30 border border-gray-700/30 space-y-1.5">
                                {signal.metadata.zone_type && (
                                    <div className="flex justify-between items-center text-[10px]">
                                        <span className="text-gray-500 uppercase tracking-wider">Zone</span>
                                        <span className={`font-bold ${signal.metadata.zone_type === 'MAJOR' ? 'text-orange-400' : 'text-blue-400'}`}>
                                            {signal.metadata.zone_type}
                                        </span>
                                    </div>
                                )}
                                
                                {signal.metadata.basis_offset !== undefined && (
                                    <div className="flex justify-between items-center text-[10px]">
                                        <span className="text-gray-500 uppercase tracking-wider">Basis</span>
                                        <span className="text-gray-300 font-mono">
                                            {signal.metadata.basis_offset > 0 ? '+' : ''}{Number(signal.metadata.basis_offset).toFixed(2)}
                                        </span>
                                    </div>
                                )}

                                {signal.metadata.confluence && signal.metadata.confluence.length > 0 && (
                                    <div className="pt-1 border-t border-gray-700/50">
                                        <div className="flex flex-wrap gap-1 mt-1">
                                            {signal.metadata.confluence.map((tag: string, i: number) => (
                                                <span key={i} className="px-1 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 text-[8px] font-bold uppercase">
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        <div className="flex gap-2 mt-4 pt-3 border-t border-gray-700">
                            <button
                                onClick={() => signal.id && handleApprove(signal.id)}
                                disabled={processingId === signal.id}
                                className="flex-1 bg-green-600 hover:bg-green-500 text-white py-2 rounded flex justify-center items-center gap-1 disabled:opacity-50 transition-colors"
                            >
                                {processingId === signal.id ? "..." : <><CheckCircle2 className="w-4 h-4" /> Approve</>}
                            </button>
                            <button
                                onClick={() => signal.id && handleReject(signal.id)}
                                disabled={processingId === signal.id}
                                className="flex-1 bg-gray-700 hover:bg-red-600/80 text-white py-2 rounded flex justify-center items-center gap-1 disabled:opacity-50 transition-colors"
                            >
                                <XCircle className="w-4 h-4" /> Reject
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
