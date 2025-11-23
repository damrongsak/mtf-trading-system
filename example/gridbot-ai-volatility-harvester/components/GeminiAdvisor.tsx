
import React, { useState } from 'react';
import { BotStats, BotConfig, AIAnalysisResult, ScenarioSuggestion } from '../types';
import { analyzePerformance } from '../services/geminiService';
import { Sparkles, MessageSquare, Play, RefreshCcw, AlertTriangle, CheckCircle, TrendingUp } from 'lucide-react';

interface GeminiAdvisorProps {
  stats: BotStats;
  config: BotConfig;
  onApplyScenario: (overrides: Partial<BotConfig>) => void;
}

export const GeminiAdvisor: React.FC<GeminiAdvisorProps> = ({ stats, config, onApplyScenario }) => {
  const [analysis, setAnalysis] = useState<AIAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    setLoading(true);
    const result = await analyzePerformance(stats, config);
    setAnalysis(result);
    setLoading(false);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400 border-emerald-500';
    if (score >= 50) return 'text-yellow-400 border-yellow-500';
    return 'text-red-400 border-red-500';
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4 h-[280px] flex flex-col shadow-lg relative overflow-hidden">
      {/* Decorative background element */}
      <div className="absolute -top-10 -right-10 w-40 h-40 bg-blue-900/10 rounded-full blur-3xl pointer-events-none"></div>

      {/* Header */}
      <div className="flex items-center justify-between mb-3 z-10">
        <h3 className="text-blue-400 font-bold text-xs uppercase tracking-widest flex items-center gap-2">
          <Sparkles size={14} className="text-blue-400" /> Quant Research Lab
        </h3>
        <button 
          onClick={handleAnalyze}
          disabled={loading}
          className="text-[10px] font-bold uppercase bg-blue-600/10 hover:bg-blue-600/20 text-blue-300 px-3 py-1.5 rounded border border-blue-500/20 transition-all disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? <RefreshCcw size={10} className="animate-spin" /> : <Play size={10} />}
          {loading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>

      <div className="flex-1 custom-scrollbar overflow-y-auto relative z-10">
        {analysis ? (
          <div className="animate-in fade-in slide-in-from-bottom-2 space-y-4">
            
            {/* Top Section: Score & Explanation */}
            <div className="flex gap-4">
               {/* Health Score Gauge */}
               <div className={`relative w-20 h-20 flex-shrink-0 rounded-full border-4 flex items-center justify-center bg-gray-900/50 ${getScoreColor(analysis.healthScore)}`}>
                  <div className="text-center">
                      <div className="text-xl font-black font-mono">{analysis.healthScore}</div>
                      <div className="text-[8px] uppercase font-bold text-gray-500">Health</div>
                  </div>
               </div>

               {/* Explanation */}
               <div className="flex-1">
                  <h4 className="text-xs font-bold text-gray-300 mb-1">Analyst Insight</h4>
                  <p className="text-[11px] text-gray-400 leading-relaxed font-mono border-l-2 border-gray-700 pl-2">
                     {analysis.explanation}
                  </p>
               </div>
            </div>

            {/* Bottom Section: Scenarios */}
            <div>
               <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                 <TrendingUp size={12} /> Proposed Scenarios
               </h4>
               <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {analysis.suggestions.map((scenario, idx) => (
                      <div key={idx} className="bg-gray-800/40 border border-gray-700 hover:border-blue-500/50 rounded p-2 transition-all group">
                          <div className="flex justify-between items-start mb-1">
                              <span className="text-[10px] font-bold text-white truncate">{scenario.name}</span>
                          </div>
                          <p className="text-[9px] text-gray-400 leading-tight mb-2 h-8 overflow-hidden">
                              {scenario.description}
                          </p>
                          <button 
                            onClick={() => onApplyScenario(scenario.configOverrides)}
                            className="w-full py-1 bg-gray-700 group-hover:bg-blue-600 text-[9px] text-gray-300 group-hover:text-white font-bold uppercase rounded transition-colors"
                          >
                            Apply Config
                          </button>
                      </div>
                  ))}
               </div>
            </div>

          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-gray-600 gap-3">
            <div className="w-12 h-12 rounded-full bg-gray-800/50 flex items-center justify-center">
                <MessageSquare size={20} className="opacity-30" />
            </div>
            <div className="text-center">
                <p className="text-xs font-bold text-gray-500">No Analysis Data</p>
                <p className="text-[10px] text-gray-600 max-w-[200px] mt-1">
                  Run the analyst to get a Health Score and AI-generated grid scenarios.
                </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
