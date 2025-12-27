'use client';

import React from 'react';
import { 
  Table, 
  TableHeader, 
  TableBody, 
  TableHead, 
  TableRow, 
  TableCell 
} from '@/components/ui/table';
import { BacktestTrade } from '@/lib/api/types';
import { format } from 'date-fns';
import { Download } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface BacktestTradesTableProps {
  trades: BacktestTrade[];
  symbol: string;
  strategyName?: string;
}

export const BacktestTradesTable: React.FC<BacktestTradesTableProps> = ({ 
    trades, 
    symbol,
    strategyName = 'strategy'
}) => {
  if (!trades || trades.length === 0) {
    return (
        <div className="text-center py-12 text-gray-500">
            No trades generated in this backtest.
        </div>
    );
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  };

  const formatPercent = (val: number) => {
    return `${(val * 100).toFixed(2)}%`;
  };

  const formatDate = (dateString: string) => {
    try {
        return format(new Date(dateString), 'MMM dd, HH:mm');
    } catch (_e) {
        return dateString;
    }
  };

  const exportToCSV = () => {
    const headers = [
        "Entry Time", "Exit Time", "Symbol", "Direction", "Size", 
        "Entry Price", "Exit Price", "PnL", "Return %"
    ];

    const rows = trades.map(t => [
        t.entry_time,
        t.exit_time,
        symbol,
        t.direction,
        t.size || 0,
        t.entry_price,
        t.exit_price,
        t.pnl,
        t.pnl_percent
    ]);

    const csvContent = [
        headers.join(","),
        ...rows.map(row => row.map(val => `"${val}"`).join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    
    // sanitized strategy name for filename
    const safeName = strategyName.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    link.setAttribute("href", url);
    link.setAttribute("download", `backtest_trades_${safeName}_${timestamp}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-950/50 overflow-hidden mt-6">
      <div className="p-4 border-b border-gray-800 bg-gray-900/30 flex justify-between items-center">
        <h3 className="font-semibold text-gray-200">Transaction History</h3>
        <Button 
            variant="outline" 
            size="sm" 
            onClick={exportToCSV}
            className="h-8 gap-2 text-slate-400 border-slate-700 hover:text-emerald-400 hover:border-emerald-500/50 hover:bg-emerald-500/10"
        >
            <Download className="h-4 w-4" />
            <span className="text-xs">Export CSV</span>
        </Button>
      </div>
      <div className="max-h-[400px] overflow-auto">
      <Table>
        <TableHeader className="bg-gray-900/50 sticky top-0 font-bold z-10">
          <TableRow className="hover:bg-transparent border-gray-800">
            <TableHead className="w-[150px] whitespace-nowrap">Entry Time</TableHead>
            <TableHead className="w-[150px] whitespace-nowrap">Exit Time</TableHead>
            <TableHead className="whitespace-nowrap">Symbol</TableHead>
            <TableHead className="whitespace-nowrap">Side</TableHead>
            <TableHead className="text-right whitespace-nowrap">Size</TableHead>
            <TableHead className="text-right whitespace-nowrap">Entry Price</TableHead>
            <TableHead className="text-right whitespace-nowrap">Exit Price</TableHead>
            <TableHead className="text-right whitespace-nowrap">Return %</TableHead>
            <TableHead className="text-right whitespace-nowrap">PnL</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade, idx) => (
            <TableRow 
                key={idx} 
                className="border-gray-800 hover:bg-gray-800/30 transition-colors"
            >
              <TableCell className="font-mono text-xs text-gray-400 whitespace-nowrap">
                {formatDate(trade.entry_time)}
              </TableCell>
               <TableCell className="font-mono text-xs text-gray-400 whitespace-nowrap">
                {formatDate(trade.exit_time)}
              </TableCell>
              <TableCell className="font-semibold text-gray-200 whitespace-nowrap">
                {symbol}
              </TableCell>
              <TableCell className="whitespace-nowrap">
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                    trade.direction === 'LONG' 
                    ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                    {trade.direction}
                </span>
              </TableCell>
              <TableCell className="text-right font-mono text-gray-300 whitespace-nowrap">
                {Number(trade.size || 0).toFixed(4)}
              </TableCell>
              <TableCell className="text-right font-mono text-gray-300 whitespace-nowrap">
                {Number(trade.entry_price).toFixed(5)}
              </TableCell>
              <TableCell className="text-right font-mono text-gray-300 whitespace-nowrap">
                {Number(trade.exit_price).toFixed(5)}
              </TableCell>
              <TableCell className={`text-right font-mono font-medium whitespace-nowrap ${
                    trade.pnl_percent > 0 ? 'text-green-400' : trade.pnl_percent < 0 ? 'text-red-400' : 'text-gray-400'
               }`}>
                {formatPercent(trade.pnl_percent)}
              </TableCell>
               <TableCell className={`text-right font-mono font-medium whitespace-nowrap ${
                    trade.pnl > 0 ? 'text-green-400' : trade.pnl < 0 ? 'text-red-400' : 'text-gray-400'
               }`}>
                {formatCurrency(trade.pnl)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      </div>
    </div>
  );
};
