
import React from 'react';
import { BotConfig, TrendMode, GridSpacingType, GridSizingType, MarketAnomaly, IndicatorType } from '../types';
import { Play, Pause, RefreshCw, Activity, Layers, TrendingUp, Shield, Wallet, Globe, BarChart2, Zap, Eye, Save, Download } from 'lucide-react';
import { suggestParameters } from '../services/geminiService';

interface SidebarProps {
  config: BotConfig;
  setConfig: (c: BotConfig) => void;
  isRunning: boolean;
  setIsRunning: (v: boolean) => void;
  onReset: () => void;
  currentPrice: number;
  onRunSimulation: () => void;
  onTriggerShock?: () => void; 
}

const PRESETS = [
  { id: 'BTC', name: 'Bitcoin (BTC/USD)', symbol: 'BTC', price: 95000, top: 105000, bottom: 85000, size: 0.1 },
  { id: 'ETH', name: 'Ethereum (ETH/USD)', symbol: 'ETH', price: 3400, top: 4000, bottom: 2800, size: 1 },
  { id: 'XAU', name: 'Gold (XAU/USD)', symbol: 'XAU', price: 2650, top: 2800, bottom: 2500, size: 1 },
  { id: 'EUR', name: 'Euro (EUR/USD)', symbol: 'EUR', price: 1.0500, top: 1.0800, bottom: 1.0200, size: 1000 },
];

export const Sidebar: React.FC<SidebarProps> = ({ 
  config, setConfig, isRunning, setIsRunning, onReset, currentPrice, onRunSimulation, onTriggerShock
}) => {
  const [isSuggesting, setIsSuggesting] = React.useState(false);

  const handleChange = (key: keyof BotConfig, value: any) => {
    setConfig({ ...config, [key]: value });
  };

  const handlePresetChange = (presetId: string) => {
    const preset = PRESETS.find(p => p.id === presetId);
    if (preset) {
        setConfig({
            ...config,
            assetSymbol: preset.symbol,
            initialPrice: preset.price,
            gridTop: preset.top,
            gridBottom: preset.bottom,
            maxBuyPrice: preset.top,
            minSellPrice: preset.bottom,
            orderSize: preset.size,
        });
    }
  };

  const saveConfig = () => {
    localStorage.setItem('gridBotConfig', JSON.stringify(config));
    alert('Strategy Saved!');
  };

  const loadConfig = () => {
    const saved = localStorage.getItem('gridBotConfig');
    if (saved) {
      setConfig(JSON.parse(saved));
      alert('Strategy Loaded!');
    }
  };

  const handleAISuggest = async () => {
    setIsSuggesting(true);
    try {
      const desc = `Market condition is ${config.trendMode} with ${config.volatility * 100}% volatility for ${config.assetSymbol}. Optimize for this.`;
      const result = await suggestParameters(desc, currentPrice);
      setConfig({
        ...config,
        gridTop: result.gridTop,
        gridBottom: result.gridBottom,
        gridCount: result.gridCount,
      });
      onReset();
    } catch (e) {
      console.error(e);
    } finally {
      setIsSuggesting(false);
    }
  };

  const InputField = ({ label, value, onChange, min, max, step = 1 }: { label: string, value: number, onChange: (v: number) => void, min?: number, max?: number, step?: number }) => (
    <div className="space-y-1">
      <label className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{label}</label>
      <input 
        type="number" 
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full bg-[#111827] border border-gray-700 rounded-md p-2 text-xs text-white font-mono focus:border-blue-500 outline-none transition-all"
      />
    </div>
  );

  return (
    <div className="w-[340px] bg-[#0B0F19] border-r border-gray-800 h-screen overflow-y-auto fixed left-0 top-0 p-5 flex flex-col z-30 shadow-2xl custom-scrollbar">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <Activity className="text-blue-500" size={24} />
          <h1 className="text-xl font-bold text-white tracking-tight">GRID ROBOT</h1>
        </div>
        <div className="text-[10px] text-blue-400 font-bold tracking-[0.2em] uppercase ml-9">Volatility Harvester</div>
      </div>

      <div className="space-y-6 flex-1">
        
        {/* Asset Selection */}
        <div className="mb-2 p-3 bg-blue-900/10 border border-blue-900/30 rounded-lg">
            <div className="flex items-center gap-2 text-blue-400 mb-2">
                <Globe size={14} />
                <h3 className="text-[11px] font-bold uppercase tracking-widest">Asset Preset</h3>
            </div>
            <select
                className="w-full bg-[#111827] border border-gray-700 rounded-md p-2 text-xs text-white font-mono focus:border-blue-500 outline-none cursor-pointer"
                onChange={(e) => handlePresetChange(e.target.value)}
                value={PRESETS.find(p => p.symbol === config.assetSymbol)?.id || ''}
            >
                <option value="" disabled>Select Asset</option>
                {PRESETS.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                ))}
            </select>
        </div>

        {/* Account & Asset */}
        <div className="space-y-3">
           <div className="flex items-center gap-2 text-gray-400">
             <Wallet size={14} />
             <h3 className="text-[11px] font-bold uppercase tracking-widest">Account & Config</h3>
           </div>
           <div className="grid grid-cols-2 gap-3">
              <InputField 
                label="Initial Capital ($)" 
                value={config.initialCapital} 
                onChange={(v) => handleChange('initialCapital', v)} 
              />
              <InputField 
                label="Start Price" 
                value={config.initialPrice} 
                onChange={(v) => handleChange('initialPrice', v)} 
              />
           </div>
           
           {/* Execution Reality (New) */}
           <div className="pt-2 border-t border-gray-800">
               <h4 className="text-[9px] text-gray-500 uppercase font-bold mb-2">Execution Reality (Friction)</h4>
               <div className="grid grid-cols-2 gap-3">
                   <InputField 
                    label="Tx Fee (%)" 
                    value={config.transactionFee} 
                    step={0.01}
                    onChange={(v) => handleChange('transactionFee', v)} 
                  />
                  <InputField 
                    label="Spread (%)" 
                    value={config.marketSpread} 
                    step={0.01}
                    onChange={(v) => handleChange('marketSpread', v)} 
                  />
               </div>
           </div>

           <div>
              <InputField 
                label={`Order Size (${config.assetSymbol})`} 
                value={config.orderSize} 
                onChange={(v) => handleChange('orderSize', v)} 
              />
              <div className="text-[9px] text-gray-500 text-right mt-1">Fixed volume per grid</div>
           </div>
        </div>

        {/* Technical Analysis / Indicators */}
        <div className="space-y-3">
           <div className="flex items-center gap-2 text-cyan-400">
             <Eye size={14} />
             <h3 className="text-[11px] font-bold uppercase tracking-widest">Technical Indicators</h3>
           </div>
           <div className="p-3 bg-[#111827] rounded-lg border border-gray-800 space-y-2">
               <label className="text-[10px] text-gray-400 font-bold uppercase">Overlay Indicator</label>
               <select 
                  value={config.activeIndicator}
                  onChange={(e) => handleChange('activeIndicator', e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded text-xs text-white p-2 outline-none"
                >
                  <option value={IndicatorType.NONE}>None</option>
                  <option value={IndicatorType.BOLLINGER}>Bollinger Bands (20, 2)</option>
                  <option value={IndicatorType.DONCHIAN}>Donchian Channels (20)</option>
                  <option value={IndicatorType.ATR_BANDS}>ATR Bands (Vol Dynamic)</option>
                </select>
           </div>
        </div>

        {/* Market Regime */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-blue-400">
             <TrendingUp size={14} />
             <h3 className="text-[11px] font-bold uppercase tracking-widest">Market Regime & Anomalies</h3>
          </div>
          
          <div className="grid grid-cols-1 gap-3 p-3 bg-[#111827] rounded-lg border border-gray-800">
             <div className="space-y-2">
                <label className="text-[10px] text-gray-400">Trend Model</label>
                <select 
                  value={config.trendMode}
                  onChange={(e) => handleChange('trendMode', e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded text-xs text-white p-2 outline-none"
                >
                  <option value={TrendMode.SIDEWAYS}>Non-Trend (Sideways)</option>
                  <option value={TrendMode.UPTREND}>Bullish (Uptrend)</option>
                  <option value={TrendMode.DOWNTREND}>Bearish (Downtrend)</option>
                </select>
             </div>

             <div className="space-y-2 border-t border-gray-700 pt-2">
                <label className="text-[10px] text-yellow-500 font-bold flex items-center gap-1">
                    <Zap size={10} /> Market Scenario
                </label>
                <select 
                  value={config.anomaly}
                  onChange={(e) => handleChange('anomaly', e.target.value)}
                  className="w-full bg-gray-900 border border-yellow-900/30 text-yellow-400 rounded text-xs p-2 outline-none focus:border-yellow-500"
                >
                  <option value={MarketAnomaly.NONE}>None (Random Walk)</option>
                  <option value={MarketAnomaly.PUMP_DUMP}>Pump & Dump (Volatile)</option>
                  <option value={MarketAnomaly.FLASH_CRASH}>Flash Crash (Fat-tail)</option>
                  <option value={MarketAnomaly.HIGH_VOL_REGIME}>High Volatility Regime</option>
                  <option value={MarketAnomaly.MEAN_REVERSION}>Strong Mean Reversion</option>
                </select>
             </div>

             <div className="space-y-2">
                <div className="flex justify-between text-[10px] text-gray-400">
                  <span>Base Volatility</span>
                  <span>{(config.volatility * 100).toFixed(0)}%</span>
                </div>
                <input 
                  type="range" min="0" max="1" step="0.05"
                  value={config.volatility}
                  onChange={(e) => handleChange('volatility', Number(e.target.value))}
                  className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
             </div>
          </div>
        </div>

        {/* Advanced Grid Design */}
        <div className="space-y-3">
           <div className="flex items-center gap-2 text-purple-400">
             <Layers size={14} />
             <h3 className="text-[11px] font-bold uppercase tracking-widest">Advanced Strategy Design</h3>
          </div>
          
          <div className="p-3 bg-[#111827] rounded-lg border border-gray-800 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <InputField 
                  label="Grid Top" 
                  value={config.gridTop} 
                  onChange={(v) => handleChange('gridTop', v)} 
                />
                <InputField 
                  label="Grid Bottom" 
                  value={config.gridBottom} 
                  onChange={(v) => handleChange('gridBottom', v)} 
                />
              </div>

              {/* Strategy Triggers / Filters */}
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-gray-800">
                 <div className="col-span-2 text-[9px] text-gray-500 uppercase font-bold">Filters (Only Trade Inside)</div>
                 <InputField 
                  label="Max Buy Price" 
                  value={config.maxBuyPrice} 
                  onChange={(v) => handleChange('maxBuyPrice', v)} 
                />
                <InputField 
                  label="Min Sell Price" 
                  value={config.minSellPrice} 
                  onChange={(v) => handleChange('minSellPrice', v)} 
                />
              </div>

               <div className="space-y-1">
                 <label className="text-[10px] text-gray-400 font-bold uppercase">Grid Spacing</label>
                 <select 
                    value={config.spacingType}
                    onChange={(e) => handleChange('spacingType', e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded text-xs text-white p-2 outline-none"
                  >
                    <option value={GridSpacingType.ARITHMETIC}>Arithmetic (Equal)</option>
                    <option value={GridSpacingType.GEOMETRIC}>Geometric (Logarithmic)</option>
                  </select>
               </div>
               
               <div className="space-y-1">
                 <label className="text-[10px] text-gray-400 font-bold uppercase">Position Sizing</label>
                 <select 
                    value={config.sizingType}
                    onChange={(e) => handleChange('sizingType', e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded text-xs text-white p-2 outline-none"
                  >
                    <option value={GridSizingType.FIXED}>Fixed (Standard)</option>
                    <option value={GridSizingType.MARTINGALE}>Martingale (Aggressive)</option>
                    <option value={GridSizingType.ANTI_MARTINGALE}>Anti-Martingale (Safe)</option>
                  </select>
               </div>

              <div className="space-y-1 mt-2">
                <div className="flex justify-between text-[10px] text-gray-400 mb-1">
                  <span className="font-bold uppercase tracking-wider">Grid Count</span>
                  <span className="text-white font-mono">{config.gridCount}</span>
                </div>
                <input 
                  type="range" min="5" max="200" 
                  value={config.gridCount}
                  onChange={(e) => handleChange('gridCount', Number(e.target.value))}
                  className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
              </div>
          </div>
        </div>

        {/* Risk Management Protocol */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-emerald-400">
             <Shield size={14} />
             <h3 className="text-[11px] font-bold uppercase tracking-widest">Risk Management Protocol</h3>
          </div>

          <div className="p-3 bg-[#111827] rounded-lg border border-gray-800 space-y-3">
             <div className="grid grid-cols-2 gap-3">
                <InputField 
                  label="Stop Loss (% Equity)" 
                  value={config.riskStopLoss} 
                  onChange={(v) => handleChange('riskStopLoss', v)} 
                />
                <InputField 
                  label="DD Guard (% Drawdown)" 
                  value={config.riskDrawdownGuard} 
                  onChange={(v) => handleChange('riskDrawdownGuard', v)} 
                />
             </div>
             
             <div>
                <button 
                  onClick={onTriggerShock}
                  className="w-full py-2 bg-red-900/20 border border-red-500/30 text-red-400 hover:bg-red-900/40 text-[10px] font-bold uppercase rounded transition-colors flex items-center justify-center gap-2"
                >
                    <Activity size={12} /> Simulate Flash Crash (-15%)
                </button>
             </div>
          </div>
        </div>
        
        {/* Strategy Management (New) */}
        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-800">
           <button onClick={saveConfig} className="py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[10px] uppercase font-bold flex items-center justify-center gap-1">
              <Save size={12} /> Save Strategy
           </button>
           <button onClick={loadConfig} className="py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[10px] uppercase font-bold flex items-center justify-center gap-1">
              <Download size={12} /> Load Strategy
           </button>
        </div>

         <div className="space-y-3 pt-2 border-t border-gray-800">
           <button 
              onClick={onRunSimulation}
              className="w-full py-2 bg-gradient-to-r from-purple-900/40 to-blue-900/40 border border-purple-500/30 text-purple-300 text-[10px] uppercase font-bold rounded-sm hover:from-purple-900/60 hover:to-blue-900/60 transition-all flex items-center justify-center gap-2"
           >
              <BarChart2 size={12} /> Run 100 Simulations
           </button>
         </div>

         <div className="space-y-4 pt-4 border-t border-gray-800">
            <div className="flex items-center justify-between text-[10px] text-gray-500 uppercase font-bold">
               <span>Sim Speed</span>
               <span>{config.simSpeed}ms</span>
            </div>
            <input 
              type="range" min="10" max="200" step="10"
              value={config.simSpeed}
              onChange={(e) => handleChange('simSpeed', Number(e.target.value))}
              className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
         </div>

      </div>

      <div className="mt-6 grid grid-cols-2 gap-2">
        <button 
          onClick={onReset}
          className="flex items-center justify-center gap-2 bg-[#1f2937] hover:bg-gray-700 text-white py-3 rounded-sm font-bold text-xs transition-colors border border-gray-700"
        >
          <RefreshCw size={14} /> RESET / APPLY
        </button>
        
        <button 
          onClick={() => setIsRunning(!isRunning)}
          className={`flex items-center justify-center gap-2 py-3 rounded-sm font-bold text-xs transition-colors ${
            isRunning 
              ? 'bg-blue-600 hover:bg-blue-500 text-white' 
              : 'bg-blue-600 hover:bg-blue-500 text-white'
          }`}
        >
          {isRunning ? <Pause size={14} /> : <Play size={14} />}
          {isRunning ? 'PAUSE' : 'START'}
        </button>
      </div>
      
       <button 
          disabled={isSuggesting}
          onClick={handleAISuggest}
          className="w-full mt-2 py-2 border border-blue-900/50 bg-blue-900/20 text-blue-400 text-[10px] uppercase font-bold rounded-sm hover:bg-blue-900/40 transition-colors flex items-center justify-center gap-2"
        >
          <Activity size={12} /> {isSuggesting ? 'Optimizing...' : 'AI Auto-Tune'}
        </button>
    </div>
  );
};
