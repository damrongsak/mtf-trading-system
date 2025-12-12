'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { CandleChart } from '@/components/charts/CandleChart';
import { fetchCandles, Candle } from '@/lib/api/market';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';

export default function MarketPage() {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [symbol, setSymbol] = useState('EUR_USD');
  const [timeframe, setTimeframe] = useState('H1');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [symbol, timeframe]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Calculate from/to if needed, or just ask for count
      // For now, let's just ask for last 500 candles
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
                <CandleChart data={candles} />
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
