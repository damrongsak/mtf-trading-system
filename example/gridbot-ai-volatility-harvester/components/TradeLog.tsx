import React, { useState } from 'react';
import { Trade, OrderType, Position, GridLevel } from '../types';

interface TradeLogProps {
    trades: Trade[];
    activePositions: Position[];
    gridLevels: GridLevel[];
}

export const TradeLog: React.FC<TradeLogProps> = ({ trades, activePositions, gridLevels }) => {
  const [activeTab, setActiveTab] = useState<'history' | 'positions' | 'pending'>('history');

  // Filter pending orders
  const pendingOrders = gridLevels.filter(level => level.status === 'PENDING');

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-sm h-[280px] flex flex-col shadow-lg overflow-hidden">
      
      {/* Tabs */}
      <div className="flex border-b border-gray-800">
          <button 
            onClick={() => setActiveTab('history')}
            className={`px-4 py-3 text-[10px] font-bold uppercase tracking-widest transition-colors ${activeTab === 'history' ? 'bg-[#1f2937] text-white border-r border-gray-800' : 'text-gray-500 hover:text-gray-300'}`}
          >
            Trade History ({trades.length})
          </button>
          <button 
            onClick={() => setActiveTab('positions')}
            className={`px-4 py-3 text-[10px] font-bold uppercase tracking-widest transition-colors ${activeTab === 'positions' ? 'bg-[#1f2937] text-white border-x border-gray-800' : 'text-gray-500 hover:text-gray-300'}`}
          >
            Active Positions ({activePositions.length})
          </button>
          <button 
            onClick={() => setActiveTab('pending')}
            className={`px-4 py-3 text-[10px] font-bold uppercase tracking-widest transition-colors ${activeTab === 'pending' ? 'bg-[#1f2937] text-white border-l border-gray-800' : 'text-gray-500 hover:text-gray-300'}`}
          >
            Pending Orders ({pendingOrders.length})
          </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-2">
        {activeTab === 'history' && (
             <div className="space-y-0.5">
                <div className="grid grid-cols-4 text-[9px] text-gray-500 px-2 mb-2 font-bold uppercase tracking-wider">
                    <span>Time</span>
                    <span>Action</span>
                    <span>Price</span>
                    <span className="text-right">Profit/Vol</span>
                </div>
                {trades.length === 0 && <div className="text-gray-600 text-xs text-center mt-10">No history yet</div>}
                {trades.map((trade) => (
                <div key={trade.id} className="grid grid-cols-4 text-xs py-1.5 px-2 hover:bg-[#1f2937] rounded transition-colors items-center border-b border-gray-800/50">
                    <span className="text-gray-500 font-mono text-[10px]">
                    {new Date(trade.timestamp).toLocaleTimeString([], {hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit"})}
                    </span>
                    <span className={`font-bold text-[10px] ${trade.type === OrderType.BUY ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {trade.type === OrderType.BUY ? 'BUY' : 'SELL'}
                    </span>
                    <span className="text-gray-300 font-mono text-[10px]">
                    {trade.price.toFixed(2)}
                    </span>
                    <span className="text-right font-mono text-[10px] text-gray-400">
                    {trade.pnl ? (
                        <span className="text-emerald-500">+{trade.pnl.toFixed(2)}</span>
                    ) : (
                        <span>{trade.amount.toFixed(4)}</span>
                    )}
                    </span>
                </div>
                ))}
             </div>
        )}

        {activeTab === 'positions' && (
             <div className="space-y-0.5">
                <div className="grid grid-cols-3 text-[9px] text-gray-500 px-2 mb-2 font-bold uppercase tracking-wider">
                    <span>Entry Time</span>
                    <span>Entry Price</span>
                    <span className="text-right">Amount</span>
                </div>
                {activePositions.length === 0 && <div className="text-gray-600 text-xs text-center mt-10">No open positions</div>}
                {activePositions.map((pos, idx) => (
                    <div key={idx} className="grid grid-cols-3 text-xs py-1.5 px-2 hover:bg-[#1f2937] rounded transition-colors items-center border-b border-gray-800/50">
                         <span className="text-gray-500 font-mono text-[10px]">
                            {new Date(pos.timestamp).toLocaleTimeString([], {hour12: false, hour: "2-digit", minute: "2-digit"})}
                        </span>
                        <span className="text-gray-300 font-mono text-[10px]">
                            {pos.price.toFixed(2)}
                        </span>
                         <span className="text-gray-400 font-mono text-[10px] text-right">
                            {pos.amount.toFixed(4)}
                        </span>
                    </div>
                ))}
             </div>
        )}

        {activeTab === 'pending' && (
             <div className="space-y-0.5">
                <div className="grid grid-cols-3 text-[9px] text-gray-500 px-2 mb-2 font-bold uppercase tracking-wider">
                    <span>Order Type</span>
                    <span>Target Price</span>
                    <span className="text-right">Status</span>
                </div>
                {pendingOrders.length === 0 && <div className="text-gray-600 text-xs text-center mt-10">No pending orders</div>}
                {/* Sort by price descending to show hierarchy */}
                {pendingOrders.sort((a, b) => b.price - a.price).map((level) => (
                    <div key={level.id} className="grid grid-cols-3 text-xs py-1.5 px-2 hover:bg-[#1f2937] rounded transition-colors items-center border-b border-gray-800/50">
                         <span className={`font-bold text-[10px] ${level.type === OrderType.BUY ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {level.type} LIMIT
                        </span>
                        <span className="text-gray-300 font-mono text-[10px]">
                            {level.price.toFixed(2)}
                        </span>
                         <span className="text-gray-500 font-mono text-[10px] text-right italic">
                            Pending
                        </span>
                    </div>
                ))}
             </div>
        )}
      </div>
    </div>
  );
};