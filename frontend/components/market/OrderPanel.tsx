'use client';

import React, { useState, useEffect } from 'react';
import { placeSmartOrder, ExecutionBrokerAccount, getAccountSummary } from '@/lib/api/execution';
import { Loader2, DollarSign, Target, Settings2, Info, ChevronDown, Check, Calculator, RefreshCw } from 'lucide-react';
import { useBrokerReference } from '@/context/BrokerReferenceContext';
import { cn } from '@/lib/utils';

interface OrderPanelProps {
  symbol: string;
  currentPrice: number;
  onOrderSuccess: () => void;
  accounts: ExecutionBrokerAccount[];
  selectedAccountId: string;
  onAccountChange: (id: string) => void;
}

type Direction = 'BULLISH' | 'BEARISH';
const LEVERAGE_DISPLAY = "1000:1"; 

export const OrderPanel: React.FC<OrderPanelProps> = ({ 
    symbol, 
    currentPrice, 
    onOrderSuccess,
    accounts,
    selectedAccountId,
    onAccountChange
}) => {
  const { getInstrument, formatPrice } = useBrokerReference();
  const instrument = getInstrument(symbol);

  // --- State: Order Core ---
  const [direction, setDirection] = useState<Direction>('BULLISH');
  const [orderType, setOrderType] = useState('MARKET');
  
  // --- State: Risk ---
  const [riskUsd, setRiskUsd] = useState<number>(10.0);
  const [balance, setBalance] = useState<number>(0);
  const [loadingBalance, setLoadingBalance] = useState(false);

  // --- State: Protection ---
  const [takeProfitEnabled, setTakeProfitEnabled] = useState(false);
  const [stopLossEnabled, setStopLossEnabled] = useState(true);

  
  const [slPrice, setSlPrice] = useState<number>(0);
  const [slPips, setSlPips] = useState<number>(500); // 50 pips

  // --- State: Smart Sizing ---
  const [isSmartSize, setIsSmartSize] = useState(false);

  // --- State: Async ---
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // --- Helpers: Math ---
  const pipVal = instrument?.details?.pipLocation ? Math.pow(10, instrument.details.pipLocation) : 0.01;
  const tickSize = instrument?.details?.displayPrecision ? Math.pow(10, -instrument.details.displayPrecision) : 0.00001;
  const spreadPips = 1.2; 
  const spreadVal = spreadPips * pipVal;
  
  const bid = currentPrice;
  const ask = currentPrice + spreadVal;
  const executePrice = direction === 'BULLISH' ? ask : bid;

  // --- Effects ---

  useEffect(() => {
    if (!selectedAccountId) return;
    setLoadingBalance(true);
    getAccountSummary(selectedAccountId)
        .then(res => {
            const bal = parseFloat(res.balance);
            if (!isNaN(bal)) setBalance(bal);
        })
        .finally(() => setLoadingBalance(false));
  }, [selectedAccountId]);

  // Smart Sizing Logic
  useEffect(() => {
      if (isSmartSize && balance > 0) {
          setRiskUsd(parseFloat((balance * 0.01).toFixed(2)));
      }
  }, [isSmartSize, balance]);

  // Sync Pips -> Price 
  useEffect(() => {
      // Avoid infinite loops by checking mostly only when pips change or direction/price changes
      // This is a simplified uni-directional sync for the UI "Pips Driven" mode
      
      if (slPips > 0) {
          const dist = slPips * tickSize;
          const newSl = direction === 'BULLISH' ? (executePrice - dist) : (executePrice + dist);
          setSlPrice(parseFloat(newSl.toFixed(instrument?.details?.displayPrecision || 5)));
      }
      
      if (tpPips > 0) {
          const dist = tpPips * tickSize;
          const newTp = direction === 'BULLISH' ? (executePrice + dist) : (executePrice - dist);
          setTpPrice(parseFloat(newTp.toFixed(instrument?.details?.displayPrecision || 5)));
      }
  }, [direction, currentPrice, slPips, tpPips, executePrice, instrument, tickSize]); 


  // --- Handlers ---
  const handleOrder = async () => {
      setLoading(true);
      setError(null);
      setSuccessMsg(null);
      try {
          if (!selectedAccountId) throw new Error("Select Broker");
          
          await placeSmartOrder({
                broker_account_id: selectedAccountId,
                symbol: symbol.replace('/', '_'),
                direction: direction,
                stop_loss: stopLossEnabled ? slPrice : 0,
                risk_usd: riskUsd,
                generated_by: 'ProTerminal',
                reason: 'Pro Panel'
          });

          setSuccessMsg("Order Placed");
          onOrderSuccess();
      } catch (err: any) {
          setError(err.message || 'Failed');
      } finally {
          setLoading(false);
      }
  };

  const applyRR = (ratio: number) => {
      if (slPips <= 0) return;
      setTakeProfitEnabled(true);
      setTpPips(slPips * ratio);
  };

  const slDistPrice = Math.abs(executePrice - slPrice);
  const estLots = (slDistPrice > 0 && stopLossEnabled) ? (riskUsd / slDistPrice) / 100000 : 0;
  
  return (
    <div className="h-full flex flex-col bg-[#111216] border-l border-black font-sans text-gray-300 select-none">
        {/* 1. Header Tabs */}
        <div className="flex border-b border-white/5 bg-[#0b0c10]">
            <button className="flex-1 py-3 text-sm font-bold text-white border-t-2 border-blue-500 bg-[#1e2029]">Order</button>
            <button className="flex-1 py-3 text-sm font-bold text-gray-500 hover:text-gray-300">DOM</button>
            <div className="px-3 flex items-center border-l border-white/5">
                <select 
                    value={selectedAccountId}
                    onChange={e => onAccountChange(e.target.value)}
                    className="bg-transparent text-xs outline-none text-gray-400 w-24 truncate cursor-pointer"
                >
                    {accounts.map(a => <option key={a.id} value={a.id}>{a.broker_name}</option>)}
                </select>
            </div>
        </div>

        {/* 2. Bid/Ask Banner */}
        <div className="flex h-20 relative border-b border-black">
             <div 
                onClick={() => setDirection('BEARISH')}
                className={cn(
                    "flex-1 flex flex-col items-center justify-center cursor-pointer transition-colors relative z-10",
                    direction === 'BEARISH' ? "bg-[#2b1216]" : "bg-[#16171d] hover:bg-[#1a1b22]"
                )}
             >
                 <span className={cn("text-sm font-bold uppercase", direction === 'BEARISH' ? "text-rose-500" : "text-gray-500")}>Sell</span>
                 <span className={cn("text-lg font-mono font-bold", direction === 'BEARISH' ? "text-white" : "text-gray-400")}>{bid.toFixed(instrument?.details?.displayPrecision || 5)}</span>
             </div>

             <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-20 bg-[#252833] text-[10px] text-gray-300 px-2 py-0.5 rounded border border-black shadow-sm font-mono">
                 {spreadPips}
             </div>

             <div 
                onClick={() => setDirection('BULLISH')}
                className={cn(
                    "flex-1 flex flex-col items-center justify-center cursor-pointer transition-colors relative z-10",
                    direction === 'BULLISH' ? "bg-[#0c1f36]" : "bg-[#16171d] hover:bg-[#1a1b22]"
                )}
             >
                 <span className={cn("text-sm font-bold uppercase", direction === 'BULLISH' ? "text-blue-500" : "text-gray-500")}>Buy</span>
                 <span className={cn("text-lg font-mono font-bold", direction === 'BULLISH' ? "text-white" : "text-gray-400")}>{ask.toFixed(instrument?.details?.displayPrecision || 5)}</span>
             </div>
        </div>

        {/* 3. Order Type */}
        <div className="flex p-1 gap-1 text-xs text-gray-400 border-b border-white/5 bg-[#16171d]">
            {['Market', 'Limit', 'Stop'].map(t => (
                <button 
                    key={t}
                    onClick={() => setOrderType(t.toUpperCase())}
                    className={cn(
                        "flex-1 py-1.5 rounded hover:text-white transition-colors uppercase font-medium", 
                        orderType === t.toUpperCase() ? "text-white bg-white/10 font-bold" : ""
                    )}
                >
                    {t}
                </button>
            ))}
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
            
            {/* Top Section Wrapper */}
            <div className="space-y-6">
                {/* 4. Volume / Risk */}
                <div className="space-y-3">
                     <div className="flex justify-between items-end">
                         <span className="text-xs text-gray-400 font-medium">Volume Calculation</span>
                         <span className="text-[10px] text-gray-500">
                             Bal: <span className="text-gray-300">${balance.toFixed(0)}</span>
                         </span>
                     </div>
                     
                     <div className="grid grid-cols-2 gap-3">
                         <div className="bg-[#1e2029] rounded border border-white/5 p-2.5">
                             <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Lot Size</div>
                             <div className="font-mono text-white text-base font-bold">
                                 {estLots > 0 ? estLots.toFixed(2) : '0.00'} <span className="text-gray-500 text-[10px] font-normal">LOTS</span>
                             </div>
                         </div>
                         
                         <div className="bg-[#1e2029] rounded border border-white/5 p-2.5 relative group">
                             <div className="text-[10px] text-blue-400 flex items-center justify-between gap-1 mb-1">
                                 <span className="cursor-pointer uppercase tracking-wider flex items-center gap-1">Risk Amount (USD) <ChevronDown size={10} /></span>
                                 <div 
                                    onClick={() => setIsSmartSize(!isSmartSize)}
                                    className={`cursor-pointer px-1.5 py-0.5 rounded text-[9px] font-bold border ${isSmartSize ? 'bg-blue-500 text-white border-blue-500' : 'bg-gray-800 text-gray-500 border-gray-700'}`}
                                 >
                                    1% {isSmartSize ? 'ON' : 'OFF'}
                                 </div>
                             </div>
                             <div className="flex items-center">
                                <input 
                                    type="number"
                                    value={riskUsd}
                                    readOnly={isSmartSize}
                                    onChange={e => !isSmartSize && setRiskUsd(parseFloat(e.target.value))}
                                    className={`bg-transparent w-full font-mono text-base font-bold outline-none border-none p-0 focus:ring-0 ${isSmartSize ? 'text-blue-400' : 'text-white'}`}
                                />
                                <DollarSign size={14} className="text-gray-500 ml-1" />
                             </div>
                         </div>
                     </div>
                </div>

                <div className="h-px bg-white/5" />

                {/* 5. Protection */}
                <div className="space-y-5">
                    {/* Take Profit */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                 <input 
                                    type="checkbox" 
                                    checked={takeProfitEnabled} 
                                    onChange={e => setTakeProfitEnabled(e.target.checked)}
                                    className="w-4 h-4 rounded bg-[#2b2e3b] border-gray-600 checked:bg-blue-500 cursor-pointer" 
                                />
                                 <span className="text-xs font-bold text-gray-300">Take Profit</span>
                            </div>
                            {/* R:R Buttons */}
                            <div className="flex gap-1">
                                 {[1, 2, 3].map(r => (
                                     <button 
                                        key={r} 
                                        onClick={() => applyRR(r)}
                                        className="px-2 py-0.5 bg-[#2b2e3b] hover:bg-blue-600 hover:text-white rounded text-[10px] text-gray-400 transition-colors font-mono"
                                    >
                                        1:{r}
                                     </button>
                                 ))}
                            </div>
                        </div>
                        
                        {takeProfitEnabled && (
                            <div className="grid grid-cols-2 gap-3 animate-in fade-in slide-in-from-top-1 duration-200">
                                 <div className="bg-[#1e2029] border border-white/5 rounded px-3 py-2">
                                     <div className="text-[10px] text-gray-500 uppercase">Target Price</div>
                                     <input 
                                         type="number" 
                                         value={tpPrice} 
                                         disabled 
                                         className="bg-transparent w-full text-sm font-mono text-gray-400 mt-0.5" 
                                     />
                                 </div>
                                  <div className="bg-[#1e2029] border border-white/5 rounded px-3 py-2 ring-1 ring-blue-500/20">
                                     <div className="text-[10px] text-blue-400 uppercase font-bold">Profit Ticks</div>
                                     <input 
                                         type="number" 
                                         value={tpPips} 
                                         onChange={e => setTpPips(parseInt(e.target.value))}
                                         className="bg-transparent w-full text-sm font-mono text-white outline-none mt-0.5 font-bold" 
                                     />
                                 </div>
                            </div>
                        )}
                    </div>

                    {/* Stop Loss */}
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                             <input 
                                type="checkbox" 
                                checked={stopLossEnabled} 
                                onChange={e => setStopLossEnabled(e.target.checked)}
                                className="w-4 h-4 rounded bg-[#2b2e3b] border-gray-600 checked:bg-rose-500 cursor-pointer" 
                            />
                             <span className="text-xs font-bold text-gray-300">Stop Loss</span>
                        </div>
                        {stopLossEnabled && (
                            <div className="grid grid-cols-2 gap-3 animate-in fade-in slide-in-from-top-1 duration-200">
                                 <div className="bg-[#1e2029] border border-white/5 rounded px-3 py-2">
                                     <div className="text-[10px] text-gray-500 uppercase">Stop Price</div>
                                     <input 
                                         type="number" 
                                         value={slPrice} 
                                         disabled 
                                         className="bg-transparent w-full text-sm font-mono text-gray-400 mt-0.5" 
                                     />
                                 </div>
                                  <div className="bg-[#1e2029] border border-white/5 rounded px-3 py-2 ring-1 ring-rose-500/20">
                                     <div className="text-[10px] text-rose-400 uppercase font-bold">Risk Ticks</div>
                                     <input 
                                         type="number" 
                                         value={slPips} 
                                         onChange={e => setSlPips(parseInt(e.target.value))}
                                         className="bg-transparent w-full text-sm font-mono text-white outline-none mt-0.5 font-bold" 
                                     />
                                 </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* 6. Position Math (Natural Flow) */}
             <div className="space-y-4 pt-4">
                 <div className="bg-[#16171d] rounded p-3 space-y-2 border border-white/5">
                    <div className="flex items-center gap-2 pb-2 border-b border-white/5 mb-1">
                        <Calculator size={14} className="text-blue-500" />
                        <span className="text-xs font-bold text-gray-200">Position Math</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-y-1 gap-x-4 text-[11px]">
                         <div className="flex justify-between">
                             <span className="text-gray-500">Risk / Pip</span>
                             <span className="text-gray-300 font-mono font-medium">${(riskUsd / slPips).toFixed(2)}</span>
                         </div>
                          <div className="flex justify-between">
                             <span className="text-gray-500">Tick Value</span>
                             <span className="text-gray-300 font-mono font-medium">{pipVal} USD</span>
                         </div>
                          <div className="flex justify-between">
                             <span className="text-gray-500">Spread Cost</span>
                             <span className="text-rose-400 font-mono font-medium">-${(estLots * 10 * spreadPips).toFixed(2)}</span>
                         </div>
                          <div className="flex justify-between">
                             <span className="text-gray-500">Trade Value</span>
                             <span className="text-gray-300 font-mono font-medium">${(estLots * 100000 * currentPrice).toLocaleString([], {maximumFractionDigits:0})}</span>
                         </div>
                    </div>
                 </div>
                 
                 {error && <div className="text-xs text-red-400 bg-red-500/10 p-3 rounded border border-red-500/20 flex items-center gap-2"><Info size={14} /> {error}</div>}
                 {successMsg && <div className="text-xs text-green-400 bg-green-500/10 p-3 rounded border border-green-500/20 flex items-center gap-2"><Check size={14} /> {successMsg}</div>}
             </div>

             {/* 7. Action Button (Scrolls with content) */}
            <div className="pt-2 pb-6">
                <button 
                    onClick={handleOrder}
                    disabled={loading || !selectedAccountId}
                    className={cn(
                        "w-full py-3.5 rounded text-white font-bold text-base shadow-lg transition-all flex flex-col items-center justify-center leading-none gap-1.5",
                        direction === 'BULLISH' ? "bg-blue-600 hover:bg-blue-500 shadow-blue-900/20" : "bg-rose-600 hover:bg-rose-500 shadow-rose-900/20",
                        loading && "opacity-50 cursor-not-allowed"
                    )}
                >
                    {loading ? (
                        <Loader2 className="animate-spin" size={24} />
                    ) : (
                        <>
                            <span className="uppercase tracking-wide">{direction === 'BULLISH' ? 'BUY' : 'SELL'} {symbol.replace('_', '/')}</span>
                            <div className="text-xs opacity-75 font-normal font-mono">
                               {estLots > 0 ? `${estLots.toFixed(2)}` : '0.01'} LOTS @ MARKET
                            </div>
                        </>
                    )}
                </button>
            </div>
        </div>


    </div>
  );
};
