'use client';

import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, Info, Zap, Brain, Shield } from 'lucide-react';
import { getFundRiskParity } from '@/lib/api/fund';
import { RiskParityData } from '@/lib/api/types';

interface RiskParityTableProps {
    fundId: string;
}

export function RiskParityTable({ fundId }: RiskParityTableProps) {
    const [data, setData] = useState<RiskParityData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true);
                const result = await getFundRiskParity(fundId);
                setData(result);
                setError(null);
            } catch (err: any) {
                setError(err.message || 'Failed to fetch risk parity data');
            } finally {
                setLoading(false);
            }
        }

        if (fundId) {
            fetchData();
        }
    }, [fundId]);

    if (loading) {
        return (
            <div className="bg-gray-950/40 border border-gray-800 rounded-2xl p-6 backdrop-blur-md animate-pulse">
                <div className="h-6 w-48 bg-gray-800 rounded mb-4" />
                <div className="space-y-3">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="h-12 bg-gray-900/50 rounded-xl" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-950/20 border border-red-900/50 rounded-2xl p-6 text-red-400">
                <div className="flex items-center gap-2 mb-2">
                    <Info className="w-5 h-5" />
                    <span className="font-semibold">Sync Error</span>
                </div>
                <p className="text-sm opacity-80">{error}</p>
            </div>
        );
    }

    if (!data || data.symbols.length === 0) {
        return (
            <div className="bg-gray-950/40 border border-gray-800 rounded-2xl p-10 text-center backdrop-blur-md">
                <div className="bg-gray-900 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 border border-gray-700">
                    <Shield className="w-6 h-6 text-gray-500" />
                </div>
                <h3 className="text-gray-300 font-medium">No Dynamic Allocation</h3>
                <p className="text-sm text-gray-500 max-w-xs mx-auto mt-2">
                    Enable Risk Parity in fund settings to see AI-driven institutional weights and sentiment analysis.
                </p>
            </div>
        );
    }

    return (
        <div className="bg-gray-950/40 border border-gray-800 rounded-2xl overflow-hidden backdrop-blur-md transition-all hover:border-gray-700/50 group">
            <div className={`p-5 border-b border-gray-800 flex items-center justify-between ${data.systemic_alert ? 'bg-rose-500/5' : 'bg-gradient-to-r from-transparent to-gray-900/40'}`}>
                <div className="flex items-center gap-3">
                    <div className={`p-2 ${data.systemic_alert ? 'bg-rose-500/10' : 'bg-indigo-500/10'} rounded-lg`}>
                        {data.systemic_alert ? <Shield className="w-5 h-5 text-rose-400" /> : <Brain className="w-5 h-5 text-indigo-400" />}
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-gray-100 font-semibold tracking-tight">Institutional Risk Parity</h3>
                            {data.systemic_alert && (
                                <span className="bg-rose-500 text-[9px] font-black text-white px-1.5 py-0.5 rounded animate-pulse uppercase">Systemic Hazard</span>
                            )}
                        </div>
                        <p className="text-[10px] text-gray-500 uppercase tracking-widest mt-0.5">
                            PCA Core Analysis • {(data.market_integration_score * 100).toFixed(1)}% Market Integration
                        </p>
                    </div>
                </div>
                <div className="hidden sm:flex items-center gap-3">
                    <div className="text-right">
                        <p className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Systemic Risk</p>
                        <p className={`text-xs font-mono ${(data.market_integration_score > 0.6) ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {(data.market_integration_score * 100).toFixed(1)}%
                        </p>
                    </div>
                    <span className="text-[10px] font-mono text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 uppercase">Live Engine</span>
                </div>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-gray-900/30">
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest">Asset</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">Weight</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">Sentiment</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">Factor Exp (PC1)</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest text-right">Scaling Adj</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800/50">
                        {data.symbols.map((symbol) => {
                            const isBullish = symbol.sentiment_score >= 0.3;
                            const isBearish = symbol.sentiment_score <= -0.3;
                            const sentimentColor = isBullish ? 'text-emerald-400' : isBearish ? 'text-rose-400' : 'text-gray-400';
                            const sentimentBg = isBullish ? 'bg-emerald-500/10' : isBearish ? 'bg-rose-500/10' : 'bg-gray-500/10';
                            
                            // [PHASE 40] De-risking logic visual
                            const isHighCorr = symbol.pc1_loading > 0.6;
                            const isDerisked = symbol.kc_multiplier < 0.95;

                            return (
                                <tr key={symbol.symbol} className="hover:bg-white/[0.02] transition-colors group/row">
                                    <td className="px-6 py-5">
                                        <div className="flex flex-col">
                                            <div className="flex items-center gap-1.5">
                                                <span className="font-bold text-gray-200 group-hover/row:text-white transition-colors">{symbol.symbol.replace('_', '/')}</span>
                                                {symbol.is_systemic && (
                                                    <span className="text-[8px] bg-red-500/20 text-red-500 px-1 border border-red-500/30 rounded font-mono">SYSTEMIC</span>
                                                )}
                                            </div>
                                            <span className="text-[10px] text-gray-600 mt-1 line-clamp-1 group-hover/row:text-gray-400 transition-colors uppercase tracking-tighter">
                                                {symbol.sentiment_reason || 'Neutral market bias detected by AI analyst'}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-5">
                                        <div className="flex flex-col items-center gap-2">
                                            <span className="text-sm font-semibold font-mono text-indigo-400">{(symbol.weight * 100).toFixed(1)}%</span>
                                            <div className="w-24 h-1 bg-gray-800 rounded-full overflow-hidden">
                                                <div 
                                                    className="h-full bg-gradient-to-r from-indigo-600 to-violet-500 transition-all duration-1000 ease-out" 
                                                    style={{ width: `${symbol.weight * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-5">
                                        <div className="flex justify-center">
                                            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${sentimentBg} border-current/10 ${sentimentColor}`}>
                                                {isBullish ? <TrendingUp className="w-3 h-3" /> : isBearish ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                                                <span className="text-[11px] font-bold">{symbol.sentiment_score.toFixed(2)}</span>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-5">
                                        <div className="flex flex-col items-center">
                                            <div className={`flex items-center gap-1 text-sm font-mono ${isHighCorr ? 'text-orange-400' : 'text-gray-500'}`}>
                                                <Shield className="w-3 h-3 opacity-50" />
                                                <span>{symbol.pc1_loading.toFixed(2)}</span>
                                            </div>
                                            <div className={`w-16 h-0.5 mt-1.5 rounded-full ${isHighCorr ? 'bg-orange-950' : 'bg-gray-800'}`}>
                                                <div 
                                                    className={`h-full ${isHighCorr ? 'bg-orange-500' : 'bg-gray-600'} rounded-full`} 
                                                    style={{ width: `${Math.min(symbol.pc1_loading * 100, 100)}%` }}
                                                />
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-5 text-right">
                                        <div className="flex flex-col items-end">
                                            <div className="flex items-center gap-1.5 font-mono">
                                                <Zap className={`w-3.5 h-3.5 ${symbol.scaling_multiplier > 1.05 ? 'text-emerald-400' : symbol.scaling_multiplier < 0.95 ? 'text-rose-400' : 'text-gray-500'}`} />
                                                <span className={`text-sm font-bold ${symbol.scaling_multiplier > 1.05 ? 'text-emerald-400' : symbol.scaling_multiplier < 0.95 ? 'text-rose-400' : 'text-gray-300'}`}>
                                                    {(symbol.scaling_multiplier * symbol.kc_multiplier).toFixed(2)}x
                                                </span>
                                            </div>
                                            {isDerisked && (
                                                <span className="text-[8px] text-rose-500 font-bold uppercase tracking-tighter mt-1 flex items-center gap-1">
                                                    <Info className="w-2 h-2" /> Anti-Correlation Applied
                                                </span>
                                            )}
                                            {!isDerisked && (
                                                <span className="text-[9px] text-gray-600 mt-1 uppercase tracking-tighter font-medium">Risk Adj Multiplier</span>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            
            <div className="p-4 bg-gray-900/20 border-t border-gray-800/50 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                    <Info className="w-3.5 h-3.5 text-gray-500" />
                    <p className="text-[10px] text-gray-600 leading-tight">
                        Multipliers adjust 1.25x for <span className="text-emerald-600/80 font-bold uppercase tracking-widest text-[9px]">Alpha Confluence</span> and 0.5x for <span className="text-rose-600/80 font-bold uppercase tracking-widest text-[9px]">Market Conflict</span>.
                    </p>
                </div>
                {data.systemic_alert && (
                    <div className="flex items-center gap-2 px-2 py-1 bg-rose-500/5 border border-rose-500/10 rounded-lg">
                        <Shield className="w-3 h-3 text-rose-500" />
                        <p className="text-[10px] text-rose-400/80 font-medium">
                            <span className="font-bold text-rose-500">SYSTEMIC ALERT:</span> Market integration exceeds 60%. De-risking factor (Kc=0.70x) applied to systemic assets with overlapping exposure.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}

