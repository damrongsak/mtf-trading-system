'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, AreaSeries, LineSeries } from 'lightweight-charts';
import { AccountHistoryItem } from '@/lib/api/types';

interface AccountHistoryGraphProps {
  data: AccountHistoryItem[];
  loading?: boolean;
}

export const AccountHistoryGraph: React.FC<AccountHistoryGraphProps> = ({ data, loading }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const balanceSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const equitySeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

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
      },
    });

    const balanceSeries = chart.addSeries(AreaSeries, {
      lineColor: '#3b82f6',
      topColor: '#3b82f644',
      bottomColor: '#3b82f600',
      lineWidth: 2,
      title: 'Balance',
    });

    const equitySeries = chart.addSeries(LineSeries, {
      color: '#10b981',
      lineWidth: 2,
      title: 'Equity',
    });

    chartRef.current = chart;
    balanceSeriesRef.current = balanceSeries;
    equitySeriesRef.current = equitySeries;

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
    if (!balanceSeriesRef.current || !equitySeriesRef.current || !data.length) return;

    // Sort data by timestamp ascending for lightweight-charts
    const sortedData = [...data].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const balanceData = sortedData.map(item => ({
      time: Math.floor(new Date(item.timestamp).getTime() / 1000) as any,
      value: item.balance,
    }));

    const equityData = sortedData.map(item => ({
      time: Math.floor(new Date(item.timestamp).getTime() / 1000) as any,
      value: item.equity,
    }));

    balanceSeriesRef.current.setData(balanceData);
    equitySeriesRef.current.setData(equityData);
    
    if (chartRef.current) {
        chartRef.current.timeScale().fitContent();
    }
  }, [data]);

  if (loading) {
    return (
      <div className="h-[350px] w-full bg-gray-950/50 rounded-xl border border-gray-800 animate-pulse flex items-center justify-center">
        <span className="text-gray-500 font-medium">Loading account history...</span>
      </div>
    );
  }

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-200">Account Fiscal History</h3>
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-blue-500"></div>
            <span className="text-gray-400">Balance</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-emerald-500"></div>
            <span className="text-gray-400">Equity</span>
          </div>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
};
