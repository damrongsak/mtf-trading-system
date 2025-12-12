'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { CandleChart } from '@/components/charts/CandleChart';
import { fetchCandles, Candle } from '@/lib/api/market';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { calculateEMA, calculateRSI } from '@/lib/api/analysis';
import { IndicatorData } from '@/components/charts/CandleChart';

export default function MarketPage() {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [symbol, setSymbol] = useState('EUR_USD');
  const [timeframe, setTimeframe] = useState('H1');
  const [loading, setLoading] = useState(false);
  
  // Indicator State
  const [showEMA, setShowEMA] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [chartIndicators, setChartIndicators] = useState<IndicatorData[]>([]);

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

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Refetch indicators when candles change or toggles change
  useEffect(() => {
    if (candles.length > 0) {
        updateIndicators();
    }
  }, [candles, showEMA, showRSI]);

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

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
          Market Analysis
        </h1>
        <div className="flex gap-2">
            <Select value={symbol} onValueChange={setSymbol}>
                <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Symbol" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="EUR_USD">EUR/USD</SelectItem>
                    <SelectItem value="XAU_USD">XAU/USD</SelectItem>
                    <SelectItem value="GBP_USD">GBP/USD</SelectItem>
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
          <CardTitle>{symbol} - {timeframe}</CardTitle>
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
