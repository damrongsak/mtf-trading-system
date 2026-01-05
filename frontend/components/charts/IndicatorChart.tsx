'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, LineSeries, HistogramSeries, Time } from 'lightweight-charts';
import { useChartSync } from './ChartContainer';

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

  // Update Data
  useEffect(() => {
    if (!chartRef.current) return;

    // Cleanup old series
    // Cleanup old series
    seriesRef.current.forEach(s => {
        try {
            chartRef.current?.removeSeries(s);
        } catch (e) {
            console.warn("Failed to remove series", e);
        }
    });
    seriesRef.current = [];

    if (type === 'RSI' || type === 'ATR' || type === 'ADX') {
        const lineSeries = chartRef.current.addSeries(LineSeries, {
            color: colors.lineColor || '#2962FF',
            lineWidth: 2,
        });
        
        const lineData = data.map(d => ({ time: d.time, value: d.value }));
        lineSeries.setData(lineData);
        seriesRef.current.push(lineSeries);

        // Register Sync with this main series
        if (registerChart && chartRef.current) {
             unregisterSyncRef.current = registerChart(chartRef.current, lineSeries);
        }
        
        // Add 70/30 lines for RSI
        if (type === 'RSI') {
              lineSeries.createPriceLine({ price: 70, color: 'rgba(255,255,255,0.3)', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
              lineSeries.createPriceLine({ price: 30, color: 'rgba(255,255,255,0.3)', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        }
    } else if (type === 'MACD') {
        // Histogram
        const histSeries = chartRef.current.addSeries(HistogramSeries, {
            color: colors.histColor || '#26a69a',
        });
        const histData = data.filter(d => d.hist !== undefined).map(d => ({ 
            time: d.time, 
            value: d.hist!, 
            color: (d.hist! >= 0 ? (colors.histColor || '#26a69a') : '#ef5350') 
        }));
        histSeries.setData(histData);
        seriesRef.current.push(histSeries);
        
        // Register Sync (Using histogram as reference)
        if (registerChart && chartRef.current) {
             unregisterSyncRef.current = registerChart(chartRef.current, histSeries);
        }

        // MACD Line
        const macdSeries = chartRef.current.addSeries(LineSeries, {
            color: colors.lineColor || '#2962FF',
            lineWidth: 2,
        });
        const macdData = data.map(d => ({ time: d.time, value: d.value }));
        macdSeries.setData(macdData);
        seriesRef.current.push(macdSeries);

        // Signal Line
        const signalSeries = chartRef.current.addSeries(LineSeries, {
            color: colors.signalColor || '#FF6D00',
            lineWidth: 2,
        });
        const signalData = data.filter(d => d.signal !== undefined).map(d => ({ time: d.time, value: d.signal! }));
        signalSeries.setData(signalData);
        seriesRef.current.push(signalSeries);
    }
    
    if (data.length > 0) {
        chartRef.current.timeScale().fitContent();
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, type, colors]);

  return <div ref={chartContainerRef} className="w-full relative" style={{ height: height }} />;
};
