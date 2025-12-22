'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, LineSeries, Time, CandlestickData } from 'lightweight-charts';
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
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const indicatorSeriesRefs = useRef<Map<string, ISeriesApi<"Line">>>(new Map());

  // 1. Initialize Chart (Once)
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.backgroundColor || 'transparent' }, // Transparent for glassmorphism
        textColor: colors.textColor || '#d1d5db', // gray-300
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      crosshair: {
        mode: 1, // Magnet
        vertLine: {
             labelBackgroundColor: '#2962FF',
        },
        horzLine: {
             labelBackgroundColor: '#2962FF',
        }
      }
    });

    chartRef.current = chart;

    // Create Main Series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981', // emerald-500
      downColor: '#ef4444', // red-500
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });
    seriesRef.current = candlestickSeries;

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current!.clientWidth });
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, []); // Run once on mount

  // 2. Update Data (When data changes)
  useEffect(() => {
    if (!chartRef.current || !seriesRef.current) return;

    // Format Data
    const formattedData = data
      .map((item) => {
        const time = new Date(item.timestamp).getTime() / 1000;
        if (isNaN(time)) return null;
        return {
          time: time as Time,
          open: item.open,
          high: item.high,
          low: item.low,
          close: item.close,
        };
      })
      .filter((item): item is CandlestickData<Time> => item !== null)
      .sort((a, b) => (a.time as number) - (b.time as number));

    // Dedup
    const uniqueData = Array.from(new Map(formattedData.map(item => [item.time, item])).values());
    
    seriesRef.current.setData(uniqueData);
    
    // Fit content if initial load (optional, maybe check if data size changed significantly?)
     // chartRef.current.timeScale().fitContent(); 
  }, [data]);

  // 3. Update Indicators
  useEffect(() => {
    if (!chartRef.current) return;
    
    // Clean up old indicators that are not in the new list (?) 
    // Or just clear all and re-add. For simplicity: Clear and Re-add.
    // Ideally we diff, but 'indicators' prop is usually a new array.
    
    indicatorSeriesRefs.current.forEach(series => chartRef.current?.removeSeries(series));
    indicatorSeriesRefs.current.clear();

    const candleTimes = data.map(d => new Date(d.timestamp).getTime() / 1000).sort((a,b) => a-b);

    indicators.forEach(ind => {
        const lineSeries = chartRef.current!.addSeries(LineSeries, {
            color: ind.color,
            lineWidth: 2,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });

        const lineData = ind.data.map((val, i) => {
             // Map based on index with candle data
             // Assumes 1-to-1 mapping with input 'data' prop
             if (val === null || i >= candleTimes.length) return null;
             return {
                 time: candleTimes[i] as Time,
                 value: val
             };
        }).filter((item): item is {time: Time, value: number} => item !== null);

        lineSeries.setData(lineData);
        indicatorSeriesRefs.current.set(ind.name, lineSeries);
    });

  }, [indicators, data]); // DEPENDS ON DATA because needed for time mapping

  return <div ref={chartContainerRef} className="w-full h-[500px]" />;
};
