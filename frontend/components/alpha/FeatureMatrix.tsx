"use client";

import React, { useEffect, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';
import { Card } from '@/components/ui/card';
import { useLiveFeatures } from '@/lib/hooks/useLiveFeatures';

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
    cell: (info: any) => <span className="font-bold text-slate-200">{info.getValue()}</span>,
  }),
  columnHelper.accessor('rsi_14', {
    header: 'RSI (14)',
    cell: (info: any) => {
      const val = info.getValue();
      if (val === null) return <span className="text-slate-600">-</span>;
      const color = val > 70 ? 'text-red-400' : val < 30 ? 'text-green-400' : 'text-slate-300';
      return <span className={color}>{val.toFixed(2)}</span>;
    },
  }),
  columnHelper.accessor('sma_20', {
    header: 'SMA (20)',
    cell: (info: any) => info.getValue()?.toFixed(4) ?? '-',
  }),
  columnHelper.accessor('atr_14', {
    header: 'ATR (14)',
    cell: (info: any) => info.getValue()?.toFixed(4) ?? '-',
  }),
  columnHelper.accessor('last_updated', {
    header: 'Freshness',
    cell: (info: any) => {
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
  // Use Live Features Hook
  const { features, connected } = useLiveFeatures(['XAU_USD', 'EUR_USD', 'GBP_USD', 'BTC_USD']);
  const [data, setData] = useState<FeatureRow[]>([]);

  useEffect(() => {
    // Transform features object to array for table
    // Explicitly cast f to any for safety given the context or FeatureUpdate if we imported it
    const rows = Object.values(features).map((f: any) => ({
        symbol: f.symbol,
        rsi_14: f.rsi_14 ?? null,
        sma_20: f.sma_20 ?? null,
        atr_14: f.atr_14 ?? null,
        volatility: f.volatility ?? null,
        last_updated: f.last_updated || new Date().toISOString()
    }));
    
    // Sort by symbol
    rows.sort((a, b) => a.symbol.localeCompare(b.symbol));
    
    setData(rows);
  }, [features]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Card className="p-4 bg-slate-900 border-slate-800 w-full h-full overflow-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Market Features (Live)</h3>
        <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-xs text-slate-600">{connected ? 'Stream Active' : 'Connecting...'}</span>
        </div>
      </div>
      
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-slate-500 uppercase bg-slate-950/50">
          {table.getHeaderGroups().map((headerGroup: any) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header: any) => (
                <th key={header.id} className="px-4 py-3">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-slate-800">
          {table.getRowModel().rows.map((row: any) => (
            <tr key={row.id} className="hover:bg-slate-800/50 transition-colors">
              {row.getVisibleCells().map((cell: any) => (
                <td key={cell.id} className="px-4 py-3 font-mono">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {data.length === 0 && (
             <tr>
                 <td colSpan={5} className="text-center py-8 text-slate-600">
                     Waiting for market data...
                 </td>
             </tr>
          )}
        </tbody>
      </table>
    </Card>
  );
};

export default FeatureMatrix;
