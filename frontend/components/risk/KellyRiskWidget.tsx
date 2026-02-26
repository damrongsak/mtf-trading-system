'use client';

import React from 'react';
import { ShieldAlert, SlidersHorizontal, Scale } from 'lucide-react';

interface KellyRiskProps {
  winRate: number; // e.g., 65.5
  profitFactor: number; // e.g., 1.5
}

export function KellyRiskWidget({ winRate, profitFactor }: KellyRiskProps) {
  // W = Win Probability
  // R = Reward to Risk Ratio
  // Kelly % = W - [(1 - W) / R]
  
  const w = winRate / 100;
  const r = profitFactor || 1; // Prevent div by 0
  
  let rawKelly = w - ((1 - w) / r);
  if (rawKelly < 0) rawKelly = 0;
  
  const kellyPct = (rawKelly * 100).toFixed(1);
  const isOptimal = rawKelly > 0;
  
  // Safe Hard Cap
  const hardCap = 5.0;
  const appliedRisk = Math.min(rawKelly * 100, hardCap);

  return (
    <div className="bg-gray-950/40 backdrop-blur-md border border-gray-800 rounded-xl overflow-hidden shadow-lg">
      <div className="border-b border-gray-800 p-4 bg-gray-900/50 flex justify-between items-center">
        <h3 className="text-gray-200 font-semibold flex items-center gap-2">
          <Scale className="w-5 h-5 text-accent-blue" />
          Dynamic Risk Engine
        </h3>
        <span className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-blue-500/10 text-accent-blue border border-blue-500/20">
          <SlidersHorizontal className="w-3 h-3" />
          Kelly Criterion
        </span>
      </div>

      <div className="p-5 grid grid-cols-2 gap-6">
        <div>
          <div className="flex justify-between text-xs text-gray-500 uppercase tracking-widest mb-2">
            <span>Raw Kelly Size</span>
            <span className="text-gray-400">{kellyPct}%</span>
          </div>
          
          {/* Progress Bar */}
          <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden mb-2 relative">
            <div 
              className={`h-full ${isOptimal ? 'bg-gradient-to-r from-accent-blue to-blue-400' : 'bg-red-500'}`} 
              style={{ width: `${Math.min(Number(kellyPct), 100)}%` }} 
            />
            {/* Hard Cap Marker */}
            <div className="absolute top-0 bottom-0 w-0.5 bg-red-500/80 z-10" style={{ left: '5%' }} />
          </div>
          
          <div className="text-xs text-gray-400 flex items-start gap-1.5 mt-3">
            <ShieldAlert className="w-4 h-4 text-orange-400 flex-shrink-0" />
            <p>
              Math suggested <span className="text-gray-200 font-semibold">{kellyPct}%</span> NAV per trade, but 
              bounded by the <span className="text-orange-400">5.0% Risk Cap</span>.
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800/50 pb-2">
            <span className="text-sm text-gray-400">Win Rate (W)</span>
            <span className="text-gray-200 font-mono">{winRate.toFixed(1)}%</span>
          </div>
          <div className="flex items-center justify-between border-b border-gray-800/50 pb-2">
            <span className="text-sm text-gray-400">Profit Factor (R)</span>
            <span className="text-gray-200 font-mono">{profitFactor.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Applied Risk</span>
            <span className="text-green-400 font-bold font-mono pl-2 border-l border-green-500/30">
              {appliedRisk.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
