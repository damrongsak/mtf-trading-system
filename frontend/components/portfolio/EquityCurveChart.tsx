'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, LineSeries } from 'lightweight-charts';
import { AccountHistoryItem } from '@/lib/api/types';

interface EquityCurveChartProps {
    data: Record<string, AccountHistoryItem[]>;
    loading?: boolean;
}

const FUND_COLORS = [
    '#3b82f6', // blue
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // purple
    '#ec4899', // pink
];

export function EquityCurveChart({ data, loading }: EquityCurveChartProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useEffect(() => {
        if (!containerRef.current || loading) return;
        
        // Cleanup previous chart
        if (chartRef.current) {
            chartRef.current.remove();
            chartRef.current = null;
        }

        const chart = createChart(containerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#6b7280',
                fontFamily: "'Inter', sans-serif",
                fontSize: 11,
            },
            grid: {
                vertLines: { color: 'rgba(75, 85, 99, 0.15)' },
                horzLines: { color: 'rgba(75, 85, 99, 0.15)' },
            },
            crosshair: {
                vertLine: { color: '#4b5563', width: 1, style: 2, labelBackgroundColor: '#1f2937' },
                horzLine: { color: '#4b5563', width: 1, style: 2, labelBackgroundColor: '#1f2937' },
            },
            rightPriceScale: {
                borderColor: 'rgba(75, 85, 99, 0.3)',
            },
            timeScale: {
                borderColor: 'rgba(75, 85, 99, 0.3)',
                timeVisible: true,
            },
        });
        chartRef.current = chart;

        const entries = Object.entries(data);
        entries.forEach(([fundName, history], idx) => {
            if (!history || history.length === 0) return;

            const color = FUND_COLORS[idx % FUND_COLORS.length];
            const series = chart.addSeries(LineSeries, {
                color,
                lineWidth: 2,
                title: fundName.substring(0, 15),
                priceLineVisible: false,
                lastValueVisible: true,
            });

            const chartData = history
                .filter(h => h.timestamp && h.equity)
                .map(h => ({
                    time: Math.floor(new Date(h.timestamp).getTime() / 1000) as number,
                    value: Number(h.equity),
                }))
                .sort((a, b) => a.time - b.time);

            if (chartData.length > 0) {
                series.setData(chartData as any);
            }
        });

        chart.timeScale().fitContent();

        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const { width, height } = entry.contentRect;
                chart.applyOptions({ width, height });
            }
        });
        resizeObserver.observe(containerRef.current);

        return () => {
            resizeObserver.disconnect();
            chart.remove();
            chartRef.current = null;
        };
    }, [data, loading]);

    if (loading) {
        return (
            <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6 h-[400px] animate-pulse flex items-center justify-center">
                <span className="text-gray-500">Loading equity curves...</span>
            </div>
        );
    }

    const hasData = Object.values(data).some(arr => arr && arr.length > 0);

    return (
        <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h3 className="text-lg font-semibold text-gray-100">Equity Curves</h3>
                    <p className="text-[10px] text-gray-500 mt-0.5 uppercase tracking-wider">Multi-fund overlay comparison</p>
                </div>
                <div className="flex gap-2">
                    {Object.keys(data).map((name, idx) => (
                        <div key={name} className="flex items-center gap-1.5 text-[10px]">
                            <div className="w-3 h-1 rounded-full" style={{ backgroundColor: FUND_COLORS[idx % FUND_COLORS.length] }} />
                            <span className="text-gray-500">{name.substring(0, 12)}</span>
                        </div>
                    ))}
                </div>
            </div>
            {hasData ? (
                <div ref={containerRef} className="h-[350px] w-full" />
            ) : (
                <div className="h-[350px] flex items-center justify-center text-gray-600 text-sm">
                    No equity history data available
                </div>
            )}
        </div>
    );
}
