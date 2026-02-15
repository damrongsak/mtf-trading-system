'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Signal, SignalStatus } from '@/lib/api/types';
import { getBatchSignals, approveSignal, rejectSignal } from '@/lib/api/signals';
import { TradeModal } from './TradeModal';
import { logger } from '@/lib/api/app-logger';

export const RecentSignalsCard: React.FC = () => {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchSignals = async () => {
    try {
      // setLoading(true); // Don't show loading spinner on refresh
      const data = await getBatchSignals("OANDA");
      // Sort logic if needed, but backend mostly returns recent. 
      // Let's sort by timestamp desc just in case.
      const sorted = data
        .filter(s => s.direction !== 'NEUTRAL')
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      setSignals(sorted);
    } catch (e) {
      logger.error("Failed to fetch signals", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 300000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, []);

  const handleTradeClick = (signal: Signal) => {
    setSelectedSignal(signal);
    setIsModalOpen(true);
  };

  const handleApprove = async (signalId: string) => {
    try {
      setLoading(true);
      await approveSignal(signalId);
      await fetchSignals();
    } catch (e) {
      logger.error("Failed to approve signal", e);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async (signalId: string) => {
    try {
      setLoading(true);
      await rejectSignal(signalId);
      await fetchSignals();
    } catch (e) {
      logger.error("Failed to reject signal", e);
    } finally {
      setLoading(false);
    }
  };

  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'LONG':
      case 'BULLISH':
        return 'text-accent-green bg-accent-green/10 border-accent-green/20';
      case 'SHORT':
      case 'BEARISH':
        return 'text-red-400 bg-red-400/10 border-red-400/20';
      default:
        return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
    }
  };

  const formatPrice = (price?: number) => {
    if (!price) return '-';
    return price.toFixed(5);
  };
  
  const formatTime = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading && signals.length === 0) {
     return (
        <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 min-h-[250px]">
            <h2 className="text-xl font-bold text-gray-100 mb-4">Recent Signals</h2>
            <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-12 bg-gray-800/30 animate-pulse rounded-lg" />
                ))}
            </div>
        </div>
     );
  }

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-100">Recent Signals</h2>
        <div className="flex gap-4 items-center">
            <span className="text-xs text-gray-500">Source: OANDA (System Default)</span>
            <button onClick={() => fetchSignals()} className="text-gray-400 hover:text-white transition">
                ↻
            </button>
        </div>
      </div>

      <div className="flex-1 overflow-x-auto max-h-[250px] scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent">
        <table className="w-full relative">
          <thead className="sticky top-0 bg-gray-950/90 backdrop-blur-sm z-10 shadow-sm">
            <tr className="border-b border-gray-800 text-left">
              <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase">Symbol</th>
              <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase">Dir</th>
              <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase">Entry</th>
              <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase hidden md:table-cell">SL</th>
              <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase hidden md:table-cell">TP</th>
              <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase hidden lg:table-cell">Time</th>
              <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {signals.length === 0 ? (
                <tr>
                    <td colSpan={7} className="text-center py-8 text-gray-500">
                        No active signals found.
                    </td>
                </tr>
            ) : (
                signals.map((signal) => (
                    <tr key={`${signal.symbol}-${signal.timestamp}`} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors group">
                        <td className="py-3 px-4 font-mono text-gray-200 font-medium">
                            {signal.symbol.replace('_', '/')}
                        </td>
                        <td className="py-3 px-4">
                            <span className={`inline-block px-2 py-1 rounded text-[10px] font-bold border ${getDirectionColor(signal.direction)}`}>
                                {signal.direction}
                            </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-gray-300 text-sm">{formatPrice(signal.entry_price)}</td>
                        <td className="py-3 px-4 font-mono text-red-300/80 text-sm hidden md:table-cell">{formatPrice(signal.sl_price)}</td>
                        <td className="py-3 px-4 font-mono text-green-300/80 text-sm hidden md:table-cell">{formatPrice(signal.tp_price)}</td>
                        <td className="py-3 px-4 text-gray-500 text-xs hidden lg:table-cell">{formatTime(signal.timestamp)}</td>
                        <td className="py-3 px-4 text-right">
                            {signal.status === SignalStatus.PENDING_APPROVAL ? (
                                <div className="flex gap-2 justify-end">
                                    <button 
                                        onClick={() => signal.id && handleApprove(signal.id)}
                                        className="bg-accent-green/10 hover:bg-accent-green/20 text-accent-green border border-accent-green/50 rounded px-2 py-1 text-[10px] font-bold transition-colors"
                                    >
                                        Approve
                                    </button>
                                    <button 
                                        onClick={() => signal.id && handleReject(signal.id)}
                                        className="bg-red-400/10 hover:bg-red-400/20 text-red-400 border border-red-400/50 rounded px-2 py-1 text-[10px] font-bold transition-colors"
                                    >
                                        Reject
                                    </button>
                                </div>
                            ) : signal.direction !== 'NEUTRAL' && (
                                <button 
                                    onClick={() => handleTradeClick(signal)}
                                    className="bg-accent-blue/10 hover:bg-accent-blue/20 text-accent-blue border border-accent-blue/50 rounded px-3 py-1.5 text-xs font-medium transition-colors"
                                >
                                    Trade
                                </button>
                            )}
                        </td>
                    </tr>
                ))
            )}
          </tbody>
        </table>
      </div>
      
      <div className="mt-4 pt-3 border-t border-gray-800 text-center">
         <Link href="/signals" className="text-xs font-medium text-accent-blue hover:text-white transition-colors flex items-center justify-center gap-1">
             View All Signals
             <span className="text-[10px]">→</span>
         </Link>
      </div>

      <TradeModal 
        signal={selectedSignal} 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)}
        onTradeSuccess={() => {
            // Optional: Show notification or refresh
            fetchSignals();
        }}
      />
    </div>
  );
};
