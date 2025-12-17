'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card'; // Check if this exists, usually shadcn/ui
import { Button } from '@/components/ui/button';
import { Loader2, XCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { closeTrade } from '@/lib/api/execution';
import { apiClient } from '@/lib/api/client';
import { APIResponse } from '@/lib/api/types';

interface OpenPosition {
  trade_id: string;
  symbol: string;
  entry_price: number;
  direction: 'LONG' | 'SHORT';
  current_price?: number; // Optional until we have live price feed
  pnl_usd?: number;
  lot_size: number;
  timestamp: string;
}

import { PriceUpdate } from '@/lib/api/types';

interface OpenPositionsCardProps {
  onRefresh?: () => void;
  prices?: Record<string, PriceUpdate>;
  connected?: boolean;
}
// Removed useLivePrices import since it is passed as prop

// DTO matching the raw API response (Decimals as strings)
interface OpenPositionDto {
  trade_id: string;
  symbol: string;
  entry_price: string;
  direction: 'LONG' | 'SHORT';
  current_price?: string;
  pnl_usd?: string;
  lot_size: string;
  timestamp: string;
}

export const OpenPositionsCard: React.FC<OpenPositionsCardProps> = ({ onRefresh, prices = {}, connected = false }) => {
  const [positions, setPositions] = useState<OpenPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [closingId, setClosingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Connected state can be inferred if needed, or passed. For now, we assume if prices update, we are good.
  // Or we can pass 'connected' boolean prop too. Let's keep it simple.


  // ... (fetchOpenPositions logic remains same)
  // Helper to fetch positions directly (since hooks might not be specific enough for just 'open' trades yet)
  const fetchOpenPositions = async () => {
    try {
      setLoading(true);
      // Use DTO for strict type checking on the raw response
      const response = await apiClient.get<APIResponse<OpenPositionDto[]>>('/api/v1/execution/trades', {
          params: { status: 'OPEN' }
      });
      
      const rawData = response.data.data || [];
      const parsedPositions: OpenPosition[] = rawData.map((p) => ({
        trade_id: p.trade_id,
        symbol: p.symbol,
        direction: p.direction,
        timestamp: p.timestamp, // Assuming timestamp string is fine or needs Date parsing? Interface says string.
        entry_price: Number(p.entry_price),
        lot_size: Number(p.lot_size),
        pnl_usd: p.pnl_usd ? Number(p.pnl_usd) : undefined,
        current_price: p.current_price ? Number(p.current_price) : undefined,
      }));

      setPositions(parsedPositions);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch open positions:', err);
      setError('Failed to load positions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOpenPositions();
  }, []);

  const handleClose = async (tradeId: string, currentPrice: number) => {
    setClosingId(tradeId);
    try {
      // Use live price if available, else passed currentPrice (which might be stale from DB)
      // actually we should probably pass the freshest price we have.
      await closeTrade(tradeId, currentPrice);
      // Remove from list locally for optimistic update
      setPositions(prev => prev.filter(p => p.trade_id !== tradeId));
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Failed to close trade:', err);
      alert('Failed to close trade. Please try again.');
    } finally {
      setClosingId(null);
    }
  };
  
  // Calculate PnL dynamically
  const getPnl = (pos: OpenPosition): { pnl: number, price: number } => {
    const live = prices[pos.symbol];
    if (!live) return { pnl: pos.pnl_usd || 0, price: pos.current_price || pos.entry_price }; // Fallback
    
    // Determine exit price (Bid for Long, Ask for Short)
    const exitPrice = pos.direction === 'LONG' ? live.bid : live.ask;
    
    // Assume lot_size 1.0 = 100,000 units (Standard Lot)
    // Adjust logic based on your backend. If backend sends 1000 for 0.01 lot, use that.
    // If backend sends 0.01, multiply by 100,000.
    // Let's assume input is raw volume (e.g. 0.01).
    const units = pos.lot_size * 100000; 
    
    const diff = pos.direction === 'LONG' ? (exitPrice - pos.entry_price) : (pos.entry_price - exitPrice);
    const pnl = diff * units;
    
    return { pnl, price: exitPrice };
  };

  if (loading && positions.length === 0) {
    return (
        <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 h-64 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
    );
  }

  return (
    <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-gray-100">Open Positions</h2>
            {connected && <span className="flex h-2 w-2 rounded-full bg-green-500 animate-pulse"/>}
        </div>
        <Button variant="ghost" size="sm" onClick={fetchOpenPositions} disabled={loading}>
            Refresh
        </Button>
      </div>

      {error && (
        <div className="text-red-400 text-sm mb-4 p-2 bg-red-400/10 rounded">
          {error}
        </div>
      )}

      {positions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No open positions active.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 text-xs text-gray-400 uppercase">
                <th className="text-left py-3 px-4">Symbol</th>
                <th className="text-left py-3 px-4">Side</th>
                <th className="hidden md:table-cell text-right py-3 px-4">Size</th>
                <th className="hidden md:table-cell text-right py-3 px-4">Entry</th>
                <th className="text-right py-3 px-4">Current</th>
                <th className="text-right py-3 px-4">PnL</th>
                <th className="text-right py-3 px-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {positions.map((pos) => {
                const { pnl, price } = getPnl(pos);
                return (
                <tr key={pos.trade_id} className="hover:bg-gray-800/20 transition-colors">
                  <td className="py-3 px-4 font-mono font-medium text-gray-200">{pos.symbol}</td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${
                      pos.direction === 'LONG' 
                        ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                        : 'bg-red-500/10 text-red-400 border border-red-500/20'
                    }`}>
                      {pos.direction === 'LONG' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {pos.direction}
                    </span>
                  </td>
                  <td className="hidden md:table-cell py-3 px-4 text-right font-mono text-gray-400">{pos.lot_size}</td>
                  <td className="hidden md:table-cell py-3 px-4 text-right font-mono text-gray-300">{pos.entry_price.toFixed(5)}</td>
                  <td className="py-3 px-4 text-right font-mono text-gray-300 animate-pulse">{price.toFixed(5)}</td>
                  <td className={`py-3 px-4 text-right font-mono font-medium ${
                    pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Button 
                      size="sm" 
                      variant="default"
                      className="bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/50"
                      disabled={closingId === pos.trade_id}
                      onClick={() => handleClose(pos.trade_id, price)} 
                    >
                      {closingId === pos.trade_id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Close'}
                    </Button>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
