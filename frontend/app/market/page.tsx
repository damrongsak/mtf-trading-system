'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import dynamic from 'next/dynamic';
const CandleChart = dynamic(() => import('@/components/charts/CandleChart').then(mod => mod.CandleChart), { ssr: false });
const ChartContainer = dynamic(() => import('@/components/charts/ChartContainer').then(mod => mod.ChartContainer), { ssr: false });
const IndicatorChart = dynamic(() => import('@/components/charts/IndicatorChart').then(mod => mod.IndicatorChart), { ssr: false });
import { IndicatorData } from '@/components/charts/CandleChart';
import { Time } from 'lightweight-charts';
import { fetchCandles, Candle } from '@/lib/api/market';
import { fetchSystemConfig } from '@/lib/api/system';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { calculateEMA, calculateRSI, calculateATR, calculateMACD, calculateADX } from '@/lib/api/analysis';
import { useLivePrices } from '@/lib/hooks/useLivePrices';
import { apiClient } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { RefreshCcw, Activity, Layers, BarChart2 } from 'lucide-react';

// Icons need lucide-react, assuming it's installed as it's common in Shadcn. 
// If not, we might need to remove them or use text.

interface UserPreferences {
    supported_symbols?: string[];
    default_symbol?: string;
}

// Default fallback until config loads
const DEFAULT_TIMEFRAMES = ['M15', 'H1', 'H4', 'D'];

export default function MarketPage() {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [symbol, setSymbol] = useState('EUR_USD');
  const [timeframe, setTimeframe] = useState('H1');
  const [availableTimeframes, setAvailableTimeframes] = useState<string[]>(DEFAULT_TIMEFRAMES);
  const [loading, setLoading] = useState(false);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  
  // Indicators
  const [showEMA, setShowEMA] = useState(false);
  const [showEMA50, setShowEMA50] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [showATR, setShowATR] = useState(false);
  const [showMACD, setShowMACD] = useState(false);
  const [showADX, setShowADX] = useState(false);
  const [chartIndicators, setChartIndicators] = useState<IndicatorData[]>([]);

  // Live Hook
  const { prices, connected } = useLivePrices([symbol]);

  useEffect(() => {
    // Load System Config
    fetchSystemConfig().then(config => {
        if (config.supported_timeframes && config.supported_timeframes.length > 0) {
            setAvailableTimeframes(config.supported_timeframes);
        }
    }).catch(err => console.error("Failed to load system config", err));

    // Load User Preferences
    apiClient.get('/api/v1/settings/preferences').then(res => {
        setPreferences(res.data);
        if (res.data.default_symbol) setSymbol(res.data.default_symbol);
    }).catch(err => console.error("Failed to load preferences", err));
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setCandles([]); // Clear old data to show loading state for new symbol
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

  // Live Updates
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

  // Indicator logic
  useEffect(() => {
    if (candles.length === 0) return;
    updateIndicators();
  }, [candles.length, showEMA, showEMA50, showRSI, showATR, showMACD, showADX, symbol, timeframe]); // Recalc mainly on new candles or toggle. live tick update ignored for perf.

  const updateIndicators = async () => {
      const newInds: IndicatorData[] = [];
      const closes = candles.map(c => c.close);
      
      if (closes.length === 0) return;

      if (showEMA) {
          try {
              const res = await calculateEMA({ data: closes, span: 200 });
              newInds.push({ name: 'EMA 200', data: res, color: '#2563eb' }); // blue-600
          } catch(e) {
              console.error("EMA Calculation failed:", e);
          }
      }
      
      if (showEMA50) {
          try {
              const res = await calculateEMA({ data: closes, span: 50 });
              newInds.push({ name: 'EMA 50', data: res, color: '#f59e0b' }); // amber-500
          } catch(e) {
              console.error("EMA 50 Calculation failed:", e);
          }
      }

      if (showRSI) {
          try {
              const res = await calculateRSI({ close: closes, window: 14 });
              newInds.push({ name: 'RSI 14', data: res, color: '#a855f7', priceScaleId: 'left' }); // purple-500
          } catch(e) {
               console.error("RSI Calculation failed:", e);
          }
      }
      
      if (showATR) {
          try {
              const res = await calculateATR({ 
                  high: candles.map(c => c.high), 
                  low: candles.map(c => c.low), 
                  close: closes, 
                  window: 14 
              });
              newInds.push({ name: 'ATR 14', data: res, color: '#ec4899', priceScaleId: 'left' }); // pink-500
          } catch(e) {
              console.error("ATR Failed:", e);
          }
      }
      
      if (showMACD) {
          try {
              const res = await calculateMACD({ close: closes });
              newInds.push({ name: 'MACD', data: res.macd, color: '#22d3ee', priceScaleId: 'left' }); // cyan-400
              newInds.push({ name: 'Signal', data: res.signal, color: '#f472b6', priceScaleId: 'left' }); // pink-400
          } catch(e) {
              console.error("MACD Failed:", e);
          }
      }
      
      if (showADX) {
          try {
              const res = await calculateADX({ 
                  high: candles.map(c => c.high), 
                  low: candles.map(c => c.low), 
                  close: closes, 
                  length: 14 
              });
              newInds.push({ name: 'ADX', data: res.adx, color: '#eab308', priceScaleId: 'left' }); // yellow-500
          } catch(e) {
              console.error("ADX Failed:", e);
          }
      }
      
      console.log(`[MarketPage] Updated indicators: ${newInds.map(i => i.name).join(', ')}`);
      setChartIndicators(newInds);
  };

  const supportedSymbols = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'BTC_USD', 'ETH_USD'];
  if (preferences?.default_symbol && !supportedSymbols.includes(preferences.default_symbol)) {
      supportedSymbols.unshift(preferences.default_symbol);
  }
  const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0;
  const prevClose = candles.length > 1 ? candles[candles.length - 2].close : currentPrice;
  const change = currentPrice - prevClose;
  const changePercent = prevClose ? (change / prevClose) * 100 : 0;
  const isUp = change >= 0;

  console.log('[MarketPage] Render:', { 
      candles: candles.length, 
      loading, 
      symbol, 
      indicators: chartIndicators.length 
  });

  return (
    <div className="min-h-screen bg-black/95 text-gray-100 p-6 space-y-8 font-sans">
      
      {/* Header Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="md:col-span-1 border-white/5 bg-white/5 backdrop-blur-xl">
             <CardContent className="p-6 flex flex-col justify-center h-full relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Activity size={48} />
                </div>
                <div className="flex items-center gap-3 mb-2">
                     <h2 className="text-xl font-bold tracking-tight text-white">{symbol.replace('_', '/')}</h2>
                     <span className={cn("px-2 py-0.5 rounded text-xs font-bold", connected ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400")}>
                        {connected ? 'LIVE' : 'OFFLINE'}
                     </span>
                </div>
                <div className="flex items-baseline gap-3">
                    <span className="text-4xl font-mono font-medium text-white">
                        {currentPrice.toFixed(symbol.includes('JPY') ? 3 : 5)}
                    </span>
                    <span className={cn("text-sm font-medium", isUp ? "text-emerald-400" : "text-rose-400")}>
                        {isUp ? '+' : ''}{change.toFixed(5)} ({changePercent.toFixed(2)}%)
                    </span>
                </div>
             </CardContent>
          </Card>
          
          {/* Quick Stats (Mocked for layout) */}
           <Card className="md:col-span-3 border-white/5 bg-white/5 backdrop-blur-xl flex items-center p-0">
               <div className="grid grid-cols-3 w-full h-full divide-x divide-white/10">
                   <div className="p-6 flex flex-col justify-center">
                        <span className="text-muted-foreground text-xs uppercase tracking-wider">24h Volume</span>
                        <span className="text-2xl font-mono text-white mt-1">142.5M</span>
                   </div>
                    <div className="p-6 flex flex-col justify-center">
                        <span className="text-muted-foreground text-xs uppercase tracking-wider">24h High</span>
                        <span className="text-2xl font-mono text-emerald-400 mt-1">{(currentPrice * 1.002).toFixed(5)}</span>
                   </div>
                    <div className="p-6 flex flex-col justify-center">
                        <span className="text-muted-foreground text-xs uppercase tracking-wider">24h Low</span>
                        <span className="text-2xl font-mono text-rose-400 mt-1">{(currentPrice * 0.998).toFixed(5)}</span>
                   </div>
               </div>
           </Card>
      </div>

      {/* Chart Content */}
      <Card className="border-white/5 bg-white/[0.02] backdrop-blur-2xl shadow-2xl overflow-hidden min-h-[600px] flex flex-col">
          {/* Toolbar */}
          <div className="border-b border-white/10 p-4 flex flex-wrap gap-4 justify-between items-center bg-white/5">
              <div className="flex items-center gap-4">
                  <Select value={symbol} onValueChange={setSymbol}>
                      <SelectTrigger className="w-[180px] bg-black/20 border-white/10 text-white focus:ring-0 focus:border-white/20 h-10">
                          <SelectValue>{symbol.replace('_', '/')}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                          {supportedSymbols.map(s => (
                              <SelectItem key={s} value={s}>{s.replace('_', '/')}</SelectItem>
                          ))}
                      </SelectContent>
                  </Select>

                  <div className="h-6 w-px bg-white/10 mx-2" />

                  <div className="flex items-center gap-1 bg-black/20 rounded-lg p-1 border border-white/5">
                      {availableTimeframes.map(tf => (
                          <button
                              key={tf}
                              onClick={() => setTimeframe(tf)}
                              className={cn(
                                  "px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200",
                                  timeframe === tf 
                                      ? "bg-white/10 text-white shadow-sm" 
                                      : "text-gray-400 hover:text-white hover:bg-white/5"
                              )}
                          >
                              {tf}
                          </button>
                      ))}
                  </div>
              </div>

              <div className="flex items-center gap-3">
                   <div className="flex items-center gap-2 mr-4 flex-wrap">
                       <button onClick={() => setShowEMA(!showEMA)} className={cn("flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-all", showEMA ? "bg-blue-500/20 border-blue-500/50 text-blue-400" : "border-white/10 text-gray-400 hover:border-white/20")}>EMA 200</button>
                       <button onClick={() => setShowEMA50(!showEMA50)} className={cn("flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-all", showEMA50 ? "bg-amber-500/20 border-amber-500/50 text-amber-500" : "border-white/10 text-gray-400 hover:border-white/20")}>EMA 50</button>
                       <button onClick={() => setShowRSI(!showRSI)} className={cn("flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-all", showRSI ? "bg-purple-500/20 border-purple-500/50 text-purple-400" : "border-white/10 text-gray-400 hover:border-white/20")}>RSI</button>
                       <button onClick={() => setShowATR(!showATR)} className={cn("flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-all", showATR ? "bg-pink-500/20 border-pink-500/50 text-pink-400" : "border-white/10 text-gray-400 hover:border-white/20")}>ATR</button>
                       <button onClick={() => setShowMACD(!showMACD)} className={cn("flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-all", showMACD ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-400" : "border-white/10 text-gray-400 hover:border-white/20")}>MACD</button>
                       <button onClick={() => setShowADX(!showADX)} className={cn("flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-all", showADX ? "bg-yellow-500/20 border-yellow-500/50 text-yellow-500" : "border-white/10 text-gray-400 hover:border-white/20")}>ADX</button>
                   </div>
                   
                   <Button variant="outline" size="sm" onClick={loadData} disabled={loading} className="border-white/10 bg-white/5 hover:bg-white/10 text-white hover:text-white w-10 h-10">
                      <RefreshCcw size={18} className={cn(loading && "animate-spin")} />
                   </Button>
              </div>
          </div>
          
          <div className="flex-1 relative min-h-[500px] w-full bg-gradient-to-b from-transparent to-black/20 p-4">
               {candles.length > 0 ? (
                   <ChartContainer>
                       {/* Main Chart (Price + Overlays) */}
                       <CandleChart 
                          data={candles} 
                          indicators={chartIndicators.filter(i => i.priceScaleId !== 'left')} // Pass only overlays
                          colors={{
                              backgroundColor: 'transparent',
                              textColor: '#737373', // neutral-500
                          }} 
                       />
                       
                       {/* Stacked Oscillators */}
                       {/* RSI */}
                       {chartIndicators.filter(i => i.name.startsWith('RSI')).map(ind => (
                           <IndicatorChart 
                              key={ind.name}
                              type="RSI"
                              data={ind.data.map((v, i) => ({ time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, value: v || 0 }))} // Mapping needs safety
                              height={150}
                              colors={{ lineColor: ind.color, textColor: '#737373' }}
                           />
                       ))}

                       {/* ATR */}
                       {chartIndicators.filter(i => i.name.startsWith('ATR')).map(ind => (
                           <IndicatorChart 
                               key={ind.name}
                               type="ATR"
                               data={ind.data.map((v, i) => ({ time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, value: v || 0 }))}
                               height={150}
                               colors={{ lineColor: ind.color, textColor: '#737373' }}
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
                                    // Hist is usually MACD - Signal but API returns it? 
                                    // Our API calculateMACD response includes hist. But updateIndicators only pushes MACD and Signal as separate lines?
                                    // Ah, updatedIndicators pushed MACD and Signal separately. 
                                    // We should fix updateIndicators to maintain grouping or reconstructing here.
                                    // For now reconstructing:
                                    return macd.map((v, i) => ({
                                        time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time,
                                        value: v || 0,
                                        signal: signal[i] || 0,
                                        hist: (v || 0) - (signal[i] || 0) // Naive hist calc if not stored
                                    }));
                                })()}
                                height={200}
                                colors={{ lineColor: '#22d3ee', signalColor: '#f472b6', histColor: '#26a69a', textColor: '#737373' }}
                            />
                        )}

                        {/* ADX */}
                        {chartIndicators.filter(i => i.name.startsWith('ADX')).map(ind => (
                           <IndicatorChart 
                               key={ind.name}
                               type="ADX"
                               data={ind.data.map((v, i) => ({ time: new Date(candles[i]?.timestamp).getTime() / 1000 as Time, value: v || 0 }))}
                               height={150}
                               colors={{ lineColor: ind.color, textColor: '#737373' }}
                           />
                       ))}

                   </ChartContainer>
               ) : (
                   <div className="absolute inset-0 flex items-center justify-center text-gray-500 flex-col gap-2">
                       {loading ? (
                           <>
                              <RefreshCcw className="animate-spin mb-2" />
                              <span>Loading Market Data...</span>
                           </>
                       ) : (
                           <span>Select a symbol to begin analysis</span>
                       )}
                   </div>
               )}
          </div>
      </Card>
    </div>
  );
}
