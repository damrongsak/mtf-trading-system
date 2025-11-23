import React from 'react';
import { BotStats } from '../types';
import { TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

interface StatsHeaderProps {
  stats: BotStats;
  currentPrice: number;
  equityHistory: number[]; // Use priceHistory mapped
  assetSymbol?: string;
}

export const StatsHeader: React.FC<StatsHeaderProps> = ({ stats, currentPrice, assetSymbol = 'USD' }) => {
  const isProfitable = stats.totalPnL >= 0;
  const priceDecimals = currentPrice < 10 ? 4 : 2;

  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-4 mb-6">
      
      {/* Large Equity Card */}
      <div className="col-span-12 md:col-span-5 bg-[#111827] border border-gray-800 rounded-sm p-4 relative overflow-hidden">
         <div className="flex justify-between items-start z-10 relative">
            <div>
               <h2 className="text-gray-400 text-[10px] font-bold uppercase tracking-widest mb-1">Total Equity</h2>
               <div className="text-3xl font-bold text-white font-mono tracking-tight">${stats.totalEquity.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
               <div className={`text-xs font-mono mt-1 flex items-center gap-1 ${isProfitable ? 'text-green-400' : 'text-red-400'}`}>
                  {isProfitable ? '+' : ''}{stats.totalPnL.toFixed(2)} ({stats.roi.toFixed(2)}%)
               </div>
            </div>
            <div className="text-right">
                <h2 className="text-gray-400 text-[10px] font-bold uppercase tracking-widest mb-1">Market Price ({assetSymbol})</h2>
                <div className="text-2xl font-bold text-blue-400 font-mono">${currentPrice.toFixed(priceDecimals)}</div>
            </div>
         </div>
         {/* Decorative graph in background */}
         <div className="absolute bottom-0 left-0 w-full h-16 opacity-10 pointer-events-none">
             {/* Abstract wave */}
             <svg viewBox="0 0 100 20" className="w-full h-full" preserveAspectRatio="none">
                 <path d="M0 20 L0 10 Q 25 20 50 10 T 100 15 L 100 20 Z" fill="white" />
             </svg>
         </div>
      </div>

      {/* Stats Grid */}
      <div className="col-span-12 md:col-span-7 grid grid-cols-5 gap-4">
         
         <div className="bg-[#111827] border border-gray-800 rounded-sm p-3 flex flex-col justify-between">
            <span className="text-gray-500 text-[9px] uppercase font-bold tracking-wider">Grid Profit</span>
            <div className="text-lg font-mono font-bold text-green-400">+{stats.gridProfit.toFixed(2)}</div>
         </div>

         <div className="bg-[#111827] border border-gray-800 rounded-sm p-3 flex flex-col justify-between">
            <span className="text-gray-500 text-[9px] uppercase font-bold tracking-wider">Floating P&L</span>
            <div className={`text-lg font-mono font-bold ${stats.floatingPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.floatingPnL >= 0 ? '+' : ''}{stats.floatingPnL.toFixed(2)}
            </div>
         </div>

         <div className="bg-[#111827] border border-gray-800 rounded-sm p-3 flex flex-col justify-between">
             <div className="flex justify-between items-center">
                 <span className="text-gray-500 text-[9px] uppercase font-bold tracking-wider">Total Buys</span>
                 <span className="text-green-500 text-[10px] font-bold">{stats.totalBuys}</span>
             </div>
             <div className="flex justify-between items-center mt-2">
                 <span className="text-gray-500 text-[9px] uppercase font-bold tracking-wider">Total Sells</span>
                 <span className="text-red-500 text-[10px] font-bold">{stats.totalSells}</span>
             </div>
         </div>

         <div className="bg-[#111827] border border-gray-800 rounded-sm p-3 flex flex-col justify-between">
             <div className="flex justify-between">
                 <span className="text-gray-500 text-[9px] uppercase font-bold tracking-wider">Max DD</span>
             </div>
             <div className="text-lg font-mono font-bold text-red-400">-{stats.maxDrawdown.toFixed(2)}%</div>
             <div className="text-[9px] text-gray-600 font-mono">Vol: {stats.portfolioVolatility.toFixed(2)}%</div>
         </div>

         <div className="bg-[#111827] border border-gray-800 rounded-sm p-3 flex flex-col justify-between">
            <span className="text-gray-500 text-[9px] uppercase font-bold tracking-wider">ROI</span>
            <div className={`text-lg font-mono font-bold ${stats.roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.roi >= 0 ? '+' : ''}{stats.roi.toFixed(2)}%
            </div>
         </div>

      </div>
    </div>
  );
};