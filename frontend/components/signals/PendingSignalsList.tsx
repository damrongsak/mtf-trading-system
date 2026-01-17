
import React, { useEffect, useState } from 'react';
import { getDetectedSignals, approveSignal, rejectSignal } from '@/lib/api/signals';
import { Signal, SignalStatus } from '@/lib/api/types';
import { CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';

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
            console.error("Failed to fetch pending signals", error);
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
            alert("Failed to approve signal: " + e);
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
                <ClockIcon className="w-6 h-6" />
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
                        
                        <div className="text-sm text-gray-300 mb-4 space-y-1">
                            <p>Price: <span className="font-mono">{signal.entry_price || signal.price}</span></p>
                            <p>Strategy: <span className="text-blue-300">{signal.strategy_name?.replace('Strategy-', '')}</span></p>
                            <p className="text-xs italic mt-2 opacity-70">"{signal.reason}"</p>
                        </div>

                        <div className="flex gap-2 mt-4 pt-3 border-t border-gray-700">
                            <button
                                onClick={() => signal.id && handleApprove(signal.id)}
                                disabled={processingId === signal.id}
                                className="flex-1 bg-green-600 hover:bg-green-500 text-white py-2 rounded flex justify-center items-center gap-1 disabled:opacity-50 transition-colors"
                            >
                                {processingId === signal.id ? "..." : <><CheckCircleIcon className="w-4 h-4" /> Approve</>}
                            </button>
                            <button
                                onClick={() => signal.id && handleReject(signal.id)}
                                disabled={processingId === signal.id}
                                className="flex-1 bg-gray-700 hover:bg-red-600/80 text-white py-2 rounded flex justify-center items-center gap-1 disabled:opacity-50 transition-colors"
                            >
                                <XCircleIcon className="w-4 h-4" /> Reject
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
