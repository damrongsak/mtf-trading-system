'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, LineSeries, Time, CandlestickData, SeriesMarker, createSeriesMarkers, ISeriesMarkersPluginApi } from 'lightweight-charts';
import { useChartSync } from './ChartContainer';
import { Candle } from '@/lib/api/market';

export interface IndicatorData {
  name: string;
  data: (number | null)[];
  color: string;
  priceScaleId?: string;
}

interface CandleChartProps {
  data: Candle[];
  indicators?: IndicatorData[];
  markers?: SeriesMarker<Time>[]; // New Prop
  colors?: {
    backgroundColor?: string;
    lineColor?: string;
    textColor?: string;
    areaTopColor?: string;
    areaBottomColor?: string;
  };
}

export const CandleChart: React.FC<CandleChartProps> = ({ data, indicators = [], markers = [], colors = {} }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const indicatorSeriesRefs = useRef<Map<string, ISeriesApi<"Line">>>(new Map());
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  
  // Use Sync Context
  const registerChart = useChartSync();

  // 1. Initialize Chart (Once)
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.backgroundColor || 'transparent' }, 
        textColor: colors.textColor || '#d1d5db',
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
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

    // Create Main Series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981', // emerald-500
      downColor: '#ef4444', // red-500
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });
    seriesRef.current = candlestickSeries;

    // Initialize Markers Plugin
    try {
        markersPluginRef.current = createSeriesMarkers(candlestickSeries, []);
    } catch (e) {
        console.error('[CandleChart] Failed to create markers plugin:', e);
    }

    chartRef.current = chart;
    
    // Register for sync
    let unregister: (() => void) | void;
    if (registerChart) unregister = registerChart(chart, candlestickSeries);

    // Resize Handler using ResizeObserver
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ 
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight
        });
      }
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      if (typeof unregister === 'function') unregister();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      markersPluginRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount

  // 2. Update Data (When data changes)
  useEffect(() => {
    if (!chartRef.current || !seriesRef.current) return;

    // Format Data
    const formattedData = data
      .map((item) => {
        const time = new Date(item.timestamp).getTime() / 1000;
        if (isNaN(time)) {
             return null;
        }
        return {
          time: time as Time,
          open: Number(item.open),
          high: Number(item.high),
          low: Number(item.low),
          close: Number(item.close),
        };
      })
      .filter((item): item is CandlestickData<Time> => item !== null)
      .sort((a, b) => (a.time as number) - (b.time as number));

    // Dedup
    const uniqueData = Array.from(new Map(formattedData.map(item => [item.time, item])).values());
    
    seriesRef.current.setData(uniqueData);
    
  }, [data]);

  // 3. Update Markers (New Effect)
  useEffect(() => {
    if (!markersPluginRef.current) return;
    try {
        markersPluginRef.current.setMarkers(markers);
    } catch (e) {
        console.error('[CandleChart] Error setting markers:', e);
    }
  }, [markers]);

  // 4. Update Indicators (Overlays ONLY)
  useEffect(() => {
    if (!chartRef.current || !seriesRef.current) return;
    
    // Clean up old indicators
    indicatorSeriesRefs.current.forEach(series => chartRef.current?.removeSeries(series));
    indicatorSeriesRefs.current.clear();

    const candleTimes = data.map(d => new Date(d.timestamp).getTime() / 1000).sort((a,b) => a-b);

    const overlayIndicators = indicators.filter(i => i.priceScaleId !== 'left');

    overlayIndicators.forEach(ind => {
        const lineSeries = chartRef.current!.addSeries(LineSeries, {
            color: ind.color,
            lineWidth: 2,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });

        const lineData = ind.data.map((val, i) => {
             if (val === null || i >= candleTimes.length) return null;
             return {
                 time: candleTimes[i] as Time,
                 value: val
             };
        }).filter((item): item is {time: Time, value: number} => item !== null);

        lineSeries.setData(lineData);
        indicatorSeriesRefs.current.set(ind.name, lineSeries);
    });

  }, [indicators, data]); 

  return <div ref={chartContainerRef} className="w-full h-full" />;
};

