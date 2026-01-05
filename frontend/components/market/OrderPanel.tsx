'use client';

import React, { useState, useEffect } from 'react';
import { placeSmartOrder, getBrokerAccounts, ExecutionBrokerAccount } from '@/lib/api/execution';
import { Loader2, TrendingUp, TrendingDown, DollarSign, Target } from 'lucide-react';
import { useBrokerReference } from '@/context/BrokerReferenceContext';
import { cn } from '@/lib/utils';

interface OrderPanelProps {
  symbol: string;
  currentPrice: number;
  onOrderSuccess: () => void;
}

export const OrderPanel: React.FC<OrderPanelProps> = ({ symbol, currentPrice, onOrderSuccess }) => {
  // Logic from TradeModal + Improvements
  const { getInstrument, formatPrice } = useBrokerReference();
  const instrument = getInstrument(symbol);
  const [accounts, setAccounts] = useState<ExecutionBrokerAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  
  const [riskUsd, setRiskUsd] = useState<number>(10.0);
  const [sl, setSl] = useState<number>(0);
  const [tp, setTp] = useState<number>(0);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Initialize
  useEffect(() => {
    getBrokerAccounts().then(accs => {
        setAccounts(accs);
        if (accs.length > 0) setSelectedAccountId(accs[0].id);
    }).catch(err => console.error("Failed to load accounts", err));
  }, []);

  // Set default SL/TP based on price when symbol impacts
  useEffect(() => {
    if (currentPrice > 0 && sl === 0 && tp === 0) {
       // Only default if both are 0 (initial load)
       setSl(currentPrice * 0.995); // 0.5% default SL
       setTp(currentPrice * 1.01); // 1% default TP
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, currentPrice]); // Intentionally omitting sl/tp to avoid reset loop

  const handleOrder = async (direction: 'BULLISH' | 'BEARISH') => {
      setLoading(true);
      setError(null);
      setSuccessMsg(null);
      
      try {
          if (!selectedAccountId) throw new Error("Select a broker account");

          await placeSmartOrder({
                broker_account_id: selectedAccountId,
                symbol: symbol.replace('/', '_'),
                direction: direction,
                stop_loss: sl,
                risk_usd: riskUsd,
                generated_by: 'MarketTerminal',
                reason: 'Manual Entry'
          });

          setSuccessMsg(`${direction} Order Placed!`);
          onOrderSuccess();
          // Reset slightly? maybe keep values for rapid fire
      } catch (err: unknown) {
          if (err instanceof Error) {
              setError(err.message || 'Order Failed');
          } else {
             setError('Order Failed');
          }
      } finally {
          setLoading(false);
      }
  };

  const dist = Math.abs(currentPrice - sl);
  const estimatedUnits = dist > 0 ? riskUsd / dist : 0;
  
  const minSize = instrument?.details?.minimumTradeSize ? parseFloat(instrument.details.minimumTradeSize) : 0;
  const isBelowMin = estimatedUnits < minSize;

  return (
    <div className="h-full flex flex-col bg-gray-900/50 backdrop-blur border-l border-white/5">
        {/* Header */}
        <div className="p-4 border-b border-white/5">
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                <Target size={16} /> Execution Panel
            </h2>
        </div>

        {/* Account Selection */}
        <div className="p-4 space-y-4 flex-1 overflow-y-auto w-full">
             <div className="space-y-1">
                <label className="text-xs text-gray-500 font-mono">BROKER ACCOUNT</label>
                <select 
                    value={selectedAccountId}
                    onChange={(e) => setSelectedAccountId(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-300 focus:border-blue-500 outline-none"
                    disabled={accounts.length === 0}
                >
                     {accounts.length === 0 && <option>No Accounts</option>}
                     {accounts.map(a => (
                         <option key={a.id} value={a.id}>{a.broker_name} ({a.account_id})</option>
                     ))}
                </select>
            </div>

            <div className="h-px bg-white/5 my-2" />

            {/* Risk Management */}
            <div className="space-y-3">
                 <div className="space-y-1">
                    <label className="text-xs text-blue-400 font-bold font-mono flex items-center gap-1">
                        <DollarSign size={10} /> RISK (USD)
                    </label>
                    <div className="relative">
                        <input 
                            type="number" 
                            value={riskUsd}
                            onChange={(e) => setRiskUsd(Number(e.target.value))}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white font-mono font-bold text-lg focus:border-blue-500 outline-none"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                     <div className="space-y-1">
                        <label className="text-xs text-red-400 font-mono">STOP LOSS</label>
                        <input 
                            type="number"
                             step={instrument?.details?.displayPrecision ? Math.pow(10, -instrument.details.displayPrecision) : "0.00001"}
                            value={sl}
                             onChange={(e) => setSl(Number(e.target.value))}
                            className="w-full bg-gray-800 border-l-2 border-l-red-500 border-gray-700 rounded px-2 py-1.5 text-gray-300 font-mono text-xs focus:border-red-500 outline-none"
                        />
                    </div>
                     <div className="space-y-1">
                        <label className="text-xs text-green-400 font-mono">TAKE PROFIT</label>
                        <input 
                            type="number"
                             step={instrument?.details?.displayPrecision ? Math.pow(10, -instrument.details.displayPrecision) : "0.00001"}
                            value={tp}
                             onChange={(e) => setTp(Number(e.target.value))}
                            className="w-full bg-gray-800 border-l-2 border-l-green-500 border-gray-700 rounded px-2 py-1.5 text-gray-300 font-mono text-xs focus:border-green-500 outline-none"
                        />
                    </div>
                </div>
            </div>

            {/* Info Box */}
            <div className="bg-white/5 p-3 rounded text-xs space-y-2 border border-white/5">
                <div className="flex justify-between">
                    <span className="text-gray-500">Est. Position</span>
                    <span className={cn("text-gray-300 font-mono", isBelowMin && "text-red-500")}>
                        ~{Math.floor(estimatedUnits)} units
                    </span>
                </div>
                {isBelowMin && (
                    <div className="text-[10px] text-red-400 text-right">
                        Min: {instrument?.details?.minimumTradeSize}
                    </div>
                )}
                 <div className="flex justify-between">
                    <span className="text-gray-500">Pip Value</span>
                    <span className="text-gray-300 font-mono">
                         {instrument?.details?.pipLocation ? `10^${instrument.details.pipLocation}` : '-'}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500">Current Price</span>
                    <span className="text-gray-300 font-mono">{formatPrice(symbol, currentPrice)}</span>
                </div>
            </div>

            {error && (
                <div className="p-2 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded">
                    {error}
                </div>
            )}
             {successMsg && (
                <div className="p-2 bg-green-500/10 border border-green-500/20 text-green-400 text-xs rounded">
                    {successMsg}
                </div>
            )}
        </div>

        {/* Action Buttons */}
        <div className="p-4 space-y-3 bg-gray-900 border-t border-white/5">
             <button 
                onClick={() => handleOrder('BULLISH')}
                disabled={loading || !selectedAccountId}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/20"
            >
                {loading ? <Loader2 className="animate-spin" /> : <TrendingUp size={20} />}
                BUY / LONG
             </button>

             <button 
                onClick={() => handleOrder('BEARISH')}
                disabled={loading || !selectedAccountId}
                className="w-full py-3 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded flex items-center justify-center gap-2 transition-all shadow-lg shadow-rose-900/20"
            >
                {loading ? <Loader2 className="animate-spin" /> : <TrendingDown size={20} />}
                SELL / SHORT
             </button>
        </div>
    </div>
  );
};
