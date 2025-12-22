'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { CandleChart } from '@/components/charts/CandleChart';
import { fetchCandles, Candle } from '@/lib/api/market';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { calculateEMA, calculateRSI } from '@/lib/api/analysis';
import { IndicatorData } from '@/components/charts/CandleChart';
import { useLivePrices } from '@/lib/hooks/useLivePrices';
import { apiClient } from '@/lib/api/client';

interface UserPreferences {
    supported_symbols?: string[];
    default_symbol?: string;
    preferred_timeframes?: string[];
}

export default function MarketPage() {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [symbol, setSymbol] = useState('EUR_USD');
  const [timeframe, setTimeframe] = useState('H1');
  const [loading, setLoading] = useState(false);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  
  // Indicator State
  const [showEMA, setShowEMA] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [chartIndicators, setChartIndicators] = useState<IndicatorData[]>([]);

  // Live Data Hook
  // We only subscribe to the current symbol
  const { prices, connected } = useLivePrices([symbol]);

  // Fetch Preferences
  useEffect(() => {
    apiClient.get('/api/v1/settings/preferences').then(res => {
        setPreferences(res.data);
        if (res.data.default_symbol) setSymbol(res.data.default_symbol);
    }).catch(err => console.error("Failed to load preferences", err));
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchCandles({
        symbol,
        timeframe,
        count: 500
      });
      setCandles(data);
    } catch (error) {
      console.error("Failed to fetch candles", error);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe]);

  // Initial Load
  useEffect(() => {
    loadData();
  }, [loadData]);


  // Handle Live Updates
  useEffect(() => {
      if (!prices[symbol]) return;
      
      const latestPrice = prices[symbol];
      if (latestPrice.type !== 'PRICE') return;

      const price = latestPrice.bid; // Using Bid for chart usually, or Mid
      const time = new Date(latestPrice.time);

      setCandles(prev => {
          if (prev.length === 0) return prev;
          
          const lastCandle = { ...prev[prev.length - 1] };
          const lastCandleTime = new Date(lastCandle.timestamp);
          
          // Check if we need a new candle
          // Simple logic: if new time is significantly past last candle based on timeframe
          // This logic depends on strict timeframe parsing which is complex.
          // For MVP, we update the LAST candle if it's "recent" (e.g. within timeframe duration), 
          // otherwise we append (or reload).
          // Ideally, the backend gives us the candle open time. 
          // Since we don't have that easily here without parsing `timeframe`, 
          // we will just update the Close/High/Low of the last candle for visual "aliveness".
          // And RELOAD periodically or on specific event for strict accuracy.
          
          // Updating current candle
          lastCandle.close = price;
          lastCandle.high = Math.max(lastCandle.high, price);
          lastCandle.low = Math.min(lastCandle.low, price);
          
          // Create new array to trigger re-render
          const newCandles = [...prev];
          newCandles[newCandles.length - 1] = lastCandle;
          return newCandles;
      });
  }, [prices, symbol]);


  // Refetch indicators when candles change or toggles change
  // Debounced or limited to avoid heavy recalc on every tick?
  // For now, we only recalc indicators if candles change length or user toggles.
  // We won't recalc indicators on every live tick to save performance for this MVP.
  useEffect(() => {
    if (candles.length > 0) {
        // Only update if not result of live tick (optimization: check length change?)
        // Or just let it update.
        updateIndicators();
    }
  }, [candles.length, showEMA, showRSI, symbol, timeframe]); // removed 'candles' dependency to avoid recalc on tick

  const updateIndicators = async () => {
      const newIndicators: IndicatorData[] = [];
      const closePrices = candles.map(c => c.close);

      if (showEMA) {
          try {
              const emaValues = await calculateEMA({ data: closePrices, span: 200 });
              newIndicators.push({
                  name: 'EMA 200',
                  data: emaValues,
                  color: '#2962FF'
              });
          } catch (e) {
              console.error("Failed to calc EMA", e);
          }
      }

      if (showRSI) {
          try {
              const rsiValues = await calculateRSI({ close: closePrices, window: 14 });
              newIndicators.push({
                  name: 'RSI 14',
                  data: rsiValues,
                  color: '#FF6D00'
              });
          } catch (e) {
              console.error("Failed to calc RSI", e);
          }
      }

      setChartIndicators(newIndicators);
  };

  const supportedSymbols = preferences?.supported_symbols || ['EUR_USD', 'XAU_USD', 'GBP_USD', 'BTC_USD'];

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
          Market Analysis
        </h1>
        <div className="flex gap-2 items-center">
            {connected && <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" title="Live Connection" />}
            
            <Select value={symbol} onValueChange={setSymbol}>
                <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Symbol" />
                </SelectTrigger>
                <SelectContent>
                    {supportedSymbols.map(s => (
                        <SelectItem key={s} value={s}>{s.replace('_', '/')}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
            <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger className="w-[100px]">
                    <SelectValue placeholder="Timeframe" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="M15">M15</SelectItem>
                    <SelectItem value="H1">H1</SelectItem>
                    <SelectItem value="H4">H4</SelectItem>
                    <SelectItem value="D">Daily</SelectItem>
                </SelectContent>
            </Select>
          <div className="flex items-center space-x-2">
            <input 
                type="checkbox" 
                id="ema" 
                checked={showEMA} 
                onChange={(e) => setShowEMA(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
            <label htmlFor="ema" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              EMA 200
            </label>
          </div>
          <div className="flex items-center space-x-2">
            <input 
                type="checkbox" 
                id="rsi" 
                checked={showRSI} 
                onChange={(e) => setShowRSI(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
            <label htmlFor="rsi" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              RSI 14
            </label>
          </div>
          <Button onClick={loadData} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </div>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle>{symbol.replace('_', '/')} - {timeframe}</CardTitle>
        </CardHeader>
        <CardContent>
          {candles.length > 0 ? (
            <div className="rounded-lg overflow-hidden border border-border/50">
                <CandleChart data={candles} indicators={chartIndicators} />
            </div>
          ) : (
            <div className="h-[400px] flex items-center justify-center text-muted-foreground">
              {loading ? 'Loading data...' : 'No data available'}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
