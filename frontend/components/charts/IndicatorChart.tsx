'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, LineSeries, AreaSeries, HistogramSeries, Time } from 'lightweight-charts';
import { useChartSync } from './ChartContainer';
import { cleanLineSeriesData, cleanHistogramData } from '@/lib/chartUtils';

export interface SingleIndicatorData {
  time: Time;
  value: number;
}

export interface MultiIndicatorData {
  time: Time;
  value: number; // For main line (e.g. MACD)
  signal?: number; // For signal line
  hist?: number; // For histogram
}

export interface IndicatorChartProps {
  data: MultiIndicatorData[];
  type: 'RSI' | 'MACD' | 'ATR' | 'ADX';
  height?: number;
  rightOffset?: number; // Added prop
  colors?: {
    lineColor?: string;
    signalColor?: string;
    histColor?: string;
    textColor?: string;
    backgroundColor?: string;
  };
  onChartReady?: (chart: IChartApi) => void;
}

export const IndicatorChart: React.FC<IndicatorChartProps> = ({ 
    data, 
    type, 
    height = 150, 
    rightOffset = 25, // Default to 25
    colors = {},
    onChartReady 
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const seriesRef = useRef<ISeriesApi<any>[]>([]);
  const unregisterSyncRef = useRef<(() => void) | void>(undefined);
  
  // Sync
  const registerChart = useChartSync();

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.backgroundColor || 'transparent' },
        textColor: colors.textColor || '#d1d5db',
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.02)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.02)' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: 'rgba(255, 255, 255, 0.1)',
        rightOffset: rightOffset, // Use prop
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        minimumWidth: 70,
        scaleMargins: {
            top: 0.1,
            bottom: 0.1,
        },
      },
      crosshair: {
        mode: 1,
      }
    });

    chartRef.current = chart;

    if (onChartReady) {
        onChartReady(chart);
    }

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (unregisterSyncRef.current) unregisterSyncRef.current();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = []; // Prevent stale series causing crashes on remount
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 1. Create Series (When type/color changes)
  useEffect(() => {
    if (!chartRef.current) return;

    // Cleanup old series
    seriesRef.current.forEach(s => {
        try {
            chartRef.current?.removeSeries(s);
        } catch (e) {
            console.warn("Failed to remove series", e);
        }
    });
    seriesRef.current = [];

    // Create new series based on type
    if (type === 'RSI' || type === 'ATR' || type === 'ADX') {
        const areaSeries = chartRef.current.addSeries(AreaSeries, {
            lineColor: colors.lineColor || '#2962FF',
            topColor: (colors.lineColor || '#2962FF') + '66', // 40% opacity (hex approximation 66)
            bottomColor: (colors.lineColor || '#2962FF') + '00', // 0% opacity
            lineWidth: 2,
        });
        seriesRef.current.push(areaSeries);

        // Register Sync
        if (registerChart && chartRef.current) {
             unregisterSyncRef.current = registerChart(chartRef.current, areaSeries);
        }
        
        // Add 70/30 lines for RSI
        if (type === 'RSI') {
              areaSeries.createPriceLine({ price: 70, color: 'rgba(255,255,255,0.3)', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
              areaSeries.createPriceLine({ price: 30, color: 'rgba(255,255,255,0.3)', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        }
    } else if (type === 'MACD') {
        // Histogram
        const histSeries = chartRef.current.addSeries(HistogramSeries, {
            color: colors.histColor || '#26a69a',
        });
        histSeries.createPriceLine({
             price: 0,
             color: 'rgba(255, 255, 255, 0.2)',
             lineWidth: 1,
             lineStyle: 2, // Dashed
             axisLabelVisible: false,
             title: '',
        });
        seriesRef.current.push(histSeries);
        
        // Register Sync
        if (registerChart && chartRef.current) {
             unregisterSyncRef.current = registerChart(chartRef.current, histSeries);
        }

        // MACD Line
        const macdSeries = chartRef.current.addSeries(LineSeries, {
            color: colors.lineColor || '#2962FF',
            lineWidth: 2,
        });
        seriesRef.current.push(macdSeries);

        // Signal Line
        const signalSeries = chartRef.current.addSeries(LineSeries, {
            color: colors.signalColor || '#FF6D00',
            lineWidth: 2,
        });
        seriesRef.current.push(signalSeries);
    }
  }, [type, colors.lineColor, colors.histColor, colors.signalColor]); // Re-create only if Structure/Style changes

  // 2. Update Data (When data changes) and FitContent ONLY on mount/first load
  const hasLoadedData = useRef(false);

  useEffect(() => {
    if (!chartRef.current || seriesRef.current.length === 0 || data.length === 0) return;

    if (type === 'RSI' || type === 'ATR' || type === 'ADX') {
        const lineData = cleanLineSeriesData(data);
        // Assuming seriesRef.current[0] is the main line
        seriesRef.current[0].setData(lineData);
    } else if (type === 'MACD') {
        // Order: [Hist, MACD, Signal]
        const histData = cleanHistogramData(data, colors.histColor || '#26a69a', '#ef5350', 'time', 'hist');
        const macdData = cleanLineSeriesData(data, 'time', 'value');
        const signalData = cleanLineSeriesData(data, 'time', 'signal');

        if (seriesRef.current[0]) seriesRef.current[0].setData(histData);
        if (seriesRef.current[1]) seriesRef.current[1].setData(macdData);
        if (seriesRef.current[2]) seriesRef.current[2].setData(signalData);
    }

    // Only fit content on initial data load to prevent jumping
    if (!hasLoadedData.current && data.length > 0) {
        chartRef.current.timeScale().fitContent();
        hasLoadedData.current = true;
    }
    
  }, [data, type, colors]); // Data updates

  // Legend State
  const [legendData, setLegendData] = React.useState<Map<string, number>>(new Map());

  // Subscribe to Crosshair
  useEffect(() => {
    if (!chartRef.current || !seriesRef.current.length) return;

    const updateLegend = (param: any) => {
       const newLegend = new Map<string, number>();
       
       // Default to last visible data point if no crosshair
       if (param.time === undefined) {
           // We could try to show the last bar, but LWC API for "last bar" isn't direct in param.
           // For simplicity, clear or keep last known? 
           // Better UX: Show values of the last candle in data.
           // However, accessing data directly from series is tricky without index.
           // Let's settle for showing nothing or persisting last known state?
           // Actually, let's just clear or show "n/a" implies no hover.
           // But user wants "output".
           // Strategy: If we have data, show the last item in data prop as default?
           if (data.length > 0) {
               const last = data[data.length - 1];
               newLegend.set('Main', last.value);
               if (last.signal !== undefined) newLegend.set('Signal', last.signal);
               if (last.hist !== undefined) newLegend.set('Hist', last.hist);
           }
       } else {
           // Iterate over all series
           param.seriesData.forEach((value: any, series: ISeriesApi<any>) => {
               // Identify series? map refs?
               // We need to know which series corresponds to what label.
               // We put them in seriesRef.current in order: [Main, (Hist?), (Signal?)]
               // For RSI/ATR: [Main]
               // For MACD: [Hist, Main, Signal] (Note implementation order: Hist, then Main, then Signal)
               
               let label = 'Value';
               const sIdx = seriesRef.current.indexOf(series);
               
               if (type === 'MACD') {
                   if (sIdx === 0) label = 'Hist';
                   if (sIdx === 1) label = 'MACD';
                   if (sIdx === 2) label = 'Signal';
               } else {
                   label = type;
               }

               // value is { time, value, ... } or just number depending on series type?
               // LineSeries: value is number. Candlestick: object.
               // Here we use Line/Hist, generally value is 'value' or the number.
               // LWC 4.x: param.seriesData map values are the data items (objects)
               let val: number | undefined;
               
               if (value?.value !== undefined) val = value.value;
               else if (typeof value === 'number') val = value;

               if (val !== undefined) {
                   newLegend.set(label, val);
               }
           });
       }
       setLegendData(newLegend);
    };

    chartRef.current.subscribeCrosshairMove(updateLegend);
    
    // Initial populate
    if (data.length > 0) {
       const last = data[data.length - 1];
       const initialLegend = new Map<string, number>();
       if (type === 'MACD') {
           if (last.hist !== undefined) initialLegend.set('Hist', last.hist); // Index 0
           initialLegend.set('MACD', last.value); // Index 1
           if (last.signal !== undefined) initialLegend.set('Signal', last.signal); // Index 2
       } else {
           initialLegend.set(type, last.value);
       }
       setLegendData(initialLegend);
    }

    return () => {
        chartRef.current?.unsubscribeCrosshairMove(updateLegend);
    };
  }, [data, type]);

  return (
    <div ref={chartContainerRef} className="w-full relative" style={{ height: height }}>
        <div className="absolute top-1 left-2 z-10 flex gap-4 text-xs font-mono pointer-events-none">
            <span style={{ color: colors.textColor || '#9ca3af' }} className="font-bold">{type}</span>
            {Array.from(legendData.entries()).map(([label, val]) => {
                let color = colors.lineColor;
                if (label === 'Signal') color = colors.signalColor;
                if (label === 'Hist') color = colors.histColor;
                if (type !== 'MACD') color = colors.lineColor; // RSI/ATR

                return (
                    <div key={label} className="flex items-center gap-1">
                        <span style={{ color: color }}>{label}:</span>
                        <span className="text-gray-200">{val.toFixed(2)}</span>
                    </div>
                );
            })}
        </div>
    </div>
  );
};