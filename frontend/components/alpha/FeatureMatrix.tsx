"use client";

import React, { useEffect, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';
import { Card } from '@/components/ui/card';

// Types
interface FeatureRow {
  symbol: string;
  rsi_14: number | null;
  sma_20: number | null;
  atr_14: number | null;
  volatility: number | null;
  last_updated: string; // ISO
}

const columnHelper = createColumnHelper<FeatureRow>();

const columns = [
  columnHelper.accessor('symbol', {
    header: 'Symbol',
    cell: info => <span className="font-bold text-slate-200">{info.getValue()}</span>,
  }),
  columnHelper.accessor('rsi_14', {
    header: 'RSI (14)',
    cell: info => {
      const val = info.getValue();
      if (val === null) return <span className="text-slate-600">-</span>;
      const color = val > 70 ? 'text-red-400' : val < 30 ? 'text-green-400' : 'text-slate-300';
      return <span className={color}>{val.toFixed(2)}</span>;
    },
  }),
  columnHelper.accessor('sma_20', {
    header: 'SMA (20)',
    cell: info => info.getValue()?.toFixed(4) ?? '-',
  }),
  columnHelper.accessor('atr_14', {
    header: 'ATR (14)',
    cell: info => info.getValue()?.toFixed(4) ?? '-',
  }),
  columnHelper.accessor('last_updated', {
    header: 'Freshness',
    cell: info => {
        // Calculate lag
        const lag = Date.now() - new Date(info.getValue()).getTime();
        let color = 'bg-green-500';
        if (lag > 5000) color = 'bg-yellow-500';
        if (lag > 15000) color = 'bg-red-500';
        return (
            <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${color}`} />
                <span className="text-xs text-slate-500">{lag}ms</span>
            </div>
        )
    },
  }),
];

const FeatureMatrix = () => {
  const [data, setData] = useState<FeatureRow[]>([]);

  // Mock Data / Real Subscription Placeholder
  useEffect(() => {
    // In Phase 3: Connect this to useWebSocket hook reacting to "market.features.*"
    // For now, static mock or poll
    const mockData: FeatureRow[] = [
        { symbol: 'XAU_USD', rsi_14: 65.4, sma_20: 2024.5, atr_14: 2.5, volatility: 0.001, last_updated: new Date().toISOString() },
        { symbol: 'EUR_USD', rsi_14: 32.1, sma_20: 1.0850, atr_14: 0.0020, volatility: 0.0005, last_updated: new Date().toISOString() },
    ];
    setData(mockData);
    
    // Simulate updates
    const interval = setInterval(() => {
        setData(prev => prev.map(row => ({
            ...row,
            rsi_14: (row.rsi_14 || 50) + (Math.random() - 0.5),
            last_updated: new Date().toISOString()
        })));
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Card className="p-4 bg-slate-900 border-slate-800 w-full h-full overflow-auto">
      <h3 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">Market Features (Live)</h3>
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-slate-500 uppercase bg-slate-950/50">
          {table.getHeaderGroups().map(headerGroup => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map(header => (
                <th key={header.id} className="px-4 py-3">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-slate-800">
          {table.getRowModel().rows.map(row => (
            <tr key={row.id} className="hover:bg-slate-800/50 transition-colors">
              {row.getVisibleCells().map(cell => (
                <td key={cell.id} className="px-4 py-3 font-mono">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
};

export default FeatureMatrix;
