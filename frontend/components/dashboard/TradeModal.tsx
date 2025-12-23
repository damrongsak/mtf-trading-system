'use client';

import React, { useState, useEffect } from 'react';
import { Signal } from '@/lib/api/types';
import { placeOrder, placeSmartOrder, getBrokerAccounts, BrokerAccount } from '@/lib/api/execution';

interface TradeModalProps {
  signal: Signal | null;
  isOpen: boolean;
  onClose: () => void;
  onTradeSuccess: () => void;
}

type ExecutionMode = 'SMART' | 'MANUAL';

export const TradeModal: React.FC<TradeModalProps> = ({ signal, isOpen, onClose, onTradeSuccess }) => {
  const [mode, setMode] = useState<ExecutionMode>('SMART');
  
  // Manual State
  const [lotSize, setLotSize] = useState<number>(0.01);
  
  // Smart State
  const [riskUsd, setRiskUsd] = useState<number>(10.0);
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');

  // Common State
  const [sl, setSl] = useState<number>(0);
  const [tp, setTp] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
        // Load accounts when opening
        getBrokerAccounts().then(accs => {
            setAccounts(accs);
            if (accs.length > 0) setSelectedAccountId(accs[0].id);
        }).catch(err => console.warn("Failed to load accounts", err));
    }
  }, [isOpen]);

  useEffect(() => {
    if (signal) {
      setSl(signal.sl_price || 0);
      setTp(signal.tp_price || 0);
      setLotSize(0.01);
      setRiskUsd(10.0);
      setError(null);
    }
  }, [signal]);

  if (!isOpen || !signal) return null;

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    
    try {
        if (mode === 'MANUAL') {
            const units = signal.direction === 'LONG' || signal.direction === 'BULLISH' 
                ? lotSize * 100000 
                : -1 * lotSize * 100000;
            
            // For Manual, we still need basic OrderRequest structure
            // But wait, OrderRequest requires specific broker config usually?
            // The old placeOrder used `OrderRequest` which had BrokerConfig.
            // Let's check `lib/api/execution.ts` OrderRequest definition. 
            // It lacks BrokerConfig in frontend definition? 
            // Ah, looking at previous view_file, OrderRequest in TS: { symbol, units, sl_price... }
            // But backend `OrderRequest` has `broker: BrokerConfig`.
            // There seems to be a mismatch or implicit handling in API Gateway previously?
            // If the old `placeOrder` worked, the TS definition matches what was sent.
            // Let's assume the previous TS definition was correct for the middleware or how it was used.
            // However, looking at the file I viewed:
            // export interface OrderRequest { symbol: string; units: number... }
            // It suggests the frontend sends this to... where? 
            // If endpoint is `/api/v1/execution/orders`, backend expects `OrderRequest` with `BrokerConfig`.
            // This implies the old frontend code might have been failing or I missed something.
            // Converting to Smart Order is safer because it uses Account ID stored in DB.
            
            // To support Legacy Manual, we'd need to construct BrokerConfig. 
            // Let's rely on Smart Mode primarily.
            
            // Actually, for Manual Mode, we can use SmartOrder with manual units if we update backend,
            // but Backend SmartOrder calculates units.
            
            // Let's try to upgrade `placeOrder` usage to be compatible? 
            // Or just enforce Smart Order for now since it's the requested upgrade.
            // Use Trigger Warning for Manual Mode if not fully implemented.
            
            // Re-reading `lib/api/execution.ts`: 
            // `placeOrder(data: OrderRequest)` -> `/api/v1/execution/orders`.
            // Backend `place_order` -> expects `req.broker`.
            // Frontend `OrderRequest` -> NO `broker` field.
            // So Manual Mode was likely BROKEN or mocking something.
            // I will implement Smart Mode and maybe disable Manual if I can't fix it easily, 
            // or I assume frontend client injects it? No.
            
            // Let's Use Smart Mode logic for everything? 
            // No, Smart Mode calculates units. Manual mode specifies units.
            
            // Strategy: I will implement Smart Mode fully. Validation.
            
            // For Manual Mode to work, we need to pass credentials. We don't have them in frontend.
            // We have Account ID.
            // So we should probably add a backend endpoint `place_order_by_id` or similar.
            // OR use SmartOrder but allow overriding units? 
            // Backend `SmartOrder` doesn't support explicit units override yet.
            
            // DECISION: I will focus on SMART MODE working. 
            // I will show an error for Manual Mode saying "Legacy Execution not supported with Account ID yet".
            throw new Error("Manual Unit entry not yet supported with secure Account ID. Please use Smart Risk.");
            
        } else {
            // Smart Mode
            if (!selectedAccountId) throw new Error("No Broker Account selected.");
            
            await placeSmartOrder({
                broker_account_id: selectedAccountId,
                symbol: signal.symbol.replace('/', '_'),
                direction: (signal.direction === 'LONG' || signal.direction === 'BULLISH') ? 'BULLISH' : 'BEARISH',
                stop_loss: sl,
                risk_usd: riskUsd,
                generated_by: 'ManualDashboard',
                reason: 'User Manual Entry'
            });
        }
        
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
  
  // Calculate dist for visual aid
  const dist = Math.abs((signal.entry_price || 0) - sl);
  const estimatedUnits = dist > 0 ? riskUsd / dist : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md shadow-2xl">
        <h3 className="text-xl font-bold text-gray-100 mb-4 flex justify-between">
          <span>Execute Trade</span>
          <span className={`font-mono ${colorClass}`}>{signal.direction} {signal.symbol}</span>
        </h3>

        {/* Mode Toggle */}
        <div className="flex bg-gray-800 p-1 rounded-lg mb-6">
            <button 
                onClick={() => setMode('SMART')}
                className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${mode === 'SMART' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
            >
                Smart Risk ($)
            </button>
            <button 
                onClick={() => setMode('MANUAL')}
                className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${mode === 'MANUAL' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
            >
                Manual Lots
            </button>
        </div>
        
        <div className="space-y-4">
            {/* Account Selector */}
            <div>
                <label className="block text-xs text-gray-400 mb-1">Broker Account</label>
                <select 
                    value={selectedAccountId}
                    onChange={(e) => setSelectedAccountId(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-200 text-sm focus:border-accent-blue outline-none"
                    disabled={accounts.length === 0}
                >
                    {accounts.length === 0 && <option>No accounts found</option>}
                    {accounts.map(acc => (
                        <option key={acc.id} value={acc.id}>{acc.broker_name} ({acc.account_id})</option>
                    ))}
                </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-xs text-gray-400 mb-1">Entry Price</label>
                    <input 
                        type="number" 
                        disabled 
                        value={signal.entry_price} 
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-400 font-mono text-sm cursor-not-allowed"
                    />
                </div>
                <div>
                {mode === 'SMART' ? (
                    <>
                        <label className="block text-xs text-accent-blue mb-1 font-bold">Risk Amount ($)</label>
                        <input 
                            type="number" 
                            step="1"
                            min="1"
                            value={riskUsd} 
                            onChange={(e) => setRiskUsd(parseFloat(e.target.value))}
                            className="w-full bg-gray-800 border-2 border-accent-blue/30 focus:border-accent-blue rounded px-3 py-2 text-white font-mono font-bold outline-none"
                        />
                    </>
                ) : (
                    <>
                        <label className="block text-xs text-gray-400 mb-1">Lot Size</label>
                        <input 
                            type="number" 
                            step="0.01"
                            min="0.01"
                            value={lotSize} 
                            onChange={(e) => setLotSize(parseFloat(e.target.value))}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-100 font-mono focus:border-gray-500 outline-none"
                        />
                    </>
                )}
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
                        className="w-full bg-gray-800 border-l-4 border-l-red-500 border-gray-700 rounded px-3 py-2 text-gray-100 font-mono outline-none text-sm"
                    />
                </div>
                <div>
                    <label className="block text-xs text-gray-400 mb-1">Take Profit</label>
                    <input 
                        type="number" 
                        step="0.00001"
                        value={tp} 
                        onChange={(e) => setTp(parseFloat(e.target.value))}
                        className="w-full bg-gray-800 border-l-4 border-l-green-500 border-gray-700 rounded px-3 py-2 text-gray-100 font-mono outline-none text-sm"
                    />
                </div>
            </div>

            <div className="bg-gray-800/50 p-3 rounded-lg text-sm text-gray-400 border border-gray-800">
                {mode === 'SMART' ? (
                    <>
                        <div className="flex justify-between mb-1">
                            <span>Target Risk</span>
                            <span className="font-mono text-white font-bold">${riskUsd.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Est. Position</span>
                            <span className="font-mono text-gray-300">~{Math.floor(estimatedUnits)} units</span>
                        </div>
                        <div className="text-[10px] text-gray-500 mt-1 text-right">
                           *Actual units calculated by backend using live price
                        </div>
                    </>
                ) : (
                    <>
                        <div className="flex justify-between mb-1">
                            <span>Units (Manual)</span>
                            <span className="font-mono text-gray-200">{Math.abs(lotSize * 100000).toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Est. Risk</span>
                            <span className="font-mono text-gray-200">
                                ${(dist * (lotSize * 100000)).toFixed(2)}
                            </span>
                        </div>
                    </>
                )}
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
                    disabled={loading ||  (mode === 'SMART' && !selectedAccountId)}
                    className={`flex-1 py-3 rounded-lg text-white font-bold transition flex justify-center items-center ${btnClass} ${(loading || (mode === 'SMART' && !selectedAccountId)) ? 'opacity-50 cursor-not-allowed' : ''}`}
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
