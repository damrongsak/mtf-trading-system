
import React, { useMemo } from 'react';
import { MonteCarloStats, BotConfig } from '../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, ScatterChart, Scatter, ZAxis, CartesianGrid } from 'recharts';
import { X, TrendingUp, AlertTriangle, Activity, Target, Skull } from 'lucide-react';

interface MonteCarloModalProps {
  isOpen: boolean;
  onClose: () => void;
  stats: MonteCarloStats | null;
  config: BotConfig;
  isLoading: boolean;
}

export const MonteCarloModal: React.FC<MonteCarloModalProps> = ({ isOpen, onClose, stats, config, isLoading }) => {
  if (!isOpen) return null;

  // Prepare Histogram Data
  const histogramData = useMemo(() => {
    if (!stats) return [];
    const binCount = 20;
    const rois = stats.results.map(r => r.roi);
    const min = Math.min(...rois);
    const max = Math.max(...rois);
    const range = max - min || 1;
    const step = range / binCount;

    const bins = Array.from({ length: binCount }, (_, i) => ({
      rangeStart: min + (i * step),
      rangeEnd: min + ((i + 1) * step),
      label: `${(min + (i * step)).toFixed(1)}%`,
      count: 0,
      fill: (min + (i * step)) >= 0 ? '#10b981' : '#ef4444' // Green for profit, red for loss
    }));

    rois.forEach(roi => {
      const binIndex = Math.min(Math.floor((roi - min) / step), binCount - 1);
      bins[binIndex].count++;
    });

    return bins;
  }, [stats]);

  // Scatter Data (Risk vs Reward)
  const scatterData = useMemo(() => {
      if (!stats) return [];
      return stats.results.map(r => ({
          x: r.maxDrawdown, // Risk
          y: r.roi,         // Reward
          z: 1              // Size
      }));
  }, [stats]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-[#0B0F19] border border-gray-700 w-full max-w-5xl rounded-lg shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-800 bg-[#111827]">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Activity className="text-blue-500" />
                Monte Carlo Simulation
            </h2>
            <div className="text-xs text-gray-400 mt-1 flex gap-4">
                <span>Runs: <span className="text-white font-mono">{isLoading ? '...' : stats?.iterations}</span></span>
                <span>Config: <span className="text-blue-400 font-mono">{config.assetSymbol} Grid ({config.gridCount} lvls)</span></span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
            {isLoading ? (
                <div className="h-64 flex flex-col items-center justify-center space-y-4">
                    <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    <div className="text-blue-400 font-mono text-sm animate-pulse">Running {config.assetSymbol} Scenarios...</div>
                </div>
            ) : stats ? (
                <div className="space-y-8">
                    {/* Top Metrics Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        <div className="bg-[#1f2937] p-4 rounded border border-gray-700">
                            <div className="text-gray-400 text-[10px] uppercase font-bold tracking-widest mb-1">Expected ROI</div>
                            <div className={`text-2xl font-mono font-bold ${stats.avgRoi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {stats.avgRoi > 0 ? '+' : ''}{stats.avgRoi.toFixed(2)}%
                            </div>
                            <div className="text-[10px] text-gray-500 mt-1">Median: {stats.medianRoi.toFixed(2)}%</div>
                        </div>
                        
                        <div className="bg-[#1f2937] p-4 rounded border border-gray-700">
                            <div className="text-gray-400 text-[10px] uppercase font-bold tracking-widest mb-1">Win Rate</div>
                            <div className="text-2xl font-mono font-bold text-blue-400">
                                {stats.winRate.toFixed(1)}%
                            </div>
                            <div className="text-[10px] text-gray-500 mt-1">Profitable Runs</div>
                        </div>

                        <div className="bg-[#1f2937] p-4 rounded border border-gray-700 relative overflow-hidden">
                             <div className="text-gray-400 text-[10px] uppercase font-bold tracking-widest mb-1 flex items-center gap-1">
                                <AlertTriangle size={10} className="text-yellow-500"/> VaR (95%)
                             </div>
                            <div className="text-2xl font-mono font-bold text-yellow-500">
                                {stats.var95.toFixed(2)}%
                            </div>
                            <div className="text-[10px] text-gray-500 mt-1">Worst 5% Outcome</div>
                        </div>
                        
                        <div className="bg-[#1f2937] p-4 rounded border border-gray-700 relative overflow-hidden">
                             <div className="text-gray-400 text-[10px] uppercase font-bold tracking-widest mb-1 flex items-center gap-1">
                                <Skull size={10} className="text-red-500"/> Risk of Ruin
                             </div>
                            <div className={`text-2xl font-mono font-bold ${stats.riskOfRuin > 10 ? 'text-red-500' : 'text-emerald-500'}`}>
                                {stats.riskOfRuin.toFixed(1)}%
                            </div>
                            <div className="text-[10px] text-gray-500 mt-1">Prob. Equity &lt; 50%</div>
                        </div>

                         <div className="bg-[#1f2937] p-4 rounded border border-gray-700">
                            <div className="text-gray-400 text-[10px] uppercase font-bold tracking-widest mb-1">Avg Max DD</div>
                            <div className="text-2xl font-mono font-bold text-red-400">
                                -{stats.avgMaxDrawdown.toFixed(2)}%
                            </div>
                            <div className="text-[10px] text-gray-500 mt-1">Expected Risk</div>
                        </div>
                    </div>

                    {/* Charts Row */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Histogram */}
                        <div className="bg-[#111827] border border-gray-800 rounded p-4">
                            <h3 className="text-sm font-bold text-gray-300 mb-4 flex items-center gap-2">
                                <TrendingUp size={16} /> Return Distribution (P&L)
                            </h3>
                            <div className="h-[250px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={histogramData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} opacity={0.3} />
                                        <XAxis 
                                            dataKey="label" 
                                            tick={{ fontSize: 10, fill: '#9ca3af' }} 
                                            stroke="#4b5563"
                                            interval={2}
                                        />
                                        <Tooltip 
                                            cursor={{fill: '#374151', opacity: 0.2}}
                                            contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff', fontSize: '12px' }}
                                        />
                                        <ReferenceLine x={0} stroke="#6b7280" />
                                        <Bar dataKey="count" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                            <p className="text-center text-[10px] text-gray-500 mt-2">Distribution of ROI outcomes over {stats.iterations} runs</p>
                        </div>

                         {/* Risk vs Reward Scatter */}
                         <div className="bg-[#111827] border border-gray-800 rounded p-4">
                            <h3 className="text-sm font-bold text-gray-300 mb-4 flex items-center gap-2">
                                <Target size={16} /> Risk vs Reward Landscape
                            </h3>
                             <div className="h-[250px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                        <XAxis 
                                            type="number" 
                                            dataKey="x" 
                                            name="Max Drawdown" 
                                            unit="%" 
                                            stroke="#4b5563"
                                            tick={{ fontSize: 10, fill: '#9ca3af' }}
                                            label={{ value: 'Max Drawdown (%)', position: 'insideBottom', offset: -10, fill: '#6b7280', fontSize: 10 }}
                                        />
                                        <YAxis 
                                            type="number" 
                                            dataKey="y" 
                                            name="ROI" 
                                            unit="%" 
                                            stroke="#4b5563"
                                            tick={{ fontSize: 10, fill: '#9ca3af' }}
                                            label={{ value: 'ROI (%)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }}
                                        />
                                        <Tooltip 
                                            cursor={{ strokeDasharray: '3 3' }} 
                                            contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff', fontSize: '12px' }}
                                        />
                                        <Scatter name="Run" data={scatterData} fill="#3b82f6" fillOpacity={0.6} />
                                    </ScatterChart>
                                </ResponsiveContainer>
                            </div>
                             <p className="text-center text-[10px] text-gray-500 mt-2">Each dot represents a single simulation run</p>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
      </div>
    </div>
  );
};
