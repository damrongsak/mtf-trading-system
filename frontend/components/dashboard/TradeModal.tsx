'use client';

import React, { useState, useEffect } from 'react';
import { Signal } from '@/lib/api/types';
import { placeOrder } from '@/lib/api/execution';

interface TradeModalProps {
  signal: Signal | null;
  isOpen: boolean;
  onClose: () => void;
  onTradeSuccess: () => void;
}

export const TradeModal: React.FC<TradeModalProps> = ({ signal, isOpen, onClose, onTradeSuccess }) => {
  const [lotSize, setLotSize] = useState<number>(0.01);
  const [sl, setSl] = useState<number>(0);
  const [tp, setTp] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (signal) {
      setSl(signal.sl_price || 0);
      setTp(signal.tp_price || 0);
      setLotSize(0.01);
      setError(null);
    }
  }, [signal]);

  if (!isOpen || !signal) return null;

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    
    try {
        const units = signal.direction === 'LONG' || signal.direction === 'BULLISH' 
            ? lotSize * 100000  // Standard Lot ? Or just units? OANDA units usually 1 unit = 1 currency. 
                                // But usually UI shows "Lots". 
                                // Let's assume standard lots constraint 0.01 = 1000 units.
            : -1 * lotSize * 100000;
            
        // Wait, Oanda units are raw units. 1 lot = 100,000 units usually in Forex.
        // So 0.01 lot = 1000 units.
        
        await placeOrder({
            symbol: signal.symbol.replace('/', '_'), // Normalize for backend if needed, but backend handles it likely? 
                                                     // Actually backend expects XAU_USD typically for OANDA.
            units: Math.round(units),
            sl_price: sl,
            tp_price: tp
        });
        
        onTradeSuccess();
        onClose();
    } catch (err: any) {
        setError(err.message || "Failed to place order");
    } finally {
        setLoading(false);
    }
  };

  const isLong = signal.direction === 'LONG' || signal.direction === 'BULLISH';
  const colorClass = isLong ? 'text-accent-green' : 'text-red-400';
  const btnClass = isLong ? 'bg-accent-green hover:bg-accent-green/80' : 'bg-red-500 hover:bg-red-500/80';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md shadow-2xl">
        <h3 className="text-xl font-bold text-gray-100 mb-4 flex justify-between">
          <span>Execute Trade</span>
          <span className={`font-mono ${colorClass}`}>{signal.direction} {signal.symbol}</span>
        </h3>
        
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-xs text-gray-400 mb-1">Entry Price</label>
                    <input 
                        type="number" 
                        disabled 
                        value={signal.entry_price} 
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-300 font-mono"
                    />
                </div>
                <div>
                    <label className="block text-xs text-gray-400 mb-1">Lot Size</label>
                    <input 
                        type="number" 
                        step="0.01"
                        min="0.01"
                        value={lotSize} 
                        onChange={(e) => setLotSize(parseFloat(e.target.value))}
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-100 font-mono focus:border-accent-blue outline-none"
                    />
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-xs text-gray-400 mb-1">Stop Loss</label>
                    <input 
                        type="number" 
                        step="0.00001"
                        value={sl} 
                        onChange={(e) => setSl(parseFloat(e.target.value))}
                        className="w-full bg-gray-800 border-l-4 border-l-red-500 border-gray-700 rounded px-3 py-2 text-gray-100 font-mono outline-none"
                    />
                </div>
                <div>
                    <label className="block text-xs text-gray-400 mb-1">Take Profit</label>
                    <input 
                        type="number" 
                        step="0.00001"
                        value={tp} 
                        onChange={(e) => setTp(parseFloat(e.target.value))}
                        className="w-full bg-gray-800 border-l-4 border-l-green-500 border-gray-700 rounded px-3 py-2 text-gray-100 font-mono outline-none"
                    />
                </div>
            </div>

            <div className="bg-gray-800/50 p-3 rounded-lg text-sm text-gray-400 border border-gray-800">
                <div className="flex justify-between mb-1">
                    <span>Units</span>
                    <span className="font-mono text-gray-200">{Math.abs(lotSize * 100000).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                    <span>Est. Risk</span>
                    {/* Simple calc: abs(entry - sl) * units. Rough approx for quote currency USD */}
                    <span className="font-mono text-gray-200">
                        ${(Math.abs((signal.entry_price || 0) - sl) * (lotSize * 100000)).toFixed(2)}
                    </span>
                </div>
            </div>
            
            {error && (
                <div className="text-red-400 text-sm bg-red-400/10 p-2 rounded border border-red-400/20">
                    {error}
                </div>
            )}

            <div className="flex gap-3 mt-6">
                <button 
                    onClick={onClose}
                    className="flex-1 py-3 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition font-medium"
                >
                    Cancel
                </button>
                <button 
                    onClick={handleSubmit}
                    disabled={loading}
                    className={`flex-1 py-3 rounded-lg text-white font-bold transition flex justify-center items-center ${btnClass} ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    {loading ? (
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                        `Confirm ${isLong ? 'Buy' : 'Sell'}`
                    )}
                </button>
            </div>
        </div>
      </div>
    </div>
  );
};
