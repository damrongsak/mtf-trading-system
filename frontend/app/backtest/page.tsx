'use client';

import React, { useState, useEffect } from 'react';
import { runBacktest, saveBacktestConfig, getBacktestConfigs, getBacktestHistory } from '@/lib/api/backtest';
import { BacktestRequest, BacktestResponse, OptimizationConfig, ParameterRange, BacktestConfig, BacktestHistorySummary } from '@/lib/api/types';
import { ApiError } from '@/lib/api/errors';
import { Pagination } from '@/components/common/Pagination';

export default function BacktestPage() {
  const [activeTab, setActiveTab] = useState<'run' | 'history'>('run');
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Configuration State
  const [config, setConfig] = useState<BacktestRequest>({
    symbol: 'XAU/USD',
    timeframe: '15m',
    start_date: '2024-01-01T00:00:00.000Z',
    end_date: '2024-01-31T23:59:59.000Z',
    initial_capital: 10000,
    strategy_params: {}
  });

  // Optimization State
  const [optimizationMode, setOptimizationMode] = useState(false);
  const [optConfig, setOptConfig] = useState<OptimizationConfig>({
    method: 'GRID',
    target_metric: 'sharpe_ratio',
    max_iterations: 100,
    early_stopping_rounds: 5,
    param_grid: {}
  });

  // Profile State
  const [savedConfigs, setSavedConfigs] = useState<BacktestConfig[]>([]);
  const [history, setHistory] = useState<BacktestHistorySummary[]>([]);
  const [profileName, setProfileName] = useState('');
  const [showSaveModal, setShowSaveModal] = useState(false);

  // Pagination State
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPerPage, setHistoryPerPage] = useState(10);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyTotalPages, setHistoryTotalPages] = useState(1);

  // Load initial data
  useEffect(() => {
      loadProfiles();
      if (activeTab === 'history') {
          loadHistory(historyPage, historyPerPage);
      }
  }, [activeTab, historyPage, historyPerPage]);

  const loadProfiles = async () => {
      try {
          const profiles = await getBacktestConfigs();
          setSavedConfigs(profiles);
      } catch (_err) { console.error(_err); }
  };

  const loadHistory = async (page: number, perPage: number) => {
      try {
          const response = await getBacktestHistory(page, perPage);
          setHistory(response.data);
          setHistoryTotal(response.meta.total);
          setHistoryTotalPages(response.meta.total_pages);
      } catch (_err) { console.error(_err); }
  };

  const handleSaveProfile = async () => {
      if (!profileName) return;
      try {
          const payload = { ...config };
          if (optimizationMode) payload.optimization = optConfig;
          
          await saveBacktestConfig({
              name: profileName,
              config: payload
          });
          setShowSaveModal(false);
          setProfileName('');
          loadProfiles();
      } catch (_err) {
          setError("Failed to save profile");
      }
  };

  const loadProfile = (profile: BacktestConfig) => {
      setConfig(profile.config);
      if (profile.config.optimization) {
          setOptimizationMode(true);
          setOptConfig(profile.config.optimization);
      } else {
          setOptimizationMode(false);
      }
  };

  // Helper to handle grid parameter changes
  const handleParamGridChange = (paramName: string, type: 'range' | 'list', value: ParameterRange | unknown[]) => {
    const newGrid = { ...optConfig.param_grid };
    if (type === 'range') {
        newGrid[paramName] = value as ParameterRange;
    } else {
        newGrid[paramName] = { values: value as unknown[] };
    }
    setOptConfig({ ...optConfig, param_grid: newGrid });
  };

  const addGridParam = () => {
      const name = prompt("Enter parameter name (e.g., ema_period):");
      if (name) {
          handleParamGridChange(name, 'range', { start: 10, stop: 50, step: 10 });
      }
  };

  const removeGridParam = (name: string) => {
      const newGrid = { ...optConfig.param_grid };
      delete newGrid[name];
      setOptConfig({ ...optConfig, param_grid: newGrid });
  };

  const handleRunBacktest = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const payload = { ...config };
      if (optimizationMode) {
          payload.optimization = optConfig;
      }
      
      const data = await runBacktest(payload);
      setResult(data);
      // Refresh history list if on history tab, or invalidate cache
      if (activeTab === 'history') {
          loadHistory(historyPage, historyPerPage); 
      }
    } catch (_err) {
      console.error("Backtest failed", _err);
      if (_err instanceof ApiError) {
          setError(_err.message);
      } else {
          setError("An unexpected error occurred during backtesting.");
      }
    } finally {
      setIsRunning(false);
    }
  };



  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Strategy Backtest</h1>
          <p className="text-gray-400 mt-1">Validate strategies and optimize parameters</p>
        </div>
        
        {/* Top Controls */}
        <div className="flex gap-3">
             {/* Profile Selector */}
             <select 
                onChange={(e) => {
                    const profile = savedConfigs.find(c => c.id === e.target.value);
                    if (profile) loadProfile(profile);
                }}
                className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5"
            >
                <option value="">Load Profile...</option>
                {savedConfigs.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                ))}
            </select>

            <button 
                onClick={() => setShowSaveModal(true)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg border border-gray-700 text-sm font-medium transition-colors"
            >
                Save Config
            </button>

            <button 
                onClick={handleRunBacktest}
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
                    'Run Backtest'
                )}
            </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
          <button 
            onClick={() => setActiveTab('run')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'run' ? 'border-blue-500 text-blue-500' : 'border-transparent text-gray-400 hover:text-gray-300'}`}
          >
              Run & Configure
          </button>
          <button 
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'history' ? 'border-blue-500 text-blue-500' : 'border-transparent text-gray-400 hover:text-gray-300'}`}
          >
              Run History
          </button>
      </div>

      {activeTab === 'run' ? (
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-16rem)]">
        {/* Left Panel: Configuration */}
        <div className="col-span-12 lg:col-span-4 space-y-4 overflow-y-auto pr-2 custom-scrollbar pb-10">
            {/* Basic Settings */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <span className="w-1 h-5 bg-indigo-500 rounded-full"></span>
                    General Settings
                </h2>
                
                <div className="space-y-4">
                    <div>
                        <label className="block text-xs text-gray-400 mb-1">Symbol</label>
                        <input 
                            type="text" 
                            value={config.symbol}
                            onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none transition-colors"
                        />
                    </div>
                    
                    <div>
                        <label className="block text-xs text-gray-400 mb-1">Timeframe</label>
                        <select 
                            value={config.timeframe}
                            onChange={(e) => setConfig({ ...config, timeframe: e.target.value })}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none transition-colors"
                        >
                            <option value="1m">1 Minute</option>
                            <option value="5m">5 Minutes</option>
                            <option value="15m">15 Minutes</option>
                            <option value="1h">1 Hour</option>
                            <option value="4h">4 Hours</option>
                            <option value="1d">1 Day</option>
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Start Date</label>
                            <div className="space-y-1">
                                <input 
                                    type="datetime-local" 
                                    value={config.start_date.slice(0, 16)} // Format YYYY-MM-DDTHH:mm for input
                                    onChange={(e) => {
                                        const date = new Date(e.target.value);
                                        setConfig({ ...config, start_date: date.toISOString() });
                                    }}
                                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none transition-colors"
                                />
                                <div className="text-[10px] font-mono text-indigo-300 bg-indigo-900/30 px-2 py-1 rounded border border-indigo-500/20 truncate" title="ISO8601 UTC">
                                    {config.start_date.endsWith('Z') ? config.start_date : `${config.start_date}Z`}
                                </div>
                            </div>
                        </div>
                        <div>
                            <label className="block text-xs text-gray-400 mb-1">End Date</label>
                            <div className="space-y-1">
                                <input 
                                    type="datetime-local" 
                                    value={config.end_date.slice(0, 16)} 
                                    onChange={(e) => {
                                        const date = new Date(e.target.value);
                                        setConfig({ ...config, end_date: date.toISOString() });
                                    }}
                                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none transition-colors"
                                />
                                <div className="text-[10px] font-mono text-indigo-300 bg-indigo-900/30 px-2 py-1 rounded border border-indigo-500/20 truncate" title="ISO8601 UTC">
                                    {config.end_date.endsWith('Z') ? config.end_date : `${config.end_date}Z`}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs text-gray-400 mb-1">Initial Capital ($)</label>
                        <input 
                            type="number" 
                            value={config.initial_capital}
                            onChange={(e) => setConfig({ ...config, initial_capital: parseFloat(e.target.value) })}
                            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none transition-colors"
                        />
                    </div>
                </div>
            </div>

            {/* Optimization Toggle */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                        <span className="w-1 h-5 bg-purple-500 rounded-full"></span>
                        Optimization
                    </h2>
                    <button 
                        onClick={() => setOptimizationMode(!optimizationMode)}
                        className={`w-11 h-6 rounded-full transition-colors flex items-center px-1 ${optimizationMode ? 'bg-purple-600' : 'bg-gray-700'}`}
                    >
                        <div className={`w-4 h-4 rounded-full bg-white transition-transform ${optimizationMode ? 'translate-x-5' : 'translate-x-0'}`} />
                    </button>
                </div>

                {optimizationMode && (
                    <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                         <div>
                            <label className="block text-xs text-gray-400 mb-1">Method</label>
                            <select 
                                value={optConfig.method}
                                onChange={(e) => setOptConfig({ ...optConfig, method: e.target.value as OptimizationConfig['method'] })}
                                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none transition-colors"
                            >
                                <option value="GRID">Grid Search</option>
                                <option value="RANDOM">Random Search</option>
                                <option value="BAYESIAN">Bayesian Optimization</option>
                            </select>
                        </div>

                         <div>
                            <label className="block text-xs text-gray-400 mb-1">Target Metric</label>
                            <select 
                                value={optConfig.target_metric}
                                onChange={(e) => setOptConfig({ ...optConfig, target_metric: e.target.value })}
                                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none transition-colors"
                            >
                                <option value="sharpe_ratio">Sharpe Ratio</option>
                                <option value="total_return">Total Return</option>
                                <option value="win_rate">Win Rate</option>
                                <option value="max_drawdown">Max Drawdown (Minimize)</option>
                            </select>
                        </div>

                        {/* Parameter Grid Editor */}
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <label className="block text-xs text-gray-400">Hyperparameters</label>
                                <button 
                                    onClick={addGridParam}
                                    className="text-xs text-purple-400 hover:text-purple-300 border border-purple-500/30 px-2 py-1 rounded"
                                >
                                    + Add Param
                                </button>
                            </div>
                            
                            <div className="space-y-3">
                                {Object.entries(optConfig.param_grid).map(([name, config], idx) => (
                                    <div key={idx} className="bg-gray-800/50 p-3 rounded border border-gray-700">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="text-sm font-medium text-purple-300">{name}</span>
                                            <button onClick={() => removeGridParam(name)} className="text-red-400 hover:text-red-300">×</button>
                                        </div>
                                        
                                        {/* Simple Range Editor (Start/Stop/Step) */}
                                        <div className="grid grid-cols-3 gap-2">
                                            <input 
                                                type="number" 
                                                placeholder="Start"
                                                value={(config as ParameterRange).start}
                                                onChange={(e) => handleParamGridChange(name, 'range', { ...(config as ParameterRange), start: parseFloat(e.target.value) })}
                                                className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                                            />
                                             <input 
                                                type="number" 
                                                placeholder="Stop"
                                                value={(config as ParameterRange).stop}
                                                onChange={(e) => handleParamGridChange(name, 'range', { ...(config as ParameterRange), stop: parseFloat(e.target.value) })}
                                                className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                                            />
                                             <input 
                                                type="number" 
                                                placeholder="Step"
                                                value={(config as ParameterRange).step}
                                                onChange={(e) => handleParamGridChange(name, 'range', { ...(config as ParameterRange), step: parseFloat(e.target.value) })}
                                                className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                                            />
                                        </div>
                                    </div>
                                ))}
                                {Object.keys(optConfig.param_grid).length === 0 && (
                                    <p className="text-xs text-gray-500 italic text-center py-2">No parameters defined</p>
                                )}
                            </div>
                        </div>

                    </div>
                )}
            </div>
        </div>

        {/* Right Panel: Visualization */}
        <div className="col-span-12 lg:col-span-8 space-y-4">
            {error && (
                <div className="bg-red-900/20 border border-red-800 text-red-200 p-4 rounded-xl">
                    Error: {error}
                </div>
            )}

             {/* Metrics */}
             <div className="grid grid-cols-4 gap-4">
                <MetricCard 
                    label="Total P&L" 
                    value={result ? `$${result.metrics.total_return.toFixed(2)}` : '-'} 
                    color={result?.metrics.total_return && result.metrics.total_return > 0 ? 'text-green-400' : (result?.metrics.total_return && result.metrics.total_return < 0 ? 'text-red-400' : 'text-gray-200')}
                />
                <MetricCard 
                    label="Win Rate" 
                    value={result ? `${(result.metrics.win_rate * 100).toFixed(1)}%` : '-'} 
                />
                <MetricCard 
                    label="Max Drawdown" 
                    value={result ? `${(result.metrics.max_drawdown_percent * 100).toFixed(1)}%` : '-'} 
                    color="text-red-400"
                />
                <MetricCard 
                    label={optimizationMode ? "Best Sharpe" : "Sharpe Ratio"} 
                    value={result ? (result.metrics.sharpe_ratio?.toFixed(2) || '-') : '-'} 
                    color="text-purple-400"
                />
            </div>

            {/* Main Content Area */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 h-[calc(100%-8rem)] relative overflow-hidden flex flex-col">
                 {result ? (
                     <div className="flex-1 overflow-y-auto custom-scrollbar">
                        {/* Optimization Results View */}
                        {result.best_params && (
                            <div className="mb-6 bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
                                <h3 className="text-purple-300 font-semibold mb-3 flex items-center gap-2">
                                    <span className="text-lg">🏆</span> Best Configuration Found
                                </h3>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {Object.entries(result.best_params).map(([key, value]) => (
                                        <div key={key} className="bg-gray-950/50 p-2 rounded">
                                            <div className="text-xs text-gray-500 uppercase">{key}</div>
                                            <div className="text-sm font-mono text-white">{String(value)}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Top Optimization Candidates Table */}
                        {result.all_results && result.all_results.length > 0 && (
                            <div className="mb-6">
                                <h3 className="text-gray-400 text-sm font-semibold mb-3">Top Candidates</h3>
                                <div className="bg-gray-950 rounded border border-gray-800 overflow-hidden">
                                    <table className="w-full text-sm text-left">
                                        <thead className="bg-gray-800 text-gray-400">
                                            <tr>
                                                <th className="p-3">Rank</th>
                                                <th className="p-3">Parameters</th>
                                                <th className="p-3 text-right">Metric</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-800">
                                            {result.all_results.slice(0, 5).map((run, idx) => (
                                                <tr key={idx} className="hover:bg-gray-900/50">
                                                    <td className="p-3 text-gray-500">#{idx + 1}</td>
                                                    <td className="p-3 font-mono text-xs text-gray-300">
                                                        {JSON.stringify(run.params).replace(/["{}]/g, '').replace(/:/g, '=')}
                                                    </td>
                                                    <td className="p-3 text-right text-purple-400 font-bold">
                                                        {run.metric}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* Standard Trade List / Equity Curve Placeholder */}
                        {!result.best_params && (
                            <div className="text-center py-20">
                                <p className="text-gray-500">Equity curve visualization pending backend support.</p>
                                <p className="text-sm text-gray-600 mt-2">Trades executed: {result.trades.length}</p>
                            </div>
                        )}
                     </div>
                 ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-center space-y-3">
                        <div className="text-6xl text-gray-800 grayscale opacity-50">📉</div>
                        <div className="text-gray-500 font-mono">Configure & run backtest to view results</div>
                    </div>
                 )}
            </div>
        </div>
      </div>
      ) : (
          /* History View */
          <div className="space-y-4">
              <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                  <table className="w-full text-sm text-left text-gray-400">
                      <thead className="bg-gray-800 text-xs uppercase text-gray-400">
                          <tr>
                              <th className="p-4">Date</th>
                              <th className="p-4">Status</th>
                              <th className="p-4">Symbol</th>
                              <th className="p-4 text-right">Total P&L</th>
                              <th className="p-4 text-right">Sharpe</th>
                              <th className="p-4">Optimization</th>
                          </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                          {history.map((run) => (
                              <tr key={run.id} className="hover:bg-gray-800/50">
                                  <td className="p-4">{new Date(run.created_at).toLocaleString()}</td>
                                  <td className="p-4">
                                      <span className={`px-2 py-1 rounded text-xs font-bold 
                                          ${run.status === 'COMPLETED' ? 'bg-green-900/50 text-green-400' : 
                                            run.status === 'FAILED' ? 'bg-red-900/50 text-red-400' : 'bg-blue-900/50 text-blue-400'}`}>
                                          {run.status}
                                      </span>
                                  </td>
                                  <td className="p-4 font-mono">{run.execution_config.symbol}</td>
                                  <td className={`p-4 text-right font-mono font-bold ${run.metrics?.total_return && run.metrics.total_return > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                      {run.metrics?.total_return ? `$${run.metrics.total_return.toFixed(2)}` : '-'}
                                  </td>
                                   <td className="p-4 text-right font-mono">
                                      {run.metrics?.sharpe_ratio ? run.metrics.sharpe_ratio.toFixed(2) : '-'}
                                  </td>
                                  <td className="p-4">
                                      {run.best_params ? (
                                          <span className="text-purple-400 text-xs">Optimized</span>
                                      ) : (
                                          <span className="text-gray-600 text-xs">-</span>
                                      )}
                                  </td>
                              </tr>
                          ))}
                          {history.length === 0 && (
                              <tr>
                                  <td colSpan={6} className="p-8 text-center text-gray-500">No history found</td>
                              </tr>
                          )}
                      </tbody>
                  </table>
              </div>
              
              <div className="bg-gray-900 border border-gray-800 rounded-xl">
                  <Pagination 
                      currentPage={historyPage}
                      totalPages={historyTotalPages}
                      perPage={historyPerPage}
                      total={historyTotal}
                      onPageChange={setHistoryPage}
                      onPerPageChange={(val) => {
                          setHistoryPerPage(val);
                          setHistoryPage(1); // Reset to first page
                      }}
                  />
              </div>
          </div>
      )}

      {/* Save Modal */}
      {showSaveModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-96 shadow-2xl">
                  <h3 className="text-lg font-bold text-white mb-4">Save Configuration</h3>
                  <div className="space-y-4">
                      <div>
                          <label className="block text-xs text-gray-400 mb-1">Profile Name</label>
                          <input 
                              type="text" 
                              value={profileName}
                              onChange={(e) => setProfileName(e.target.value)}
                              placeholder="e.g., Gold Aggressive Grid"
                              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
                              autoFocus
                          />
                      </div>
                      <div className="flex gap-3 justify-end mt-6">
                          <button 
                              onClick={() => setShowSaveModal(false)}
                              className="px-4 py-2 text-sm text-gray-400 hover:text-white"
                          >
                              Cancel
                          </button>
                          <button 
                              onClick={handleSaveProfile}
                              disabled={!profileName}
                              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded text-sm font-medium"
                          >
                              Save
                          </button>
                      </div>
                  </div>
              </div>
          </div>
      )}
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
