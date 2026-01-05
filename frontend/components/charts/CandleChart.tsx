'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, LineSeries, Time, CandlestickData, SeriesMarker, createSeriesMarkers, ISeriesMarkersPluginApi, IPriceLine } from 'lightweight-charts';
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
    upColor?: string;
    downColor?: string;
    areaTopColor?: string;
    areaBottomColor?: string;
    wickUpColor?: string;
    wickDownColor?: string;
  };
  rightOffset?: number;
  bid?: number;
  ask?: number;
}

export const CandleChart: React.FC<CandleChartProps> = ({ data, indicators = [], markers = [], colors = {}, rightOffset = 15, bid, ask }) => {
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
        rightOffset: rightOffset,
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
      upColor: colors.lineColor || '#10b981', // Fallback or passed prop. logic below:
      // Actually we want specific up/down colors from prop if passed, else fallback
      // Since colors object is generic, let's use up/down if specific keys existed or map from proposal
      // But the interface passed was generic. Let's rely on standard logic: 
      // If user passed upColor/downColor map it. Wait, the interface in step 2 was:
      // colors?: { ... wickUpColor ... }
      // So we map:
      upColor: colors.lineColor || '#10b981', 
      downColor: colors.textColor || '#ef4444', 
      // Wait, 'lineColor' and 'textColor' are poor names for candles. 
      // Let's use the explicit props we defined in step 2 or rely on caller passing them in a cleaner way?
      // Actually, looking at the previous Replace, I added wickUpColor/wickDownColor.
      // I should have added upColor/downColor too if I wanted to be clean, but `colors` prop is `colors: { ... }`.
      // Let's assume the caller will pass `lineColor` as UP and `areaTopColor` as DOWN? No that's confusing.
      // Let's just use the props I added. Oh wait, I didn't add upColor/downColor to the interface in the previous step, only wicks.
      // Let's fix that in a subsequent step or just use what we have. 
      // Actually, standard LightWeightCharts uses upColor/downColor.
      // Let's use hardcoded logic for now based on the Plan: Blue/White.
      // But this is a generic component.
      // Let's re-read the Plan. "Pass specific colors: upColor: #3b82f6...".
      // So I should have added up/down color to the interface. I missed that in the previous step's Description but let's check the code I wrote.
      // I wrote: `wickUpColor?: string; wickDownColor?: string;`.
      // The interface already has `lineColor`.
      // Let's just add `upColor` and `downColor` to the interface now to be safe.
      
      // FOR NOW, to be safe and avoid breaking valid Typescript, I will use `colors['upColor']` pattern if I can't change the interface in this specific tool call (I can't mix ranges).
      // Actually, I will just use the `colors` object as any or extend it correctly in a fix-up.
      
      // CORRECT APPROACH: I'll overwrite this block to use the props, assuming I'll fix the interface in a second.
      upColor: (colors as any).upColor || '#10b981',
      downColor: (colors as any).downColor || '#ef4444',
      borderVisible: false,
      wickUpColor: colors.wickUpColor || '#10b981',
      wickDownColor: colors.wickDownColor || '#ef4444',
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

  // 5. Update Bid/Ask Lines
  const bidLineRef = useRef<IPriceLine | null>(null);
  const askLineRef = useRef<IPriceLine | null>(null);

  useEffect(() => {
    if (!seriesRef.current) return;

    // --- Bid Line ---
    if (bid !== undefined) {
        if (!bidLineRef.current) {
            bidLineRef.current = seriesRef.current.createPriceLine({
                price: bid,
                color: (colors as any).upColor || '#3b82f6', // Use Up Color
                lineWidth: 1,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'BID',
            });
        } else {
            bidLineRef.current.applyOptions({ price: bid });
        }
    } else if (bidLineRef.current) {
        seriesRef.current.removePriceLine(bidLineRef.current);
        bidLineRef.current = null;
    }

    // --- Ask Line ---
    if (ask !== undefined) {
        if (!askLineRef.current) {
            askLineRef.current = seriesRef.current.createPriceLine({
                price: ask,
                color: (colors as any).downColor || '#ffffff', // Use Down Color
                lineWidth: 1,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'ASK',
            });
        } else {
            askLineRef.current.applyOptions({ price: ask });
        }
    } else if (askLineRef.current) {
        seriesRef.current.removePriceLine(askLineRef.current);
        askLineRef.current = null;
    }

  }, [bid, ask, colors]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
};

