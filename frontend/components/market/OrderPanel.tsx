'use client';

import React, { useState, useEffect } from 'react';
import { placeSmartOrder, ExecutionBrokerAccount, getAccountSummary } from '@/lib/api/execution';
import { Loader2, DollarSign, Target, Settings2, Info, ChevronDown, Check, Calculator, RefreshCw, Lock } from 'lucide-react';
import { useBrokerReference } from '@/context/BrokerReferenceContext';
import { cn } from '@/lib/utils';
import { ChartPriceLine } from '@/components/charts/CandleChart';
import { usePersistentState } from '@/lib/hooks/usePersistentState';

interface OrderPanelProps {
  symbol: string;
  currentPrice: number;
  onOrderSuccess: () => void;
  accounts: ExecutionBrokerAccount[];
  selectedAccountId: string;
  onAccountChange: (id: string) => void;
  onOrderLinesChange?: (lines: ChartPriceLine[]) => void;
  
  // Lifted State
  slPrice: number;
  setSlPrice: (val: number) => void;
  tpPrice: number;
  setTpPrice: (val: number) => void;
  limitPrice: number;
  setLimitPrice: (val: number) => void;

  // Lifted Modes
  slMode: 'PIPS' | 'PRICE';
  setSlMode: (mode: 'PIPS' | 'PRICE') => void;
  tpMode: 'PIPS' | 'PRICE';
  setTpMode: (mode: 'PIPS' | 'PRICE') => void;
}

type Direction = 'BULLISH' | 'BEARISH';
const LEVERAGE_DISPLAY = "1000:1"; 

export const OrderPanel: React.FC<OrderPanelProps> = ({ 
    symbol, 
    currentPrice, 
    onOrderSuccess,
    accounts,
    selectedAccountId,
    onAccountChange,
    onOrderLinesChange,
    slPrice, setSlPrice,
    tpPrice, setTpPrice,
    limitPrice, setLimitPrice,
    slMode, setSlMode,
    tpMode, setTpMode
}) => {
  const { getInstrument, formatPrice } = useBrokerReference();
  const instrument = getInstrument(symbol);

  // --- State: Order Core ---
  const [direction, setDirection] = useState<Direction>('BULLISH');
  const [orderType, setOrderType] = usePersistentState<string>('mtf_order_type', 'MARKET');
  
  // --- State: Risk ---
  const [riskUsd, setRiskUsd] = usePersistentState<number>('mtf_risk_usd', 10.0);
  const [riskPercent, setRiskPercent] = usePersistentState<number>('mtf_risk_percent', 1.0);
  const [balance, setBalance] = useState<number>(0);
  const [loadingBalance, setLoadingBalance] = useState(false);

  // --- State: Protection ---
  const [takeProfitEnabled, setTakeProfitEnabled] = usePersistentState<boolean>('mtf_tp_enabled', true);
  const [stopLossEnabled, setStopLossEnabled] = usePersistentState<boolean>('mtf_sl_enabled', true);

  
  // const [slPrice, setSlPrice] = useState<number>(0); // Lifted
  const [slPips, setSlPips] = usePersistentState<number>('mtf_sl_pips', 50); // 50 pips
  // const [tpPrice, setTpPrice] = useState<number>(0); // Lifted
  const [tpPips, setTpPips] = usePersistentState<number>('mtf_tp_pips', 150); // Default 1:3 RR (50 * 3)
  // const [limitPrice, setLimitPrice] = useState<number>(0); // Lifted

  // --- State: Smart Sizing ---
  const [isSmartSize, setIsSmartSize] = usePersistentState<boolean>('mtf_smart_size', false);
  const [manualLots, setManualLots] = useState<string>('');
  const [isManualLots, setIsManualLots] = useState(false);

  // --- State: Minimax (Risk Citadel) ---
  const [confidence, setConfidence] = usePersistentState<number>('mtf_confidence', 0.85);
  const [painThreshold, setPainThreshold] = usePersistentState<number>('mtf_pain_threshold', 50.0);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // --- State: Async ---
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // --- Helpers: Math ---
  const pipVal = (instrument?.details?.pipLocation !== undefined && instrument?.details?.pipLocation !== null) 
    ? Math.pow(10, instrument.details.pipLocation) 
    : 0.01;
  const tickSize = instrument?.details?.displayPrecision ? Math.pow(10, -instrument.details.displayPrecision) : 0.00001;
  const spreadPips = 1.2; 
  const spreadVal = spreadPips * pipVal;
  
  const bid = currentPrice;
  const ask = currentPrice + spreadVal;
  const isPendingOrder = orderType !== 'MARKET';
  
  // Initialize Limit Price
  useEffect(() => {
      if (isPendingOrder && limitPrice === 0 && currentPrice > 0) {
          setLimitPrice(currentPrice);
      }
  }, [isPendingOrder, currentPrice]);

  const executePrice = isPendingOrder && limitPrice > 0 ? limitPrice : (direction === 'BULLISH' ? ask : bid);

  const slDistPrice = Math.abs(executePrice - slPrice);
  const calculatedLots = (slDistPrice > 0 && stopLossEnabled) ? (riskUsd / slDistPrice) / 100000 : 0;
  const currentLots = isManualLots ? (parseFloat(manualLots) || 0) : calculatedLots;

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
          setRiskUsd(parseFloat((balance * (riskPercent / 100)).toFixed(2)));
      }
  }, [isSmartSize, balance, riskPercent]);

  // Sync Lots from Risk
  useEffect(() => {
    if (!isManualLots) {
        setManualLots(calculatedLots > 0 ? calculatedLots.toFixed(2) : '0.01');
    }
  }, [calculatedLots, isManualLots]);



  // --- Handlers: Mode Switching & Updates ---
  
  const handleSlPriceChange = (val: number) => {
      setSlPrice(val);
      setSlMode('PRICE'); // User is editing Price, so Price is Anchor
  };

  const handleTpPriceChange = (val: number) => {
      setTpPrice(val);
      setTpMode('PRICE');
  };

  const handleSlPipsChange = (val: number) => {
      setSlPips(val);
      setSlMode('PIPS'); // User is editing Pips, so Pips is Anchor
  };

  const handleTpPipsChange = (val: number) => {
      setTpPips(val);
      setTpMode('PIPS');
  };

  // --- Bi-Directional Sync Effects ---
  
  // 1. ANCHOR: PRICE (Mode = 'PRICE')
  // If Price is Anchor, we update Pips when: Price Changes OR Market Moves
  useEffect(() => {
     if (slMode !== 'PRICE') return;
     if (slPrice > 0 && pipVal > 0) {
          const dist = Math.abs(executePrice - slPrice);
          const pips = parseFloat((dist / pipVal).toFixed(1));
          if (Math.abs(pips - slPips) > 0.1) setSlPips(pips);
     }
  }, [slPrice, executePrice, pipVal, slMode]);

  useEffect(() => {
     if (tpMode !== 'PRICE') return;
     if (tpPrice > 0 && pipVal > 0) {
          const dist = Math.abs(executePrice - tpPrice);
          const pips = parseFloat((dist / pipVal).toFixed(1));
          if (Math.abs(pips - tpPips) > 0.1) setTpPips(pips);
     }
  }, [tpPrice, executePrice, pipVal, tpMode]);

  // 2. ANCHOR: PIPS (Mode = 'PIPS')
  // If Pips is Anchor, we update Price when: Pips Changes OR Market Moves
  useEffect(() => {
     if (slMode !== 'PIPS') return;
     if (stopLossEnabled && slPips > 0 && pipVal > 0) {
          const dist = slPips * pipVal;
          const newSl = direction === 'BULLISH' ? (executePrice - dist) : (executePrice + dist);
          if (Math.abs(newSl - slPrice) > tickSize) {
              setSlPrice(parseFloat(newSl.toFixed(instrument?.details?.displayPrecision || 5)));
          }
     }
  }, [slPips, executePrice, pipVal, direction, stopLossEnabled, slMode]);

  useEffect(() => {
     if (tpMode !== 'PIPS') return;
     if (takeProfitEnabled && tpPips > 0 && pipVal > 0) {
          const dist = tpPips * pipVal;
          const newTp = direction === 'BULLISH' ? (executePrice + dist) : (executePrice - dist);
          if (Math.abs(newTp - tpPrice) > tickSize) {
              setTpPrice(parseFloat(newTp.toFixed(instrument?.details?.displayPrecision || 5)));
          }
     }
  }, [tpPips, executePrice, pipVal, direction, takeProfitEnabled, tpMode]);

  
  // Ensure Dragging updates mode? 
  // If slPrice changes and it wasn't our effect, we probably want to assume PRICE mode?
  // But hard to detect "our effect". 
  // For now, let's rely on onFocus / onChange handlers.
  // Wait, if I drag the line chart, onOrderLinesChange -> page.tsx -> setSlPrice (Prop Update).
  // We need to detect Prop Update.
  // Actually, Effect 1 (PRICE mode) depends on slPrice.
  // If I drag, slPrice updates. 
  // If I was in PIPS mode: 
  //    Effect 2 (PIPS mode) runs on tick. Resets Price. Conflict!
  // So Dragging MUST switch to PRICE mode.
  // Since we can't easily detect Drag source here, we should probably default "Price Change" implies Price Mode if the change didn't come from Pips?
  // Let's add a `useEffect` to watch `slPrice` prop specifically?
  // No, clean solution: Add `onLineDrag` prop to OrderPanel logic? No, its local.
  // Users will have to click the "Price" input to lock it, or we accept that Dragging might fight Pips mode.
  // Actually, if I drag a line, `slPrice` changes. 
  // In `PIPS` mode, next tick resets it.
  // This IS the bug. 
  // I will add a "Lock" UI toggle to make it explicit.


  const handleLotChange = (valStr: string) => {
      setManualLots(valStr);
      setIsManualLots(true);
      
      const val = parseFloat(valStr);
      if (!isNaN(val) && val > 0 && slDistPrice > 0) {
          // Reverse calc Risk: Risk = Lots * Dist * 100000
          // Ensure we don't divide by zero logic elsewhere
          const newRisk = val * slDistPrice * 100000;
          setRiskUsd(parseFloat(newRisk.toFixed(2)));
      }
  };

  const handleRiskChange = (val: number) => {
      setRiskUsd(val);
      setIsManualLots(false); // Revert to auto-calculation based on Risk
      
      // Reverse calculate percent if balance exists
      if (balance > 0) {
          const pct = (val / balance) * 100;
          setRiskPercent(parseFloat(pct.toFixed(2)));
      }
  };

  // --- Handlers: Execution ---
  const handleOrder = async () => {
      setLoading(true);
      setError(null);
      setSuccessMsg(null);
      try {
          if (!selectedAccountId) throw new Error("Select Broker");
          
          const finalRisk = isManualLots ? ((parseFloat(manualLots) || 0) * 100000 * slDistPrice) : riskUsd;

          await placeSmartOrder({
                broker_account_id: selectedAccountId,
                symbol: symbol.replace('/', '_'),
                direction: direction,
                entry_price: isPendingOrder ? limitPrice : undefined,
                stop_loss: stopLossEnabled ? slPrice : 0,
                take_profit: takeProfitEnabled ? tpPrice : 0,
                risk_usd: finalRisk,
                time_in_force: 'GTC', // Default to Good-Til-Cancelled
                slippage_tolerance: 0.0001, // 1 pip default tolerance
                generated_by: 'ProTerminal',
                reason: 'Pro Panel',
                confidence: confidence,
                pain_threshold: painThreshold,
                atr_multiplier: 1.0
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
      
      const newTpPips = slPips * ratio;
      setTpPips(newTpPips);
      setTpMode('PIPS'); // Set mode to PIPS
      
      // Update Price Immediately
      const dist = newTpPips * pipVal;
      const newTp = direction === 'BULLISH' ? (executePrice + dist) : (executePrice - dist);
      setTpPrice(parseFloat(newTp.toFixed(instrument?.details?.displayPrecision || 5)));
  };



  // --- Effect: Sync Chart Lines ---
  useEffect(() => {
      if (!onOrderLinesChange) return;

      const lines: ChartPriceLine[] = [];
      
      // Stop Loss Line
      if (stopLossEnabled && slPrice > 0) {
          lines.push({
              price: slPrice,
              color: '#ef4444', // Red
              title: 'SL',
              lineStyle: 2, // Dashed
              lineWidth: 1,
              axisLabelVisible: true
          });
      }
      
      // Take Profit Line
      if (takeProfitEnabled && tpPrice > 0) {
          lines.push({
              price: tpPrice,
              color: '#22c55e', // Green
              title: 'TP',
              lineStyle: 2, // Dashed
              lineWidth: 1,
              axisLabelVisible: true
          });
      }

      // Entry Price Line (Pending)
      if (isPendingOrder && limitPrice > 0) {
          lines.push({
              price: limitPrice,
              color: '#fbbf24', // Amber-400
              title: 'ENTRY',
              lineStyle: 2, // Dashed
              lineWidth: 1,
              axisLabelVisible: true
          });
      }
      
      onOrderLinesChange(lines);
  }, [slPrice, tpPrice, limitPrice, stopLossEnabled, takeProfitEnabled, isPendingOrder, onOrderLinesChange]);
  
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
                
                {/* Entry Price (Pending Orders) */}
                {isPendingOrder && (
                    <div className="bg-[#1e2029] rounded border border-white/5 p-2.5 relative group animate-in fade-in slide-in-from-top-2">
                        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Entry Price</div>
                        <div className="flex items-center">
                            <input 
                                type="number"
                                value={limitPrice}
                                onChange={e => setLimitPrice(parseFloat(e.target.value))}
                                className="bg-transparent w-full font-mono text-base font-bold outline-none border-none p-0 focus:ring-0 text-amber-400"
                            />
                        </div>
                    </div>
                )}

                {/* 4. Volume / Risk */}
                <div className="space-y-3">
                     <div className="flex justify-between items-end">
                         <span className="text-xs text-gray-400 font-medium">Volume Calculation</span>
                         <span className="text-[10px] text-gray-500">
                             Bal: <span className="text-gray-300">${balance.toFixed(0)}</span>
                         </span>
                     </div>
                     
                     <div className="grid grid-cols-2 gap-3">
                         <div className="bg-[#1e2029] rounded border border-white/5 p-2.5 relative group">
                             <div className="text-[10px] text-gray-500 flex items-center justify-between gap-1 mb-1">
                                 <span className="uppercase tracking-wider">Lot Size</span>
                                 {isManualLots && (
                                     <button 
                                        onClick={() => setIsManualLots(false)}
                                        className="text-blue-400 hover:text-blue-300"
                                        title="Reset to Calculated"
                                     >
                                         <RefreshCw size={10} />
                                     </button>
                                 )}
                             </div>
                             <div className="flex items-center">
                                 <input 
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    value={manualLots}
                                    onChange={e => handleLotChange(e.target.value)}
                                    className={cn(
                                        "bg-transparent w-full font-mono text-base font-bold outline-none border-none p-0 focus:ring-0",
                                        isManualLots ? "text-blue-400" : "text-white"
                                    )}
                                 />
                                 <span className="text-gray-500 text-[10px] font-normal ml-1">LOTS</span>
                             </div>
                         </div>
                         
                         <div className="bg-[#1e2029] rounded border border-white/5 p-2.5 relative group">
                             <div className="text-[10px] text-blue-400 flex items-center justify-between gap-1 mb-1">
                                 <span className="cursor-pointer uppercase tracking-wider flex items-center gap-1">Risk Amount (USD) <ChevronDown size={10} /></span>
                                 <div className="flex items-center gap-1">
                                 <div className="flex items-center gap-1">
                                    <div className="flex items-center bg-gray-800 rounded px-1 border border-blue-500/30 w-12">
                                        <input 
                                            type="number" 
                                            min="0.1"
                                            max="100"
                                            step="0.1"
                                            value={riskPercent}
                                            onChange={e => {
                                                const val = e.target.value;
                                                const newPct = parseFloat(val);
                                                setRiskPercent(isNaN(newPct) ? 0 : newPct);
                                                
                                                // Calculator Logic (Manual Mode)
                                                if (!isSmartSize) {
                                                    // Allow 0 balance to result in 0 Risk (responsive UI)
                                                    const bal = balance || 0; 
                                                    const risk = isNaN(newPct) ? 0 : (bal * (newPct / 100));
                                                    setRiskUsd(parseFloat(risk.toFixed(2)));
                                                }
                                            }}
                                            className="w-full bg-transparent text-[9px] font-bold text-blue-400 outline-none text-right"
                                        />
                                        <span className="text-[9px] text-blue-500 ml-0.5">%</span>
                                    </div>
                                    <div 
                                        onClick={() => setIsSmartSize(!isSmartSize)}
                                        className={`cursor-pointer px-1.5 py-0.5 rounded text-[9px] font-bold border ${isSmartSize ? 'bg-blue-500 text-white border-blue-500' : 'bg-gray-800 text-gray-500 border-gray-700 hover:text-gray-300'}`}
                                        title={isSmartSize ? "Smart Mode: Risk auto-updates with Balance" : "Manual Mode: Risk is fixed USD"}
                                    >
                                        {isSmartSize ? 'A' : 'M'}
                                    </div>
                                 </div>
                                 </div>
                             </div>
                             <div className="flex items-center">
                                <input 
                                    type="number"
                                    value={riskUsd}
                                    readOnly={isSmartSize}
                                    onChange={e => !isSmartSize && handleRiskChange(parseFloat(e.target.value))}
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
                                 {[1, 2, 3].map(r => {
                                     const isActive = Math.abs(tpPips - (slPips * r)) < 1; // Use small delta for float safety if any
                                     return (
                                         <button 
                                            key={r} 
                                            onClick={() => applyRR(r)}
                                            className={cn(
                                                "px-2 py-0.5 rounded text-[10px] transition-colors font-mono border",
                                                isActive 
                                                    ? "bg-blue-600 text-white border-blue-500 font-bold" 
                                                    : "bg-[#2b2e3b] hover:bg-blue-600/30 text-gray-400 border-transparent hover:text-gray-200"
                                            )}
                                        >
                                            1:{r}
                                         </button>
                                     );
                                 })}
                            </div>
                        </div>
                        
                        {takeProfitEnabled && (
                            <div className="grid grid-cols-2 gap-3 animate-in fade-in slide-in-from-top-1 duration-200">
                                 <div className={cn("bg-[#1e2029] border border-white/5 rounded px-3 py-2 transition-all", tpMode === 'PRICE' && "ring-1 ring-blue-500/50 bg-blue-500/5")}>
                                     <div className="text-[10px] text-gray-500 uppercase flex justify-between">
                                         Target Price
                                         {tpMode === 'PRICE' && <Lock size={10} className="text-blue-400" />}
                                     </div>
                                     <input 
                                         type="number" 
                                         value={tpPrice} 
                                         onFocus={() => setTpMode('PRICE')}
                                         onChange={e => handleTpPriceChange(parseFloat(e.target.value))}
                                         className="bg-transparent w-full text-sm font-mono text-gray-400 mt-0.5 outline-none focus:text-white transition-colors" 
                                     />
                                 </div>
                                  <div className={cn("bg-[#1e2029] border border-white/5 rounded px-3 py-2 transition-all", tpMode === 'PIPS' && "ring-1 ring-blue-500/50 bg-blue-500/5")}>
                                     <div className="text-[10px] text-blue-400 uppercase font-bold flex justify-between">
                                         Profit Pips
                                         {tpMode === 'PIPS' && <Lock size={10} />}
                                     </div>
                                     <input 
                                         type="number" 
                                         value={tpPips} 
                                         onFocus={() => setTpMode('PIPS')}
                                         onChange={e => handleTpPipsChange(parseFloat(e.target.value))}
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
                                 <div className={cn("bg-[#1e2029] border border-white/5 rounded px-3 py-2 transition-all", slMode === 'PRICE' && "ring-1 ring-rose-500/50 bg-rose-500/5")}>
                                     <div className="text-[10px] text-gray-500 uppercase flex justify-between">
                                         Stop Price
                                         {slMode === 'PRICE' && <Lock size={10} className="text-rose-400" />}
                                     </div>
                                     <input 
                                         type="number" 
                                         value={slPrice} 
                                         onFocus={() => setSlMode('PRICE')}
                                         onChange={e => handleSlPriceChange(parseFloat(e.target.value))}
                                         className="bg-transparent w-full text-sm font-mono text-gray-400 mt-0.5 outline-none focus:text-white transition-colors" 
                                     />
                                 </div>
                                  <div className={cn("bg-[#1e2029] border border-white/5 rounded px-3 py-2 transition-all", slMode === 'PIPS' && "ring-1 ring-rose-500/50 bg-rose-500/5")}>
                                     <div className="text-[10px] text-rose-400 uppercase font-bold flex justify-between">
                                         Risk Pips
                                         {slMode === 'PIPS' && <Lock size={10} />}
                                     </div>
                                     <input 
                                         type="number" 
                                         value={slPips} 
                                         onFocus={() => setSlMode('PIPS')}
                                         onChange={e => handleSlPipsChange(parseFloat(e.target.value))}
                                         className="bg-transparent w-full text-sm font-mono text-white outline-none mt-0.5 font-bold" 
                                     />
                                 </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* 6. Minimax / Risk Citadel (Advanced) */}
            <div className="border border-white/5 rounded bg-[#16171d] overflow-hidden">
                <button 
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="w-full flex items-center justify-between p-3 text-xs font-bold text-gray-400 hover:text-white transition-colors bg-[#1e2029]"
                >
                    <span className="flex items-center gap-2"><Target size={12} /> Risk Citadel (AI)</span>
                    <Settings2 size={12} />
                </button>
                
                {showAdvanced && (
                    <div className="p-3 space-y-3 animate-in fade-in slide-in-from-top-1">
                        <div className="space-y-1">
                            <div className="flex justify-between text-[10px] text-gray-500 uppercase">
                                <span>Confidence</span>
                                <span>{(confidence * 100).toFixed(0)}%</span>
                            </div>
                            <input 
                                type="range" 
                                min="0.1" 
                                max="1.0" 
                                step="0.05"
                                value={confidence}
                                onChange={e => setConfidence(parseFloat(e.target.value))}
                                className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                            />
                        </div>

                        <div className="space-y-1">
                            <div className="flex justify-between text-[10px] text-gray-500 uppercase">
                                <span>Pain Threshold</span>
                                <span>${painThreshold}</span>
                            </div>
                             <div className="flex items-center bg-[#0b0c10] border border-white/10 rounded px-2">
                                <span className="text-gray-500 text-xs">$</span>
                                <input 
                                    type="number" 
                                    value={painThreshold}
                                    onChange={e => setPainThreshold(parseFloat(e.target.value))}
                                    className="bg-transparent w-full text-xs font-mono text-white p-1 outline-none"
                                />
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* 7. Position Math (Natural Flow) */}
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
                             <span className="text-rose-400 font-mono font-medium">-${(currentLots * 10 * spreadPips).toFixed(2)}</span>
                         </div>
                          <div className="flex justify-between">
                             <span className="text-gray-500">Trade Value</span>
                             <span className="text-gray-300 font-mono font-medium">${(currentLots * 100000 * currentPrice).toLocaleString([], {maximumFractionDigits:0})}</span>
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
                               {currentLots > 0 ? `${currentLots.toFixed(2)}` : '0.01'} LOTS @ MARKET
                            </div>
                        </>
                    )}
                </button>
            </div>
        </div>


    </div>
  );
};
