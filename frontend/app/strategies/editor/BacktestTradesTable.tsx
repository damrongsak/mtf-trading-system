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

interface BacktestTradesTableProps {
  trades: BacktestTrade[];
  symbol: string;
}

export const BacktestTradesTable: React.FC<BacktestTradesTableProps> = ({ 
    trades, 
    symbol
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

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-950/50 overflow-hidden mt-6">
      <div className="p-4 border-b border-gray-800 bg-gray-900/30">
        <h3 className="font-semibold text-gray-200">Transaction History</h3>
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
