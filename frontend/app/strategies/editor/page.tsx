"use client";

import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { DeploymentModal } from './DeploymentModal';
import { Play, Save, Terminal, Loader2, Settings2, Trash2, Copy, Check, BookOpen, FileCode, Plus, Search, Rocket, PanelRight, Bot, SlidersHorizontal, Activity } from 'lucide-react';
import InteractiveBacktestChart from '@/components/dashboard/InteractiveBacktestChart';
import { runCustomBacktest } from '@/lib/api/backtest';
import { getPreferences } from '@/lib/api/settings';
import { getSavedStrategies, createSavedStrategy, updateSavedStrategy, deleteSavedStrategy } from '@/lib/api/saved_strategies';
import { OptimizationPanel } from './OptimizationPanel';
import { runOptimization, runMonteCarlo } from '@/lib/api/backtest';
import { MonteCarloPanel } from './MonteCarloPanel';
import { OptimizationResult, MonteCarloRequest, MonteCarloResponse, BacktestTrade, UserPreferences, SavedStrategy, BacktestResponse, OptimizationConfig } from '@/lib/api/types';
import { ConfirmationModal } from '@/components/ui/confirmation-modal';
import { SimulationChart } from './SimulationChart';
import { OptimizationChart } from './OptimizationChart';
import { BacktestTradesTable } from './BacktestTradesTable';
import { StrategyChatPanel } from '@/components/strategies/editor/StrategyChatPanel';

// ... (Keep existing TIMEFRAME_MAP and DEFAULT_CODE) ...
const TIMEFRAME_MAP: Record<string, string> = {
    '1m': 'M1', 'm1': 'M1',
    '5m': 'M5', 'm5': 'M5',
    '15m': 'M15', 'm15': 'M15',
    '30m': 'M30', 'm30': 'M30',
    '1h': 'H1', 'h1': 'H1',
    '4h': 'H4', 'h4': 'H4',
    '1d': 'D', 'd': 'D',
    '1w': 'W', 'w': 'W',
    '1mn': 'M', 'm': 'M', 'M': 'M'
};

const NORMALIZE_TF = (tf: string) => TIMEFRAME_MAP[tf.toLowerCase()] || tf.toUpperCase();

const DEFAULT_CODE = `import vectorbt as vbt
import pandas as pd
import numpy as np

def strategy(data, params=None):
    """
    Vectorized Strategy with Optimization Support
    
    Args:
        data: pd.DataFrame with columns: open, high, low, close, volume (lowercase)
        params: dict (optional) injected by the optimization engine
    
    Returns: 
        entries, exits (boolean pd.Series)
    """
    if params is None:
        params = {}

    # 0. Extract Parameters (with defaults for standard run)
    fast_window = int(params.get('fast_window', 10))
    slow_window = int(params.get('slow_window', 20))
    
    # 1. Prepare Data
    close = data['close']
    
    # 2. Calculate Indicators using dynamic parameters
    fast_ma = vbt.MA.run(close, fast_window, short_name='fast')
    slow_ma = vbt.MA.run(close, slow_window, short_name='slow')
    
    # 3. Generate Signals
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
   
    return entries, exits
`;

interface SaveModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (name: string, description: string, isPublic: boolean) => void;
    initialName?: string;
    initialDescription?: string;
    initialIsPublic?: boolean;
    isLoading?: boolean;
}

function SaveModal({ isOpen, onClose, onConfirm, initialName = '', initialDescription = '', initialIsPublic = false, isLoading = false }: SaveModalProps) {
    const [name, setName] = useState(initialName);
    const [description, setDescription] = useState(initialDescription);



    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-slate-950 border border-slate-800 rounded-xl shadow-xl overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-slate-800">
                    <h3 className="text-lg font-bold text-slate-100">Save Strategy</h3>
                </div>
                <div className="p-6 space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="name">Name</Label>
                        <Input id="name" value={name} onChange={e => setName(e.target.value)} placeholder="My Super Strategy" className="bg-slate-900 border-slate-700" />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="desc">Description</Label>
                        <Input id="desc" value={description} onChange={e => setDescription(e.target.value)} placeholder="Short description..." className="bg-slate-900 border-slate-700" />
                    </div>
                </div>
                <div className="px-6 py-4 bg-slate-900/50 flex justify-end gap-3 border-t border-slate-800">
                    <Button variant="ghost" onClick={onClose} disabled={isLoading}>Cancel</Button>
                    <Button 
                        onClick={() => onConfirm(name, description, initialIsPublic)} 
                        disabled={isLoading || !name.trim()} 
                        className="bg-emerald-600 hover:bg-emerald-700"
                    >
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save
                    </Button>
                </div>
            </div>
        </div>
    );
}

export default function StrategyEditor() {
    interface LogEntry {
        id: string;
        timestamp: Date;
        level: 'INFO' | 'DEBUG' | 'ERROR' | 'SUCCESS';
        message: string;
    }

    const [code, setCode] = useState(DEFAULT_CODE);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isRunning, setIsRunning] = useState(false);
    const [title, setTitle] = useState("My Custom Strategy");
    const [description, setDescription] = useState("");
    
    // Change Detection State
    const [lastSavedCode, setLastSavedCode] = useState(DEFAULT_CODE);
    const [lastSavedTitle, setLastSavedTitle] = useState("My Custom Strategy");
    
    // UI State
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    const [sidebarTab, setSidebarTab] = useState<'config' | 'library' | 'optimize' | 'simulation' | 'chat'>('config');
    const [isCopied, setIsCopied] = useState(false);
    
    // Visualization State
    const [activeTab, setActiveTab] = useState<'editor' | 'backtest' | 'optimization' | 'simulation'>('editor');
    const [plotJson, setPlotJson] = useState<string | null>(null);
    const [lastOptResult, setLastOptResult] = useState<OptimizationResult[] | null>(null);
    const [lastSimResult, setLastSimResult] = useState<MonteCarloResponse | null>(null);

    // Configuration State
    const [preferences, setPreferences] = useState<UserPreferences | null>(null);
    const [symbol, setSymbol] = useState("XAU_USD");
    const [timeframe, setTimeframe] = useState("H1");
    const [startDate, setStartDate] = useState(new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
    const [initialCapital, setInitialCapital] = useState(10000);
    const [fees, setFees] = useState(0.0001);
    const [slippage, setSlippage] = useState(0.0001);
    const [orderSize, setOrderSize] = useState(1.0);
    const [sizeType, setSizeType] = useState<'amount' | 'value' | 'percent'>('amount');

    // Strategy Library State
    const [savedStrategies, setSavedStrategies] = useState<SavedStrategy[]>([]);
    const [currentStrategyId, setCurrentStrategyId] = useState<string | null>(null);
    const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // Optimization State
    const [isOptimizing, setIsOptimizing] = useState(false);
    const [isSimulating, setIsSimulating] = useState(false);
    const [isDeployModalOpen, setIsDeployModalOpen] = useState(false);
    const [lastBacktestResult, setLastBacktestResult] = useState<BacktestResponse | null>(null);
    const [lastBacktestTrades, setLastBacktestTrades] = useState<BacktestTrade[] | null>(null);

    // Confirmation Modal States
    const [showLoadConfirm, setShowLoadConfirm] = useState(false);
    const [showNewStrategyConfirm, setShowNewStrategyConfirm] = useState(false);
    const [pendingLoadStrategy, setPendingLoadStrategy] = useState<SavedStrategy | null>(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [strategyToDelete, setStrategyToDelete] = useState<{id: string, name: string} | null>(null);

    useEffect(() => {
        const fetchPreferences = async () => {
            try {
                const prefs = await getPreferences();
                setPreferences(prefs);
                if (prefs.default_symbol) {
                     setSymbol(prefs.default_symbol.replace('/', '_'));
                }
                if (prefs.preferred_timeframes?.length > 0) {
                    setTimeframe(NORMALIZE_TF(prefs.preferred_timeframes[0]));
                }
            } catch (error) {
                console.error("Failed to fetch preferences:", error);
            }
        };
        fetchPreferences();
        fetchStrategies();
    }, []);

    const fetchStrategies = async () => {
        try {
            const strats = await getSavedStrategies();
            setSavedStrategies(strats);
        } catch (error) {
            console.error("Failed to fetch strategies:", error);
            addLog('ERROR', "Failed to load strategy library.");
        }
    };

    const addLog = (level: LogEntry['level'], message: string) => {
        setLogs(prev => [{
            id: Math.random().toString(36).substring(7),
            timestamp: new Date(),
            level,
            message
        }, ...prev]);
    };

    const handleRun = async () => {
        setIsRunning(true);
        addLog('INFO', "Starting backtest simulation...");
        addLog('DEBUG', `Parameters: ${symbol} | ${timeframe} | ${startDate} to ${endDate}`);
        
        try {
            if (!startDate || !endDate) throw new Error("Please select both start and end dates.");

            const payload = {
                code: code,
                symbol: symbol,
                timeframe: timeframe,
                start_date: new Date(startDate).toISOString(), 
                end_date: new Date(endDate).toISOString(),
                initial_capital: initialCapital,
                fees: fees,
                slippage: slippage,
                size: orderSize,
                size_type: sizeType
            };

            addLog('INFO', "Sending code to server...");
            const res = await runCustomBacktest({
                 ...payload,
                 strategy_id: currentStrategyId || undefined
            });
            
            addLog('SUCCESS', "Backtest Complete!");
            addLog('INFO', `----------------------------------------`);
            addLog('INFO', `Total Return: $${res.metrics.total_return.toFixed(2)} (${res.metrics.total_return_percent.toFixed(2)}%)`);
            addLog('INFO', `Win Rate:     ${res.metrics.win_rate.toFixed(1)}%`);
            addLog('INFO', `Max Drawdown: $${res.metrics.max_drawdown.toFixed(2)} (${res.metrics.max_drawdown_percent.toFixed(2)}%)`);
            addLog('INFO', `Total Trades: ${res.metrics.total_trades}`);
            addLog('INFO', `----------------------------------------`);
            
            if (res.plot_json) {
                setPlotJson(res.plot_json);
                setLastBacktestResult(res);
                setLastBacktestTrades(res.trades || []);
                setActiveTab('backtest');
                addLog('SUCCESS', "Interactive Chart Generated.");
            }
            
        } catch (error) {
            addLog('ERROR', `Execution failed: ${(error as Error).message || String(error)}`);
        } finally {
            setIsRunning(false);
        }
    };

    const handleSaveClick = () => {
        setIsSaveModalOpen(true);
    };

    const handleConfirmSave = async (name: string, desc: string, isPublic: boolean) => {
        setIsSaving(true);
        try {
            const payload = {
                name,
                description: desc,
                code,
                parameters: {
                    symbol, timeframe, initialCapital, fees, slippage, orderSize, sizeType
                },
                last_results: plotJson ? {
                    metrics: null, 
                    plot_json: plotJson,
                    trades: lastBacktestTrades || undefined
                } : null,
                is_public: isPublic
            };

            if (currentStrategyId) {
                const updated = await updateSavedStrategy(currentStrategyId, payload);
                addLog('SUCCESS', `Strategy "${updated.name}" updated successfully.`);
                // update local list
                setSavedStrategies(prev => prev.map(s => s.id === updated.id ? updated : s));
                setTitle(updated.name);
                setDescription(updated.description || "");
            } else {
                const created = await createSavedStrategy(payload);
                addLog('SUCCESS', `Strategy "${created.name}" created successfully.`);
                setSavedStrategies(prev => [created, ...prev]);
                setCurrentStrategyId(created.id);
                setTitle(created.name);
                setDescription(created.description || "");
            }
            // Update last saved state
            setLastSavedCode(code);
            setLastSavedTitle(name);
            setIsSaveModalOpen(false);
        } catch (err) {
            addLog('ERROR', `Failed to save strategy: ${(err as Error).message}`);
        } finally {
            setIsSaving(false);
        }
    };

    const performLoadStrategy = (strategy: SavedStrategy) => {
        setCode(strategy.code);
        setTitle(strategy.name);
        setDescription(strategy.description || "");
        setCurrentStrategyId(strategy.id);
        
        // Load params if available
        if (strategy.parameters) {
             if (strategy.parameters.symbol) setSymbol(String(strategy.parameters.symbol));
             if (strategy.parameters.timeframe) setTimeframe(String(strategy.parameters.timeframe));
             if (strategy.parameters.initialCapital) setInitialCapital(Number(strategy.parameters.initialCapital));
             if (strategy.parameters.orderSize) setOrderSize(Number(strategy.parameters.orderSize));
             if (strategy.parameters.sizeType) setSizeType(String(strategy.parameters.sizeType) as 'amount' | 'value' | 'percent');
        }
        addLog('INFO', `Loaded strategy: ${strategy.name}`);
        
        // Restore last results if available
        if (strategy.last_results) {
             setPlotJson(strategy.last_results.plot_json || null);
             setLastBacktestTrades(strategy.last_results.trades || null);
        } else {
            setPlotJson(null);
            setLastBacktestTrades(null);
        }

        if (strategy.last_optimization_result) {
            setLastOptResult(strategy.last_optimization_result);
        } else {
            setLastOptResult(null);
        }

        if (strategy.last_simulation_result) {
            setLastSimResult(strategy.last_simulation_result);
        } else {
            setLastSimResult(null);
        }
        
        // Decide active tab based on what's available
        if (strategy.last_simulation_result) setActiveTab('simulation');
        else if (strategy.last_optimization_result) setActiveTab('optimization');
        else if (strategy.last_results?.plot_json) setActiveTab('backtest');
        else setActiveTab('editor');

        // Update last saved state
        setLastSavedCode(strategy.code);
        setLastSavedTitle(strategy.name);
        
        setShowLoadConfirm(false);
        setPendingLoadStrategy(null);
    };

    const handleLoadStrategy = (strategy: SavedStrategy) => {
        // Check if current editor content is different from what was last saved/loaded
        const isDirty = code !== lastSavedCode || title !== lastSavedTitle;
        
        // Only ignore if it is exactly the same strategy ID (reloading same strat) - purely optional optimization
        // actually, if I modified it, I want to be warned even if reloading same ID.
        
        if (isDirty) {
             setPendingLoadStrategy(strategy);
             setShowLoadConfirm(true);
             return;
        }
        performLoadStrategy(strategy);
    };

    const handleDeleteClick = (id: string, name: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setStrategyToDelete({ id, name });
        setShowDeleteConfirm(true);
    };

    const confirmDeleteStrategy = async () => {
        if (!strategyToDelete) return;
        const { id, name } = strategyToDelete;
        
        try {
            await deleteSavedStrategy(id);
            setSavedStrategies(prev => prev.filter(s => s.id !== id));
            if (currentStrategyId === id) {
                setCurrentStrategyId(null);
                setTitle("My Custom Strategy");
                performNewStrategy(); // Reset editor
            }
            addLog('SUCCESS', `Strategy "${name}" deleted.`);
        } catch (err) {
            addLog('ERROR', `Failed to delete: ${(err as Error).message}`);
        } finally {
            setShowDeleteConfirm(false);
            setStrategyToDelete(null);
        }
    };

    const handleRunOptimization = async (paramGrid: Record<string, unknown>) => {
        setIsOptimizing(true);
        addLog('INFO', "Starting optimization...");
        
        try {
             if (!startDate || !endDate) throw new Error("Start/End dates required");

             const payload = {
                code: code,
                symbol: symbol,
                timeframe: timeframe,
                start_date: new Date(startDate).toISOString(), 
                end_date: new Date(endDate).toISOString(),
                initial_capital: initialCapital,
                fees: fees,
                slippage: slippage,
                optimization: {
                    method: 'GRID' as const,
                    target_metric: 'sharpe_ratio', // default
                    param_grid: paramGrid as OptimizationConfig['param_grid']
                }
            };
            
            
            const results = await runOptimization({
                ...payload,
                strategy_id: currentStrategyId || undefined
            });
            setLastOptResult(results);
            setActiveTab('optimization');
            addLog('SUCCESS', `Optimization complete. Found ${results.length} results.`);
            return results;
        } catch (error) {
            addLog('ERROR', `Optimization failed: ${(error as Error).message}`);
            throw error;
        } finally {
            setIsOptimizing(false);
        }
    };

    const handleRunSimulation = async (trades: BacktestTrade[], iterations: number) => {
        setIsSimulating(true);
        try {
             const res = await runMonteCarlo({ 
                 trades, 
                 iterations,
                 strategy_id: currentStrategyId || undefined
             });
             setLastSimResult(res);
             setActiveTab('simulation');
             return res;
        } finally {
             setIsSimulating(false);
        }
    };

    const performNewStrategy = () => {
        setCode(DEFAULT_CODE);
        setTitle("New Strategy");
        setDescription("");
        setCurrentStrategyId(null);
        setCurrentStrategyId(null);
        setPlotJson(null);
        setLastOptResult(null);
        setLastSimResult(null);
        setLastBacktestTrades(null);
        setActiveTab('editor');
        
        setLastSavedCode(DEFAULT_CODE);
        setLastSavedTitle("New Strategy");
        
        setShowNewStrategyConfirm(false);
        addLog('INFO', "Created new strategy draft.");
    };

    const handleNewStrategy = () => {
        const isIgnore = code === DEFAULT_CODE; // If untouched default, just reset anyway (no-op visual)
        const isDirty = (code !== lastSavedCode || title !== lastSavedTitle) && !isIgnore;

        if (isDirty) {
            setShowNewStrategyConfirm(true);
            return;
        }
        performNewStrategy();
    };

    const handleClearLogs = () => setLogs([]);

    const handleCopyLogs = () => {
        const text = logs.map(l => `[${l.timestamp.toISOString()}] [${l.level}] ${l.message}`).join('\n');
        navigator.clipboard.writeText(text);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    return (
        <div className="container mx-auto p-4 space-y-4 text-slate-100 min-h-[calc(100vh-4rem)] flex flex-col">
            {/* Deployment Modal */}
            <DeploymentModal
                open={isDeployModalOpen}
                onOpenChange={setIsDeployModalOpen}
                strategyId={currentStrategyId}
                initialConfig={{
                    symbol: symbol,
                    timeframe: timeframe,
                    capital: initialCapital,
                    strategy_params: {} 
                }}
            />

            {/* Save Strategy Modal */}
            <SaveModal 
                key={isSaveModalOpen ? 'open' : 'closed'}
                isOpen={isSaveModalOpen} 
                onClose={() => setIsSaveModalOpen(false)} 
                onConfirm={handleConfirmSave} 
                initialName={title}
                initialDescription={description}
                initialIsPublic={false}
                isLoading={isSaving}
            />
            
            <ConfirmationModal
                isOpen={showLoadConfirm}
                onClose={() => setShowLoadConfirm(false)}
                onConfirm={() => pendingLoadStrategy && performLoadStrategy(pendingLoadStrategy)}
                title="Unsaved Changes"
                message="You have unsaved changes in your current strategy. Loading a new strategy will overwrite them. Are you sure you want to continue?"
                confirmText="Load Strategy"
                variant="danger"
            />
            
            <ConfirmationModal
                isOpen={showNewStrategyConfirm}
                onClose={() => setShowNewStrategyConfirm(false)}
                onConfirm={performNewStrategy}
                title="Unsaved Changes"
                message="You have unsaved changes in your current strategy. Starting a new strategy will overwrite them. Are you sure you want to continue?"
                confirmText="Start New Strategy"
                variant="danger"
            />

            <ConfirmationModal
                isOpen={showDeleteConfirm}
                onClose={() => setShowDeleteConfirm(false)}
                onConfirm={confirmDeleteStrategy}
                title="Delete Strategy"
                message={`Are you sure you want to delete "${strategyToDelete?.name}"? This action cannot be undone and will delete all associated deployments.`}
                confirmText="Delete Strategy"
                variant="danger"
            />


            {/* Header */}
            <div className="flex justify-between items-center bg-slate-950/50 p-4 rounded-xl border border-slate-800 backdrop-blur-sm">
                <div className="flex-1">
                     <div className="flex items-center gap-2">
                        <input 
                            type="text" 
                            value={title} 
                            onChange={(e) => setTitle(e.target.value)}
                            className="bg-transparent text-2xl font-bold text-emerald-400 focus:outline-none placeholder-emerald-400/50 min-w-[200px]"
                            placeholder="Strategy Name"
                        />
                        {currentStrategyId && <span className="text-xs text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">Saved</span>}
                     </div>
                    <p className="text-slate-400 text-sm truncate max-w-xl">{description || "Write, test, and deploy custom Python algorithms."}</p>
                </div>
                <div className="flex gap-2">
                     <Button 
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)} 
                        variant="ghost" 
                        size="sm"
                        className={`h-9 w-9 p-0 rounded-lg border transition-colors ${isSidebarOpen ? 'bg-slate-800 border-slate-700 text-emerald-400' : 'bg-transparent border-slate-800 text-slate-500 hover:text-emerald-400'}`}
                        title="Toggle Sidebar"
                     >
                        <PanelRight className="h-5 w-5" />
                     </Button>

                    <div className="h-8 w-[1px] bg-slate-700 mx-1" />
                    
                    <Button onClick={handleNewStrategy} variant="ghost" size="icon" title="New Strategy">
                        <Plus className="h-5 w-5" />
                    </Button>
                    
                    <Button onClick={handleSaveClick} variant="ghost" size="icon" title="Save Strategy">
                        <Save className="h-5 w-5" />
                    </Button>

                    <div className="h-8 w-[1px] bg-slate-700 mx-1" />

                    <Button onClick={handleRun} disabled={isRunning} variant="outline" className="gap-2 border-emerald-500/30 hover:bg-emerald-500/10 hover:text-emerald-400 min-w-[100px]">
                        {isRunning ? <Loader2 className="animate-spin h-4 w-4" /> : <Play className="h-4 w-4" />}
                        Run
                    </Button>
                    
                    <Button 
                        onClick={() => {
                            setSidebarTab('chat');
                            setIsSidebarOpen(true);
                        }}
                        variant="outline"
                        className={`gap-2 border-indigo-500/30 hover:bg-indigo-500/10 hover:text-indigo-400 ${sidebarTab === 'chat' && isSidebarOpen ? 'bg-indigo-500/20 text-indigo-300' : ''}`}
                    >
                         <Bot className="h-4 w-4" />
                         AI Assist
                    </Button>

                    <Button 
                        onClick={() => setIsDeployModalOpen(true)} 
                        disabled={!currentStrategyId}
                        variant="ghost"
                        className="gap-2 text-purple-400 hover:text-purple-300 hover:bg-purple-400/10"
                        title={!currentStrategyId ? "Save strategy first to deploy" : "Deploy Live"}
                    >
                        <Rocket className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex gap-4 min-h-0">
                {/* Editor & Output Column */}
                <div className="flex-1 flex flex-col gap-4 min-w-0">
                    <Card className="flex-1 bg-slate-900/50 border-slate-800 flex flex-col backdrop-blur-sm min-h-[600px]">
                        <CardHeader className="py-2 px-4 border-b border-slate-800 bg-slate-950/30 flex flex-row items-center gap-4">
                            <button 
                                onClick={() => setActiveTab('editor')}
                                className={`text-xs font-mono px-2 py-1 rounded transition-colors ${activeTab === 'editor' ? 'text-emerald-400 bg-emerald-400/10' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                main.py
                            </button>
                            <button 
                                onClick={() => setActiveTab('backtest')}
                                className={`text-xs font-mono px-2 py-1 rounded transition-colors ${activeTab === 'backtest' ? 'text-emerald-400 bg-emerald-400/10' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                Backtest {plotJson && '•'}
                            </button>
                            <button 
                                onClick={() => setActiveTab('optimization')}
                                className={`text-xs font-mono px-2 py-1 rounded transition-colors ${activeTab === 'optimization' ? 'text-emerald-400 bg-emerald-400/10' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                Optimization {lastOptResult && '•'}
                            </button>
                            <button 
                                onClick={() => setActiveTab('simulation')}
                                className={`text-xs font-mono px-2 py-1 rounded transition-colors ${activeTab === 'simulation' ? 'text-emerald-400 bg-emerald-400/10' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                Simulation {lastSimResult && '•'}
                            </button>
                        </CardHeader>
                        <CardContent className="p-0 flex-1 relative min-h-0 overflow-hidden">
                            {activeTab === 'editor' && (
                                <Editor
                                    height="950px"
                                    defaultLanguage="python"
                                    theme="vs-dark"
                                    value={code}
                                    onChange={(value) => setCode(value || "")}
                                    options={{
                                        minimap: { enabled: false },
                                        fontSize: 14,
                                        scrollBeyondLastLine: false,
                                        padding: { top: 16 },
                                        fontFamily: 'JetBrains Mono, Menlo, Monaco, monospace',
                                    }}
                                />
                            )}
                            {activeTab === 'backtest' && (
                                <div className="h-full w-full bg-slate-950 p-0">
                                    {plotJson || lastBacktestTrades ? (
                                        <div className="flex flex-col h-full overflow-hidden">
                                            <div className="flex-1 min-h-[500px]">
                                                {plotJson ? (
                                                    <InteractiveBacktestChart plotJson={plotJson} />
                                                ) : (
                                                    <div className="h-full flex items-center justify-center text-slate-500/50">
                                                        <p>No chart data available</p>
                                                    </div>
                                                )}
                                            </div>
                                            {lastBacktestTrades && (
                                                <div className="p-4 bg-slate-950">
                                                    <BacktestTradesTable 
                                                        trades={lastBacktestTrades} 
                                                        symbol={symbol} 
                                                        strategyName={title}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="h-full flex items-center justify-center text-slate-500 flex-col gap-2">
                                            <span className="text-4xl">📊</span>
                                            <p>Run a backtest to generate an interactive chart.</p>
                                        </div>
                                    )}
                                </div>
                            )}
                            {activeTab === 'optimization' && (
                                <div className="h-full w-full bg-slate-950 p-0">
                                    <OptimizationChart results={lastOptResult || undefined} />
                                </div>
                            )}
                            {activeTab === 'simulation' && (
                                <div className="h-full w-full bg-slate-950 p-0">
                                    <SimulationChart equityCurves={lastSimResult?.equity_curves} />
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card className="h-80 bg-slate-950 border-slate-800 flex flex-col shrink-0">
                        <CardHeader className="py-2 px-4 border-b border-slate-800 bg-slate-900/50 flex flex-row items-center justify-between">
                            <CardTitle className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-400 font-medium">
                                <Terminal className="h-3.5 w-3.5" />
                                Console Output
                            </CardTitle>
                            <div className="flex gap-1">
                                <Button variant="ghost" size="icon" className="h-6 w-6 text-slate-500 hover:text-emerald-400 hover:bg-emerald-400/10" onClick={handleCopyLogs} title="Copy Logs">
                                    {isCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                                </Button>
                                <Button variant="ghost" size="icon" className="h-6 w-6 text-slate-500 hover:text-red-400 hover:bg-red-400/10" onClick={handleClearLogs} title="Clear Logs">
                                    <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                            </div>
                        </CardHeader>

                        <CardContent className="p-4 flex-1 font-mono text-xs overflow-auto space-y-2">
                            {isRunning && <div className="text-emerald-500/50 animate-pulse mb-2">Running...</div>}
                            {logs.length === 0 && !isRunning && <span className="text-slate-600 italic">Ready to execute...</span>}
                            {logs.map((log) => (
                                <div key={log.id} className="flex gap-2 items-start animate-in fade-in slide-in-from-top-1 duration-300">
                                    <span className="text-slate-600 shrink-0 select-none">
                                        {log.timestamp.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                    </span>
                                    <span className={`shrink-0 font-bold px-1 rounded select-none ${log.level === 'INFO' ? 'text-blue-400 bg-blue-400/10' : log.level === 'DEBUG' ? 'text-slate-400 bg-slate-400/10' : log.level === 'SUCCESS' ? 'text-emerald-400 bg-emerald-400/10' : 'text-red-400 bg-red-400/10'}`}>
                                        {log.level}
                                    </span>
                                    <span className={`break-all whitespace-pre-wrap ${log.level === 'ERROR' ? 'text-red-300' : 'text-slate-300'}`}>
                                        {log.message}
                                    </span>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                </div>

                {/* Right Sidebar (Config & Library) */}
                <div 
                    className={`
                        bg-slate-950/80 backdrop-blur-xl border border-slate-800 rounded-xl transition-all duration-300 ease-in-out overflow-hidden flex flex-col max-h-[800px]
                        ${isSidebarOpen ? 'w-80 opacity-100 translate-x-0' : 'w-0 opacity-0 translate-x-10 p-0 border-0'}
                    `}
                >
                    <div className="p-0 border-b border-slate-800 flex bg-slate-950/50">
                        {[
                            { id: 'config', icon: Settings2, label: 'Config' },
                            { id: 'library', icon: BookOpen, label: 'Library' },
                            { id: 'optimize', icon: SlidersHorizontal, label: 'Optimize' },
                            { id: 'simulation', icon: Activity, label: 'Simulate' },
                            { id: 'chat', icon: Bot, label: 'Assistant' },
                        ].map((tab) => (
                             <button 
                                key={tab.id}
                                className={`flex-1 py-4 flex flex-col items-center gap-1.5 transition-all relative group
                                    ${sidebarTab === tab.id 
                                        ? 'text-emerald-400 bg-slate-900/50' 
                                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'
                                    }
                                `}
                                onClick={() => setSidebarTab(tab.id as any)}
                                title={tab.label}
                            >
                                <tab.icon className={`h-5 w-5 ${sidebarTab === tab.id ? 'scale-110' : 'group-hover:scale-110'} transition-transform`} />
                                {sidebarTab === tab.id && (
                                     <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-500 animate-in fade-in zoom-in duration-300" />
                                )}
                            </button>
                        ))}
                    </div>
                    
                    <div className={`flex-1 flex flex-col ${sidebarTab === 'chat' ? 'overflow-hidden' : 'overflow-y-auto custom-scrollbar'}`}>
                        {sidebarTab === 'chat' && (
                             <StrategyChatPanel 
                                strategyId={currentStrategyId || undefined} 
                                contextCode={code}
                                className="h-full border-0"
                             />
                        )}
                        {sidebarTab === 'config' && (
                            <div className="p-4 space-y-6">
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <Label className="text-xs text-slate-400">Symbol</Label>
                                        <Select value={symbol} onValueChange={setSymbol}>
                                            <SelectTrigger className="bg-slate-900 border-slate-700"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                {(preferences?.supported_symbols || ["XAU_USD", "EUR_USD", "BTC_USD"]).map((s) => (
                                                    <SelectItem key={s} value={s.replace('/', '_')}>{s.replace('_', '/')}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-xs text-slate-400">Timeframe</Label>
                                        <Select value={timeframe} onValueChange={setTimeframe}>
                                            <SelectTrigger className="bg-slate-900 border-slate-700"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                {(preferences?.preferred_timeframes || ["M1", "M5", "M15", "H1", "H4", "D"]).map((tf) => {
                                                    const normalized = NORMALIZE_TF(tf);
                                                    return <SelectItem key={tf} value={normalized}>{normalized}</SelectItem>;
                                                })}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="space-y-4 pt-4 border-t border-slate-800">
                                     <div className="space-y-2">
                                        <Label className="text-xs text-slate-400">Start Date</Label>
                                        <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="bg-slate-900 border-slate-700" />
                                    </div>
                                     <div className="space-y-2">
                                        <Label className="text-xs text-slate-400">End Date</Label>
                                        <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="bg-slate-900 border-slate-700" />
                                    </div>
                                </div>

                                 <div className="space-y-4 pt-4 border-t border-slate-800">
                                     <div className="space-y-2">
                                        <Label className="text-xs text-slate-400">Initial Capital ($)</Label>
                                        <Input type="number" value={initialCapital} onChange={(e) => setInitialCapital(Number(e.target.value))} className="bg-slate-900 border-slate-700" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label className="text-xs text-slate-400">Fees (%)</Label>
                                            <Input type="number" step="0.0001" value={fees} onChange={(e) => setFees(Number(e.target.value))} className="bg-slate-900 border-slate-700" />
                                        </div>
                                        <div className="space-y-2">
                                            <Label className="text-xs text-slate-400">Slippage (%)</Label>
                                            <Input type="number" step="0.0001" value={slippage} onChange={(e) => setSlippage(Number(e.target.value))} className="bg-slate-900 border-slate-700" />
                                        </div>
                                    </div>
                                </div>
                                
                                <div className="space-y-4 pt-4 border-t border-slate-800">
                                     <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Position Sizing</h3>
                                     <div className="grid grid-cols-2 gap-4">
                                          <div className="space-y-2">
                                             <Label className="text-xs text-slate-400">Type</Label>
                                             <Select value={sizeType} onValueChange={(v) => setSizeType(v as "amount" | "value" | "percent")}>
                                                 <SelectTrigger className="bg-slate-900 border-slate-700 h-8 text-xs"><SelectValue /></SelectTrigger>
                                                 <SelectContent className="min-w-[150px]">
                                                     <SelectItem value="amount">Fixed Amount</SelectItem>
                                                     <SelectItem value="percent">Percent of Equity</SelectItem>
                                                     <SelectItem value="value">Fixed Value ($)</SelectItem>
                                                 </SelectContent>
                                             </Select>
                                         </div>
                                         <div className="space-y-2">
                                             <Label className="text-xs text-slate-400">Size</Label>
                                             <Input 
                                                 type="number" 
                                                 value={orderSize} 
                                                 onChange={(e) => setOrderSize(Number(e.target.value))} 
                                                 className="bg-slate-900 border-slate-700 h-8 text-xs" 
                                                 step="0.01"
                                             />
                                         </div>
                                     </div>
                                     {sizeType === 'percent' && (
                                          <p className="text-[10px] text-slate-500 italic">100 = 100% of available cash per trade.</p>
                                     )}
                                </div>
                            </div>
                        )}
                        {sidebarTab === 'library' && (
                            // Library Tab
                            <div className="p-4 space-y-4">
                                {savedStrategies.length === 0 ? (
                                    <div className="text-center py-8 text-slate-500">
                                        <p>No saved strategies found.</p>
                                        <Button variant="link" onClick={() => setSidebarTab('config')} className="text-emerald-400">Create one?</Button>
                                    </div>
                                ) : (
                                    savedStrategies.map(strat => (
                                        <div 
                                            key={strat.id} 
                                            onClick={() => handleLoadStrategy(strat)}
                                            className={`
                                                group p-3 rounded-lg border cursor-pointer hover:border-emerald-500/50 hover:bg-slate-900 transition-all
                                                ${currentStrategyId === strat.id ? 'border-emerald-500 bg-slate-900' : 'border-slate-800 bg-slate-950'}
                                            `}
                                        >
                                            <div className="flex justify-between items-start mb-1">
                                                <h4 className={`font-medium text-sm ${currentStrategyId === strat.id ? 'text-emerald-400' : 'text-slate-200'}`}>
                                                    {strat.name}
                                                </h4>
                                                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                     <button 
                                                        className="text-slate-500 hover:text-red-400 p-0.5"
                                                        onClick={(e) => handleDeleteClick(strat.id, strat.name, e)}
                                                    >
                                                        <Trash2 className="h-3 w-3" />
                                                     </button>
                                                </div>
                                            </div>
                                            <p className="text-xs text-slate-500 line-clamp-2">{strat.description || "No description"}</p>
                                            <div className="mt-2 flex gap-2 text-[10px] text-slate-600 font-mono">
                                                <span>{String(strat.parameters?.symbol || "ANY")}</span>
                                                <span>•</span>
                                                <span>{new Date(strat.updated_at).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                        {sidebarTab === 'optimize' && (
                             <div className="h-full p-4 flex flex-col overflow-hidden">
                                <OptimizationPanel onRunOptimization={handleRunOptimization} isLoading={isOptimizing} />
                             </div>
                        )}
                        {sidebarTab === 'simulation' && (
                             <div className="h-full p-4 flex flex-col overflow-hidden">
                                <MonteCarloPanel 
                                    trades={lastBacktestResult?.trades || []} 
                                    onRunSimulation={handleRunSimulation} 
                                    isLoading={isSimulating} 
                                />
                             </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
