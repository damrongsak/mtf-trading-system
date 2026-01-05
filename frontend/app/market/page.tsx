'use client';

import React, { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
const CandleChart = dynamic(() => import('@/components/charts/CandleChart').then(mod => mod.CandleChart), { ssr: false });
const ChartContainer = dynamic(() => import('@/components/charts/ChartContainer').then(mod => mod.ChartContainer), { ssr: false });
const IndicatorChart = dynamic(() => import('@/components/charts/IndicatorChart').then(mod => mod.IndicatorChart), { ssr: false });
import { IndicatorData } from '@/components/charts/CandleChart';
import { Time } from 'lightweight-charts';
import { fetchCandles, Candle } from '@/lib/api/market';
import { fetchSystemConfig } from '@/lib/api/system';
import { calculateEMA, calculateRSI, calculateATR, calculateMACD, calculateADX } from '@/lib/api/analysis';
import { useLivePrices } from '@/lib/hooks/useLivePrices';

import { cn } from '@/lib/utils';
import { RefreshCcw, Activity, TrendingUp, BarChart2, Zap, Layers, Maximize2, Minimize2, ChevronDown, ChevronRight, Layout } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { OpenInterestAnalytics } from '@/components/data/OpenInterestAnalytics';
import { useBrokerReference } from '@/context/BrokerReferenceContext';

// --- Types ---

const DEFAULT_TIMEFRAMES = ['M5', 'M15', 'H1', 'H4', 'D', 'W', 'M'];

export default function MarketPage() {
  // --- State: Market Data ---
  const [candles, setCandles] = useState<Candle[]>([]);
  const [symbol, setSymbol] = useState('XAU_USD');
  const [timeframe, setTimeframe] = useState('H1');
  const [availableTimeframes, setAvailableTimeframes] = useState<string[]>(DEFAULT_TIMEFRAMES);
  const [loading, setLoading] = useState(false);


  // --- State: Indicators ---
  const [showEMA, setShowEMA] = useState(false);
  const [showEMA50, setShowEMA50] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [showATR, setShowATR] = useState(false);
  const [showMACD, setShowMACD] = useState(false);
  const [showADX, setShowADX] = useState(false);
  const [chartIndicators, setChartIndicators] = useState<IndicatorData[]>([]);
  
  // --- State: UI Layout ---
  const [showAnalytics, setShowAnalytics] = useState(true);
  const [mounted, setMounted] = useState(false);

  // --- Hooks ---
  const { prices, connected } = useLivePrices([symbol]);
  const { symbols: brokerSymbols } = useBrokerReference();

  // --- Effects: Initialization ---
  useEffect(() => {
    // Load System Config
    fetchSystemConfig().then(config => {
        if (config.supported_timeframes && config.supported_timeframes.length > 0) {
            setAvailableTimeframes(config.supported_timeframes);
        }
    }).catch(err => console.error("Failed to load system config", err));

    setMounted(true);
  }, []);

  // --- Effects: Data Loading ---
  const loadData = useCallback(async () => {
    setLoading(true);
    setCandles([]); // Clear old data
    try {
      const data = await fetchCandles({ symbol, timeframe, count: 500 });
      setCandles(data);
    } catch (error) {
      console.error("Failed to fetch candles", error);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe]);

  useEffect(() => { loadData(); }, [loadData]);

  // --- Effects: Live Price Updates ---
  useEffect(() => {
      if (!prices[symbol] || prices[symbol].type !== 'PRICE') return;
      
      const latest = prices[symbol];
      const price = latest.bid; 

      setCandles(prev => {
          if (prev.length === 0) return prev;
          const last = { ...prev[prev.length - 1] };
          
          // Simple visual update of last candle
          last.close = price;
          last.high = Math.max(last.high, price);
          last.low = Math.min(last.low, price);
          
          const newCandles = [...prev];
          newCandles[newCandles.length - 1] = last;
          return newCandles;
      });
  }, [prices, symbol]);

  // --- Effects: Indicators ---
  useEffect(() => {
    if (candles.length === 0) return;
    updateIndicators();
  }, [candles.length, showEMA, showEMA50, showRSI, showATR, showMACD, showADX, symbol, timeframe]);

  const updateIndicators = async () => {
      const newInds: IndicatorData[] = [];
      const closes = candles.map(c => c.close);
      
      if (closes.length === 0) return;

      // ... (Same Indicator Logic as before, keeping code clean) ...
      // Helper to handle promise errors silently
      const tryCalc = async (fn: () => Promise<any>, pushFn: (res: any) => void) => {
          try {
              const res = await fn();
              pushFn(res);
          } catch(e) { console.error("Indicator Calc Failed", e); }
      };

      if (showEMA) await tryCalc(() => calculateEMA({ data: closes, span: 200 }), (res) => newInds.push({ name: 'EMA 200', data: res, color: '#3b82f6' }));
      if (showEMA50) await tryCalc(() => calculateEMA({ data: closes, span: 50 }), (res) => newInds.push({ name: 'EMA 50', data: res, color: '#f59e0b' }));
      if (showRSI) await tryCalc(() => calculateRSI({ close: closes, window: 14 }), (res) => newInds.push({ name: 'RSI 14', data: res, color: '#a855f7', priceScaleId: 'left' }));
      if (showATR) await tryCalc(() => calculateATR({ high: candles.map(c => c.high), low: candles.map(c => c.low), close: closes, window: 14 }), (res) => newInds.push({ name: 'ATR 14', data: res, color: '#ec4899', priceScaleId: 'left' }));
      if (showMACD) {
           await tryCalc(() => calculateMACD({ close: closes }), (res) => {
               newInds.push({ name: 'MACD', data: res.macd, color: '#06b6d4', priceScaleId: 'left' });
               newInds.push({ name: 'Signal', data: res.signal, color: '#f472b6', priceScaleId: 'left' });
           });
      }
      if (showADX) await tryCalc(() => calculateADX({ high: candles.map(c => c.high), low: candles.map(c => c.low), close: closes, length: 14 }), (res) => newInds.push({ name: 'ADX', data: res.adx, color: '#eab308', priceScaleId: 'left' }));
      
      setChartIndicators(newInds);
  };

  // --- Derived Data ---
  const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0;
  const prevClose = candles.length > 1 ? candles[candles.length - 2].close : currentPrice;
  const change = currentPrice - prevClose;
  const changePercent = prevClose ? (change / prevClose) * 100 : 0;
  const isUp = change >= 0;

  // --- Render ---
  return (
    <div className="min-h-screen bg-black text-gray-300 font-sans selection:bg-blue-500/30">
        
        {/* Top Bar: Market Ticker */}
        <header className="border-b border-white/5 bg-gray-950/50 backdrop-blur-md sticky top-0 z-40 h-14 flex items-center px-6 justify-between">
            <div className="flex items-center gap-6">
                 {/* Symbol Selector embedded in header for quick switch */}
                <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-blue-500/10 rounded-md">
                        <Activity size={18} className="text-blue-500" />
                    </div>
                     <Select value={symbol} onValueChange={setSymbol}>
                        <SelectTrigger className="w-[140px] h-8 bg-transparent border-none text-white font-bold text-lg focus:ring-0 px-0">
                             <SelectValue>{symbol.replace('_', '/')}</SelectValue>
                        </SelectTrigger>
                        <SelectContent className="bg-gray-900 border-gray-800">
                            {brokerSymbols.size > 0 ? (
                                Array.from(brokerSymbols.values()).map(s => (
                                    <SelectItem key={s.id} value={s.symbol} className="text-gray-300 focus:bg-gray-800 focus:text-white">
                                        {s.symbol.replace('_', '/')}
                                    </SelectItem>
                                ))
                            ) : (
                                <SelectItem value={symbol} disabled>{symbol.replace('_', '/')}</SelectItem>
                            )}
                        </SelectContent>
                    </Select>
                </div>

                <div className="h-6 w-px bg-white/10" />

                {/* Price Stats */}
                <div className="flex items-baseline gap-3">
                    <span className="text-xl font-mono font-medium text-white tracking-tight">
                        {currentPrice.toFixed(symbol.includes('JPY') ? 3 : 5)}
                    </span>
                    <span className={cn("text-sm font-mono font-medium flex items-center", isUp ? "text-emerald-400" : "text-rose-400")}>
                        {isUp ? <TrendingUp size={14} className="mr-1" /> : <TrendingUp size={14} className="mr-1 rotate-180" />}
                        {change.toFixed(5)} ({changePercent.toFixed(2)}%)
                    </span>
                </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-gray-500">
                <div className="flex items-center gap-2">
                    <span>STATUS:</span>
                    <span className={cn("px-1.5 py-0.5 rounded-sm font-bold", connected ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500")}>
                        {connected ? 'LIVE' : 'DISCONNECTED'}
                    </span>
                </div>
                <span>VOL: 142.5M</span>
            </div>
        </header>

        <div className="p-4 space-y-4 max-w-[1920px] mx-auto">
            
            {/* Main Chart Panel */}
            <div className="border border-white/5 bg-gray-900/30 rounded-xl backdrop-blur-sm overflow-hidden shadow-2xl">
                {/* Toolbar */}
                <div className="bg-white/[0.02] border-b border-white/5 p-2 px-4 flex justify-between items-center">
                    <div className="flex items-center gap-1">
                        {mounted ? availableTimeframes.map(tf => (
                            <button
                                key={tf}
                                onClick={() => setTimeframe(tf)}
                                className={cn(
                                    "px-3 py-1 rounded text-xs font-bold transition-all",
                                    timeframe === tf 
                                        ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20" 
                                        : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                                )}
                            >
                                {tf}
                            </button>
                        )) : (
                            // Skeleton/Loading state for SSR to prevent mismatch if config loads fast
                            DEFAULT_TIMEFRAMES.slice(0, 4).map(tf => (
                                 <div key={tf} className="px-3 py-1 rounded text-xs font-bold text-gray-700 bg-white/5">
                                    {tf}
                                 </div>
                            ))
                        )}
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1 bg-black/20 p-1 rounded-lg border border-white/5">
                            {[
                                { id: 'EMA', label: 'EMA', state: showEMA, set: setShowEMA },
                                { id: 'RSI', label: 'RSI', state: showRSI, set: setShowRSI },
                                { id: 'MACD', label: 'MACD', state: showMACD, set: setShowMACD },
                                { id: 'ATR', label: 'ATR', state: showATR, set: setShowATR },
                            ].map(btn => (
                                <button
                                    key={btn.id}
                                    onClick={() => btn.set(!btn.state)}
                                    className={cn(
                                        "px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider transition-colors",
                                        btn.state ? "bg-white/10 text-white border border-white/10" : "text-gray-600 hover:text-gray-400"
                                    )}
                                >
                                    {btn.label}
                                </button>
                            ))}
                        </div>
                        <button onClick={loadData} className="p-2 hover:bg-white/10 rounded-md text-gray-500 hover:text-white transition-colors">
                            <RefreshCcw size={16} className={cn(loading && "animate-spin")} />
                        </button>
                    </div>
                </div>

                {/* Chart Area */}
                <div className="relative min-h-[600px] w-full bg-gradient-to-b from-transparent to-black/40">
                    {candles.length > 0 ? (
                       <ChartContainer>
                           {/* Main Chart (Price + Overlays) */}
                           <CandleChart 
                              data={candles} 
                              indicators={chartIndicators.filter(i => i.priceScaleId !== 'left')} // Pass only overlays
                              colors={{
                                  backgroundColor: 'transparent',
                                  textColor: '#525252',
                              }} 
                           />
                           
                           {/* Stacked Oscillators */}
                           {/* RSI */}
                           {chartIndicators.filter(i => i.name.startsWith('RSI')).map(ind => (
                               <IndicatorChart 
                                   key={ind.name}
                                   type="RSI"
                                   data={ind.data.map((v, i) => ({ time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, value: v || 0 }))} // Mapping needs safety
                                   height={120}
                                   colors={{ lineColor: ind.color, textColor: '#525252' }}
                               />
                           ))}

                           {/* ATR */}
                           {chartIndicators.filter(i => i.name.startsWith('ATR')).map(ind => (
                               <IndicatorChart 
                                   key={ind.name}
                                   type="ATR"
                                   data={ind.data.map((v, i) => ({ time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, value: v || 0 }))}
                                   height={120}
                                   colors={{ lineColor: ind.color, textColor: '#525252' }}
                               />
                           ))}

                            {/* MACD */}
                            {showMACD && (
                                <IndicatorChart 
                                    key="MACD"
                                    type="MACD"
                                    data={(() => {
                                        const macd = chartIndicators.find(i => i.name === 'MACD')?.data || [];
                                        const signal = chartIndicators.find(i => i.name === 'Signal')?.data || [];
                                        return macd.map((v, i) => ({
                                            time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time,
                                            value: v || 0,
                                            signal: signal[i] || 0,
                                            hist: (v || 0) - (signal[i] || 0)
                                        }));
                                    })()}
                                    height={180}
                                    colors={{ lineColor: '#22d3ee', signalColor: '#f472b6', histColor: '#26a69a', textColor: '#525252' }}
                                />
                            )}
                       </ChartContainer>
                   ) : (
                       <div className="absolute inset-0 flex items-center justify-center text-gray-600 flex-col gap-3">
                           {loading ? (
                               <>
                                  <RefreshCcw className="animate-spin text-blue-500" size={32} />
                                  <span className="font-mono text-sm">Loading Market Data...</span>
                               </>
                           ) : (
                               <span>Waiting for data...</span>
                           )}
                       </div>
                   )}
                </div>
            </div>

            {/* Analytics Panel Toggle */}
            <div className="flex items-center justify-between">
                <div onClick={() => setShowAnalytics(!showAnalytics)} className="flex items-center gap-2 cursor-pointer group select-none">
                     <div className={cn("p-1.5 rounded transition-colors group-hover:bg-blue-500/20", showAnalytics ? "bg-blue-500/10 text-blue-400" : "bg-white/5 text-gray-500")}>
                        {showAnalytics ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                     </div>
                     <span className={cn("text-sm font-bold tracking-wide uppercase transition-colors", showAnalytics ? "text-blue-400" : "text-gray-500 group-hover:text-gray-300")}>
                        Market Sentiment & Depth
                     </span>
                </div>
                <div className="h-px bg-white/5 flex-1 ml-4" />
            </div>

            {/* Analytics Content */}
            {showAnalytics && (
                <div className="animate-in fade-in slide-in-from-top-4 duration-300">
                     <OpenInterestAnalytics />
                </div>
            )}
        </div>
    </div>
  );
}

