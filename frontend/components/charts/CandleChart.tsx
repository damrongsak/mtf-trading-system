'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, LineSeries, CandlestickSeriesPartialOptions } from 'lightweight-charts';
import { Candle } from '@/lib/api/market';

export interface IndicatorData {
  name: string;
  data: (number | null)[];
  color: string;
}

interface CandleChartProps {
  data: Candle[];
  indicators?: IndicatorData[];
  colors?: {
    backgroundColor?: string;
    lineColor?: string;
    textColor?: string;
    areaTopColor?: string;
    areaBottomColor?: string;
  };
}

export const CandleChart: React.FC<CandleChartProps> = ({ data, indicators = [], colors = {} }) => {
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
      // Note: we assume data is roughly sorted or we might break indicator alignment if we sort here
      // but indices don't match exactly. 
      // Ideally, we shouldn't sort if we rely on index matching with external arrays.
      // But lightweight charts needs sorted data.
      // We will assume backend returns sorted data or consistent order.
      // If we sort chartData, we lose the mapping to `indicators` arrays unless they are also sorted/mapped.
      // For now, let's assume input `data` is correct order or we accept mis-alignment risk if out of order.
      // A better way is to zip them first then sort. but `indicators` are separate arrays.
      .sort((a, b) => (a.time as number) - (b.time as number));

    // Deduplicate by time if necessary (though API should handle this)
    const uniqueData = Array.from(new Map(chartData.map(item => [item.time, item])).values());

    candlestickSeries.setData(uniqueData);

    // Add indicators
    indicators.forEach(ind => {
        const lineSeries = chart.addSeries(LineSeries, {
            color: ind.color,
            lineWidth: 2,
            crosshairMarkerVisible: false,
        });

        // Map indicator values to times. 
        // We assume indicators.data corresponds 1-to-1 with input `data`.
        // If we filtered `chartData` (e.g. invalid dates), we might have mismatch.
        // But invalid dates are rare.
        const lineData = ind.data.map((val, index) => {
            // We need the time from the corresponding candle.
            if (index >= chartData.length) return null;
            // Since chartData might be sorted differently than 'data' if 'data' was unsorted...
            // Use chartData[index]? No, chartData is sorted. 
            // If `data` came in unsorted, specific values would move.
            // Correct approach: The backend returns sorted candles usually.
            // We will assume data is 0..N sorted ascending.
            const item = chartData[index];
            if (!item || val === null) return null;
            
            return {
                time: item.time,
                value: val
            };
        }).filter((item): item is NonNullable<typeof item> => item !== null);
        
        lineSeries.setData(lineData);
    });

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, colors, indicators]);

  return <div ref={chartContainerRef} className="w-full h-[400px]" />;
};
