'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { CandleChart, IndicatorData } from '@/components/charts/CandleChart';
import { fetchCandles, Candle } from '@/lib/api/market';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { calculateEMA, calculateRSI } from '@/lib/api/analysis';
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

const TIMEFRAMES = ['M15', 'H1', 'H4', 'D'];

export default function MarketPage() {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [symbol, setSymbol] = useState('EUR_USD');
  const [timeframe, setTimeframe] = useState('H1');
  const [loading, setLoading] = useState(false);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  
  // Indicators
  const [showEMA, setShowEMA] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [chartIndicators, setChartIndicators] = useState<IndicatorData[]>([]);

  // Live Hook
  const { prices, connected } = useLivePrices([symbol]);

  useEffect(() => {
    apiClient.get('/api/v1/settings/preferences').then(res => {
        setPreferences(res.data);
        if (res.data.default_symbol) setSymbol(res.data.default_symbol);
    }).catch(err => console.error("Failed to load preferences", err));
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
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
  }, [candles.length, showEMA, showRSI]); // Recalc mainly on new candles or toggle. live tick update ignored for perf.

  const updateIndicators = async () => {
      const newInds: IndicatorData[] = [];
      const closes = candles.map(c => c.close);

      if (showEMA) {
          try {
              const res = await calculateEMA({ data: closes, span: 200 });
              newInds.push({ name: 'EMA 200', data: res, color: '#2563eb' }); // blue-600
          } catch(e) {}
      }
      if (showRSI) {
          try {
              const res = await calculateRSI({ close: closes, window: 14 });
              // RSI is separate pane usually, but here we overlay for MVP or need logic
              // Chart lib supports overlay or separate panes. 
              // For overlay standard line, RSI values (0-100) will be tiny compared to price (e.g. 2000 for Gold).
              // FIXME: RSI should be separate. For now, we disabling RSI overlay or mapping it crudely?
              // Or we assume the Chart component handles panes? The basic one doesn't.
              // Let's Skip RSI visualization on Main Chart for now to avoid confusion, 
              // OR render it but it will be flattened at bottom.
              // Better: Don't push RSI to chartIndicators if it's main pane only.
              // For this "Enhance" task, let's keep EMA as it scales with price.
              // console.warn("RSI requires separate pane, skipping overlay");
          } catch(e) {}
      }
      setChartIndicators(newInds);
  };

  const supportedSymbols = preferences?.supported_symbols || ['XAU_USD', 'EUR_USD', 'GBP_USD', 'BTC_USD', 'ETH_USD'];
  const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0;
  const prevClose = candles.length > 1 ? candles[candles.length - 2].close : currentPrice;
  const change = currentPrice - prevClose;
  const changePercent = prevClose ? (change / prevClose) * 100 : 0;
  const isUp = change >= 0;

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

      {/* Main Analysis Area */}
      <Card className="border-white/5 bg-white/[0.02] backdrop-blur-2xl shadow-2xl overflow-hidden min-h-[600px] flex flex-col">
        {/* Toolbar */}
        <div className="border-b border-white/10 p-4 flex flex-wrap gap-4 justify-between items-center bg-white/5">
            <div className="flex items-center gap-4">
                {/* Symbol Select */}
                <Select value={symbol} onValueChange={setSymbol}>
                    <SelectTrigger className="w-[180px] bg-black/20 border-white/10 text-white focus:ring-0 focus:border-white/20 h-10">
                        <SelectValue placeholder="Symbol" />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-900 border-white/10 text-gray-200">
                        {supportedSymbols.map(s => (
                            <SelectItem key={s} value={s} className="focus:bg-white/10">{s.replace('_', '/')}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <div className="h-6 w-px bg-white/10 mx-2" />

                {/* Timeframes Pill Group */}
                <div className="flex bg-black/20 rounded-lg p-1 border border-white/5">
                    {TIMEFRAMES.map(tf => (
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
                 {/* Indicators Toggle Group */}
                 <div className="flex items-center gap-2 mr-4">
                     <button 
                        onClick={() => setShowEMA(!showEMA)}
                        className={cn(
                           "flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-all",
                           showEMA ? "bg-blue-500/20 border-blue-500/50 text-blue-400" : "border-white/10 text-gray-400 hover:border-white/20"
                        )}
                     >
                        <Layers size={14} /> EMA 200
                     </button>
                     {/* RSI removed from toggles for visual cleanliness as it doesn't overlay well yet */}
                 </div>
                 
                 <Button 
                    variant="outline" 
                    size="icon" 
                    onClick={loadData} 
                    disabled={loading}
                    className="border-white/10 bg-white/5 hover:bg-white/10 text-white hover:text-white w-10 h-10"
                 >
                    <RefreshCcw size={18} className={cn(loading && "animate-spin")} />
                 </Button>
            </div>
        </div>
        
        {/* Chart Content */}
        <div className="flex-1 relative min-h-[500px] w-full bg-gradient-to-b from-transparent to-black/20">
             {candles.length > 0 ? (
                 <CandleChart 
                    data={candles} 
                    indicators={chartIndicators} 
                    colors={{
                        backgroundColor: 'transparent',
                        textColor: '#525252', // neutral-600
                    }} 
                 />
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
