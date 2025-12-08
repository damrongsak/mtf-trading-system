'use client';

import React, { useState } from 'react';
import { MarketRegimeSelector } from '@/components/simulation/MarketRegimeSelector';
import { SimulationControls } from '@/components/simulation/SimulationControls';
import { runSimulation } from '@/lib/api/simulation';
import { SimulationResult, MarketRegime, GridConfig } from '@/lib/api/types';

export default function SimulationPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);

  const [regime, setRegime] = useState<MarketRegime>({
    trend: 'NO_TREND',
    volatility: 5,
    noise: 'GAUSSIAN'
  });

  const [gridConfig, setGridConfig] = useState<GridConfig>({
    step_size: 10,
    grid_levels: 20,
    initial_lot: 0.01,
    use_compound: false,
    stop_loss_pct: 20
  });

  const handleRunSimulation = async () => {
    setIsRunning(true);
    try {
      const data = await runSimulation({
        regime,
        grid: gridConfig,
        iterations: 1 // Single run for MVP
      });
      setResult(data);
    } catch (error) {
      console.error("Simulation failed", error);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">GRID Simulation Lab</h1>
          <p className="text-gray-400 mt-1">Research, Stress Test, and Optimize GRID Strategies</p>
        </div>
        <div className="flex gap-3">
            <button className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg border border-gray-700 text-sm font-medium transition-colors">
                Load Profile
            </button>
            <button 
                onClick={handleRunSimulation}
                disabled={isRunning}
                className={`px-4 py-2 rounded-lg text-sm font-medium shadow-lg transition-all flex items-center gap-2
                    ${isRunning 
                        ? 'bg-blue-800 text-gray-300 cursor-not-allowed' 
                        : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/20'}
                `}
            >
                {isRunning ? (
                    <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Running...
                    </>
                ) : (
                    'Run Simulation'
                )}
            </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-12rem)]">
        {/* Left Panel: Controls */}
        <div className="col-span-12 lg:col-span-4 space-y-4 overflow-y-auto pr-2 custom-scrollbar pb-10">
            {/* Market Regime */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <MarketRegimeSelector value={regime} onChange={setRegime} />
            </div>

            {/* Grid Strategy */}
             <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <span className="w-1 h-5 bg-emerald-500 rounded-full"></span>
                    Strategy Config
                </h2>
                <SimulationControls value={gridConfig} onChange={setGridConfig} />
            </div>
        </div>

        {/* Right Panel: Visualization */}
        <div className="col-span-12 lg:col-span-8 space-y-4">
             {/* Metrics */}
             <div className="grid grid-cols-4 gap-4">
                <MetricCard 
                    label="Total P&L" 
                    value={result ? `$${result.metrics.total_pnl.toFixed(2)}` : '-'} 
                    color={result?.metrics.total_pnl && result.metrics.total_pnl > 0 ? 'text-green-400' : 'text-gray-200'}
                />
                <MetricCard 
                    label="Win Rate" 
                    value={result ? `${result.metrics.win_rate.toFixed(1)}%` : '-'} 
                />
                <MetricCard 
                    label="Max Drawdown" 
                    value={result ? `${result.metrics.max_drawdown.toFixed(1)}%` : '-'} 
                    color="text-red-400"
                />
                <MetricCard 
                    label="Sharpe Ratio" 
                    value={result ? result.metrics.sharpe_ratio.toFixed(2) : '-'} 
                />
            </div>

            {/* Main Chart */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 h-[calc(100%-8rem)] flex items-center justify-center relative overflow-hidden">
                 {result ? (
                     <div className="w-full h-full flex flex-col">
                        <h3 className="text-gray-400 text-sm mb-4">Equity Curve</h3>
                        <div className="flex-1 flex items-end gap-1 px-4 pb-4 bg-gray-950/30 rounded border border-gray-800/50 relative">
                             {/* Simple CSS Bar Chart for MVP */}
                             {result.equity_curve.map((point, _) => {
                                 // Normalize for display
                                 const min = Math.min(...result.equity_curve.map(p => p.value));
                                 const max = Math.max(...result.equity_curve.map(p => p.value));
                                 const range = max - min;
                                 const height = ((point.value - min) / range) * 80 + 10; // 10% to 90% height
                                 
                                 return (
                                     <div 
                                        key={point.timestamp} 
                                        className="bg-blue-500/50 hover:bg-blue-400 w-full rounded-t transition-all"
                                        style={{ height: `${height}%` }}
                                        title={`$${point.value.toFixed(2)}`}
                                     />
                                 )
                             })}
                        </div>
                     </div>
                 ) : (
                    <div className="text-center space-y-3">
                        <div className="text-6xl text-gray-800 grayscale opacity-50">📊</div>
                        <div className="text-gray-500 font-mono">Run simulation to view results</div>
                    </div>
                 )}
            </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, color = 'text-white' }: { label: string, value: string, color?: string }) {
    return (
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
            <div className={`text-xl font-bold font-mono ${color}`}>{value}</div>
        </div>
    )
}
