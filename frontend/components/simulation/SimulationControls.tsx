'use client';

import React from 'react';
import { GridConfig } from '@/lib/api/types';

interface SimulationControlsProps {
  value: GridConfig;
  onChange: (value: GridConfig) => void;
}

export function SimulationControls({ value, onChange }: SimulationControlsProps) {


  return (
    <div className="space-y-6">
       {/* Grid Architecture */}
       <div className="space-y-3">
           <label className="text-xs uppercase tracking-wider text-gray-500 font-bold mb-2 block">
               Grid Structure
           </label>
           
           <div className="grid grid-cols-2 gap-4">
               <div>
                   <label className="block text-xs text-gray-400 mb-1">Step Size (pips)</label>
                   <input 
                      type="number" 
                      value={value.step_size}
                      onChange={(e) => onChange({ ...value, step_size: parseInt(e.target.value) })}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none transition-colors"
                   />
               </div>
               <div>
                   <label className="block text-xs text-gray-400 mb-1">Grid Levels</label>
                   <input 
                      type="number" 
                      value={value.grid_levels}
                      onChange={(e) => onChange({ ...value, grid_levels: parseInt(e.target.value) })}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none transition-colors"
                   />
               </div>
           </div>
       </div>

       <div className="h-px bg-gray-800 my-4"></div>

       {/* Lot Sizing */}
        <div className="space-y-3">
           <label className="text-xs uppercase tracking-wider text-gray-500 font-bold mb-2 block">
               Position Sizing
           </label>
           
           <div className="space-y-4">
               <div>
                   <label className="block text-xs text-gray-400 mb-1">Initial Lot</label>
                   <input 
                      type="number" 
                      step="0.01"
                      value={value.initial_lot}
                      onChange={(e) => onChange({ ...value, initial_lot: parseFloat(e.target.value) })}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none transition-colors"
                   />
               </div>
               
               <div className="flex items-center justify-between">
                   <span className="text-sm text-gray-300">Compound Profits</span>
                    <button 
                        onClick={() => onChange({ ...value, use_compound: !value.use_compound })}
                        className={`w-11 h-6 rounded-full transition-colors flex items-center px-1 ${value.use_compound ? 'bg-emerald-600' : 'bg-gray-700'}`}
                    >
                        <div className={`w-4 h-4 rounded-full bg-white transition-transform ${value.use_compound ? 'translate-x-5' : 'translate-x-0'}`} />
                    </button>
               </div>
           </div>
       </div>

       <div className="h-px bg-gray-800 my-4"></div>

        {/* Protection */}
        <div className="space-y-3">
           <label className="text-xs uppercase tracking-wider text-gray-500 font-bold mb-2 block">
               Risk Control
           </label>
           
           <div>
               <label className="block text-xs text-gray-400 mb-1">Stop Loss (Equity %)</label>
               <input 
                  type="number" 
                  value={value.stop_loss_pct}
                  onChange={(e) => onChange({ ...value, stop_loss_pct: parseFloat(e.target.value) })}
                  className="w-full bg-gray-800 border border-red-900/50 rounded px-3 py-2 text-sm text-white focus:border-red-500 focus:outline-none transition-colors"
               />
               <p className="text-[10px] text-red-500 mt-1">Hard stop if equity drops {value.stop_loss_pct}%</p>
           </div>
       </div>
    </div>
  );
}
