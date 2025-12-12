'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, CandlestickSeriesPartialOptions } from 'lightweight-charts';
import { Candle } from '@/lib/api/market';

interface CandleChartProps {
  data: Candle[];
  colors?: {
    backgroundColor?: string;
    lineColor?: string;
    textColor?: string;
    areaTopColor?: string;
    areaBottomColor?: string;
  };
}

export const CandleChart: React.FC<CandleChartProps> = ({ data, colors = {} }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const handleResize = () => {
      chartRef.current?.applyOptions({ width: chartContainerRef.current!.clientWidth });
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.backgroundColor || '#1e1e1e' },
        textColor: colors.textColor || 'white',
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    // Map API data to chart data format
    // Lightweight charts expects time as string (YYYY-MM-DD) or unix timestamp (seconds).
    // Our API returns ISO string. We can use unix timestamp.
    const chartData = data
      .map((item) => {
        const time = new Date(item.timestamp).getTime() / 1000;
        // Check for invalid dates
        if (isNaN(time)) return null;
        
        return {
        time: time as any, // Cast to any because lightweight-charts types can be strict about UTCTimestamp
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
      }})
      .filter((item): item is NonNullable<typeof item> => item !== null)
      .sort((a, b) => (a.time as number) - (b.time as number)); // Ensure sorted

    // Deduplicate by time if necessary (though API should handle this)
    const uniqueData = Array.from(new Map(chartData.map(item => [item.time, item])).values());

    candlestickSeries.setData(uniqueData);

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, colors]);

  return <div ref={chartContainerRef} className="w-full h-[400px]" />;
};
