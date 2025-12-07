'use client';

import React from 'react';
import { TrendingUp, Activity, Zap } from 'lucide-react';
import { MarketRegime } from '@/lib/api/types';

interface MarketRegimeSelectorProps {
  value: MarketRegime;
  onChange: (value: MarketRegime) => void;
}

export function MarketRegimeSelector({ value, onChange }: MarketRegimeSelectorProps) {


  const trendOptions = [
    { value: 'NO_TREND', label: 'Ranging / Sideways' },
    { value: 'UPTREND', label: 'Strong Uptrend' },
    { value: 'DOWNTREND', label: 'Strong Downtrend' },
  ];

  return (
    <div className="space-y-6">
      {/* Trend Selection */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-400 flex items-center gap-2">
            <TrendingUp size={16} className="text-purple-400" />
            Trend Structure
        </label>
        <div className="grid grid-cols-1 gap-2">
            {trendOptions.map((opt) => (
                <button
                    key={opt.value}
                    onClick={() => onChange({ ...value, trend: opt.value as MarketRegime['trend'] })}
                    className={`
                        px-4 py-3 rounded-lg text-sm text-left border transition-all
                        ${value.trend === opt.value
                            ? 'bg-purple-900/30 border-purple-500 text-white shadow-[0_0_15px_rgba(168,85,247,0.15)]'
                            : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-750 hover:border-gray-600'
                        }
                    `}
                >
                    {opt.label}
                </button>
            ))}
        </div>
      </div>

       {/* Volatility Selection */}
       <div className="space-y-3">
        <label className="text-sm font-medium text-gray-400 flex items-center gap-2">
            <Activity size={16} className="text-blue-400" />
            Volatility Index (σ)
        </label>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
             <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-gray-500">Low (Stable)</span>
                <span className="text-sm font-bold text-white">{value.volatility} / 10</span>
                <span className="text-xs text-gray-500">High (Extreme)</span>
             </div>
             <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={value.volatility}
                onChange={(e) => onChange({ ...value, volatility: parseInt(e.target.value) })}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
             />
        </div>
      </div>

      {/* Noise Model */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-400 flex items-center gap-2">
             <Zap size={16} className="text-yellow-400" />
             Noise Distribution
        </label>
        <div className="grid grid-cols-2 gap-3">
            <button
                onClick={() => onChange({ ...value, noise: 'GAUSSIAN' })}
                className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors
                     ${value.noise === 'GAUSSIAN' ? 'bg-yellow-900/20 border-yellow-600 text-yellow-400' : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'}
                `}
            >
                Gaussian (Normal)
            </button>
            <button
                 onClick={() => onChange({ ...value, noise: 'FAT_TAIL' })}
                 className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors
                     ${value.noise === 'FAT_TAIL' ? 'bg-red-900/20 border-red-600 text-red-400' : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'}
                `}
            >
                Fat-Tail (Black Swan)
            </button>
        </div>
      </div>
    </div>
  );
}
