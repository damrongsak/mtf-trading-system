'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, AreaSeries, LineSeries } from 'lightweight-charts';

interface PerformancePoint {
  time: string | number;
  equity: number;
  balance?: number;
}

interface AccountPerformanceChartProps {
  data: PerformancePoint[];
  loading?: boolean;
  title?: string;
}

export const AccountPerformanceChart: React.FC<AccountPerformanceChartProps> = ({ 
  data, 
  loading, 
  title = "Account Performance" 
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const equitySeriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const balanceSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: '#374151',
      },
      rightPriceScale: {
        borderColor: '#374151',
      },
    });

    const equitySeries = chart.addSeries(AreaSeries, {
      lineColor: '#3b82f6',
      topColor: '#3b82f644',
      bottomColor: '#3b82f600',
      lineWidth: 2,
      title: 'Equity',
    });

    const balanceSeries = chart.addSeries(LineSeries, {
      color: '#10b981',
      lineWidth: 1,
      lineStyle: 2, // LargeDash
      title: 'Balance',
    });

    chartRef.current = chart;
    equitySeriesRef.current = equitySeries;
    balanceSeriesRef.current = balanceSeries;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!equitySeriesRef.current || !balanceSeriesRef.current || !data.length) return;

    // Sort data by time ascending
    const sortedData = [...data].sort((a, b) => {
        const timeA = typeof a.time === 'string' ? new Date(a.time).getTime() : a.time;
        const timeB = typeof b.time === 'string' ? new Date(b.time).getTime() : b.time;
        return timeA - timeB;
    });

    const equityData = sortedData.map(item => ({
      time: (typeof item.time === 'string' ? Math.floor(new Date(item.time).getTime() / 1000) : item.time) as any,
      value: item.equity,
    }));

    const balanceData = sortedData
      .filter(item => item.balance !== undefined)
      .map(item => ({
        time: (typeof item.time === 'string' ? Math.floor(new Date(item.time).getTime() / 1000) : item.time) as any,
        value: item.balance as number,
      }));

    equitySeriesRef.current.setData(equityData);
    if (balanceData.length > 0) {
        balanceSeriesRef.current.setData(balanceData);
    }
    
    if (chartRef.current) {
        chartRef.current.timeScale().fitContent();
    }
  }, [data]);

  if (loading) {
    return (
      <div className="h-[350px] w-full bg-gray-950/50 rounded-xl border border-gray-800 animate-pulse flex items-center justify-center">
        <span className="text-gray-500 font-medium">Loading performance data...</span>
      </div>
    );
  }

  if (data.length === 0) {
    return (
        <div className="h-[350px] w-full bg-gray-950/50 rounded-xl border border-gray-800 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-12 h-12 bg-gray-900 rounded-full flex items-center justify-center mb-4">
              <span className="text-gray-600 text-xl font-bold">📈</span>
          </div>
          <h4 className="text-gray-300 font-semibold mb-1">No Performance Data</h4>
          <p className="text-gray-500 text-xs max-w-xs">Performance data will appear here once trade activity is recorded for the selected filter.</p>
        </div>
      );
  }

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-200">{title}</h3>
        <div className="flex gap-4 text-[10px] uppercase tracking-wider">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-blue-500"></div>
            <span className="text-gray-400">Equity</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-emerald-500 border-t border-dashed"></div>
            <span className="text-gray-400">Balance</span>
          </div>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
};
