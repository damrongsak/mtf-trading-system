'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, LineSeries, Time, CandlestickData, SeriesMarker, createSeriesMarkers, ISeriesMarkersPluginApi, IPriceLine, LineWidth } from 'lightweight-charts';
import { useChartSync } from './ChartContainer';
import { Candle } from '@/lib/api/market';

export interface IndicatorData {
  name: string;
  data: (number | null | any)[];
  color: string;
  priceScaleId?: string;
}

export interface ChartPriceLine {
    price: number;
    color: string;
    title?: string;
    lineStyle?: number; // 0=Solid, 1=Dotted, 2=Dashed, 3=LargeDashed, 4=SparseDotted
    lineWidth?: number;
    axisLabelVisible?: boolean;
}

interface CandleChartProps {
  data: Candle[];
  indicators?: IndicatorData[];
  markers?: SeriesMarker<Time>[]; 
  priceLines?: ChartPriceLine[]; // New Prop
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

export const CandleChart: React.FC<CandleChartProps> = ({ data, indicators = [], markers = [], priceLines = [], colors = {}, rightOffset = 15, bid, ask }) => {
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
      upColor: colors.upColor || '#10b981',
      downColor: colors.downColor || '#ef4444',
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

    // Dynamic Cursor
    chart.subscribeCrosshairMove(param => {
        if (!chartContainerRef.current) return;
        
        // If hovering over data (candles)
        if (param.time || (param.seriesData && param.seriesData.size > 0)) {
            chartContainerRef.current.style.cursor = 'pointer';
        } else {
            // Restore default or fallback (Note: 'active:cursor-grabbing' is handled by CSS, 
            // but JS inline style overrides standard class CSS. We need to be careful not to break grabbing.)
            // Actually, LWC clears cursor style when not set? 
            // Let's set it to 'crosshair' as fallback, but check if dragging?
            // Simple approach: Set it to default empty, let CSS class handle the rest.
            chartContainerRef.current.style.cursor = ''; 
        }
    });

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
    indicatorSeriesRefs.current.forEach(series => {
        try {
            if (chartRef.current) {
                chartRef.current.removeSeries(series);
            }
        } catch (e) {
            console.warn('[CandleChart] Failed to remove series:', e);
        }
    });
    indicatorSeriesRefs.current.clear();

    const candleTimes = data.map(d => new Date(d.timestamp).getTime() / 1000).sort((a,b) => a-b);

    const overlayIndicators = indicators.filter(i => i.priceScaleId !== 'left');

    overlayIndicators.forEach(ind => {
        if (!chartRef.current) return;
        try {
            const lineSeries = chartRef.current.addSeries(LineSeries, {
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
        } catch (e) {
             console.error('[CandleChart] Failed to add indicator series:', e);
        }
    });

  }, [indicators, data]); 

  // 5. Update Bid/Ask Lines
  const bidLineRef = useRef<IPriceLine | null>(null);
  const askLineRef = useRef<IPriceLine | null>(null);

  useEffect(() => {
    if (!seriesRef.current) return;

    // Default colors if not provided in props (using explicit defaults for Bid/Ask clarity)
    const bidColor = (colors as any).upColor || '#22c55e'; // Green-500
    const askColor = (colors as any).downColor || '#ef4444'; // Red-500

    // --- Bid Line (Buy Price) ---
    if (bid !== undefined && bid !== null) {
        if (!bidLineRef.current) {
            bidLineRef.current = seriesRef.current.createPriceLine({
                price: bid,
                color: bidColor,
                lineWidth: 1,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'BID',
            });
        } else {
            bidLineRef.current.applyOptions({ price: bid, color: bidColor });
        }
    } else if (bidLineRef.current) {
        seriesRef.current.removePriceLine(bidLineRef.current);
        bidLineRef.current = null;
    }

    // --- Ask Line (Sell Price) ---
    if (ask !== undefined && ask !== null) {
        if (!askLineRef.current) {
            askLineRef.current = seriesRef.current.createPriceLine({
                price: ask,
                color: askColor,
                lineWidth: 1,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'ASK',
            });
        } else {
            askLineRef.current.applyOptions({ price: ask, color: askColor });
        }
    } else if (askLineRef.current) {
        seriesRef.current.removePriceLine(askLineRef.current);
        askLineRef.current = null;
    }

  }, [bid, ask, colors]);

  // 6. Update Generic Price Lines
  const priceLinesMapRef = useRef<Map<string, IPriceLine>>(new Map());

  useEffect(() => {
    if (!seriesRef.current) return;
    
    // Remove old lines
    priceLinesMapRef.current.forEach(line => {
        try {
           seriesRef.current?.removePriceLine(line);
        } catch(e) { console.warn(e); }
    });
    priceLinesMapRef.current.clear();

    // Add new lines
    priceLines.forEach((pl, index) => {
        try {
            const line = seriesRef.current?.createPriceLine({
                price: pl.price,
                color: pl.color,
                title: pl.title || '',
                lineStyle: pl.lineStyle ?? 2,
                lineWidth: (pl.lineWidth ?? 1) as LineWidth,
                axisLabelVisible: pl.axisLabelVisible ?? true,
            });
            if (line) {
                priceLinesMapRef.current.set(`line-${index}`, line);
            }
        } catch (e) {
            console.error('Failed to create price line:', e);
        }
    });

  }, [priceLines]);

  return <div ref={chartContainerRef} className="w-full flex-1 min-h-0" />;
};

