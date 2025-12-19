'use client';

import React from 'react';
import { 
  Table, 
  TableHeader, 
  TableBody, 
  TableHead, 
  TableRow, 
  TableCell 
} from '@/components/ui/table'; // Assuming shadcn/ui approach or similar basic table components
import { Badge } from '@/components/ui/badge'; // Assuming shadcn/ui badge
import { Trade } from '@/lib/api/execution';
import { Loader2 } from 'lucide-react';
import { format } from 'date-fns';

interface TradesTableProps {
  trades: Trade[];
  loading: boolean;
  selectedIds?: Set<string>;
  onToggleSelection?: (id: string) => void;
  onToggleAll?: (ids: string[]) => void;
}

export const TradesTable: React.FC<TradesTableProps> = ({ 
    trades, 
    loading,
    selectedIds,
    onToggleSelection,
    onToggleAll
}) => {
  if (loading && trades.length === 0) {
     return (
        <div className="flex justify-center items-center py-12">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
     );
  }

  if (!loading && trades.length === 0) {
    return (
        <div className="text-center py-12 text-gray-500">
            No trades found matching your criteria.
        </div>
    );
  }

  const formatCurrency = (val: number | undefined) => {
    if (val === undefined || val === null) return '-';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  };

  const formatDate = (dateString: string) => {
    try {
        return format(new Date(dateString), 'MMM dd, HH:mm');
    } catch (e) {
        return dateString;
    }
  };

  const allSelected = selectedIds && trades.length > 0 && trades.every(t => selectedIds.has(t.trade_id));
  const showSelection = !!onToggleSelection;

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-950/50 overflow-hidden">
      <Table>
        <TableHeader className="bg-gray-900/50">
          <TableRow className="hover:bg-transparent border-gray-800">
            {showSelection && (
                <TableHead className="w-[50px] text-center">
                    <input 
                        type="checkbox"
                        checked={allSelected}
                        onChange={() => onToggleAll?.(trades.map(t => t.trade_id))}
                        className="rounded border-gray-600 text-indigo-500 focus:ring-indigo-500 bg-gray-800 w-4 h-4 cursor-pointer align-middle"
                    />
                </TableHead>
            )}
            <TableHead className="w-[180px]">Time</TableHead>
            <TableHead>Symbol</TableHead>
            <TableHead className="hidden md:table-cell">Strategy</TableHead>
            <TableHead>Side</TableHead>
            <TableHead className="hidden md:table-cell text-right">Size</TableHead>
            <TableHead className="text-right">Entry</TableHead>
            <TableHead className="text-right">Exit</TableHead>
            <TableHead className="text-right">PnL</TableHead>
            <TableHead className="text-right">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade) => (
            <TableRow 
                key={trade.trade_id} 
                className={`border-gray-800 transition-colors ${selectedIds?.has(trade.trade_id) ? 'bg-indigo-500/10 hover:bg-indigo-500/20' : 'hover:bg-gray-800/30'}`}
            >
              {showSelection && (
                  <TableCell className="text-center">
                    <input 
                        type="checkbox"
                        checked={selectedIds?.has(trade.trade_id)}
                        onChange={() => onToggleSelection?.(trade.trade_id)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded border-gray-600 text-indigo-500 focus:ring-indigo-500 bg-gray-800 w-4 h-4 cursor-pointer align-middle"
                    />
                  </TableCell>
              )}
              <TableCell className="font-mono text-xs text-gray-400">
                {formatDate(trade.signal_timestamp)}
              </TableCell>
              <TableCell className="font-semibold text-gray-200">
                {trade.symbol}
              </TableCell>
              <TableCell className="hidden md:table-cell text-gray-400 text-sm">
                {trade.strategy_name}
              </TableCell>
              <TableCell>
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                    trade.direction === 'LONG' 
                    ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                    {trade.direction}
                </span>
              </TableCell>
              <TableCell className="hidden md:table-cell text-right font-mono text-gray-300">
                {trade.lot_size}
              </TableCell>
              <TableCell className="text-right font-mono text-gray-300">
                {Number(trade.entry_price).toFixed(5)}
              </TableCell>
              <TableCell className="text-right font-mono text-gray-300">
                {trade.exit_price ? Number(trade.exit_price).toFixed(5) : '-'}
              </TableCell>
               <TableCell className={`text-right font-mono font-medium ${
                    (trade.pnl_usd || 0) > 0 ? 'text-green-400' : (trade.pnl_usd || 0) < 0 ? 'text-red-400' : 'text-gray-400'
               }`}>
                {formatCurrency(trade.pnl_usd)}
              </TableCell>
              <TableCell className="text-right">
                <Badge variant={
                    trade.status === 'OPEN' ? 'default' : 
                    trade.status === 'CLOSED' ? 'secondary' : 'destructive'
                } className="uppercase text-[10px]">
                    {trade.status}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};
