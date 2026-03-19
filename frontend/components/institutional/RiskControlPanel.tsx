'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Shield, AlertTriangle, Power, Save, RefreshCw, BrainCircuit, XCircle } from 'lucide-react';
import { analyticsApi } from '@/lib/api/analytics';
import { FundRiskConfig, RiskRecommendation } from '@/lib/api/types';
import { logger } from '@/lib/api/app-logger';

interface RiskControlPanelProps {
    fundId?: string;
}

export function RiskControlPanel({ fundId }: RiskControlPanelProps) {
    const [config, setConfig] = useState<FundRiskConfig | null>(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [drawdown, setDrawdown] = useState<string>('');
    const [grossLimit, setGrossLimit] = useState<string>('');
    const [reviewing, setReviewing] = useState(false);
    const [aiRecommendation, setAiRecommendation] = useState<RiskRecommendation | null>(null);

    const fetchConfig = useCallback(async () => {
        if (!fundId) return;
        try {
            setLoading(true);
            const res = await analyticsApi.getFundRiskConfig(fundId);
            if (res.data) {
                setConfig(res.data);
                setDrawdown(res.data.max_drawdown_threshold?.toString() || '');
                setGrossLimit(res.data.gross_exposure_limit?.toString() || '');
            }
        } catch (e) {
            logger.error('Failed to fetch risk config', e);
        } finally {
            setLoading(false);
        }
    }, [fundId]);

    useEffect(() => {
        fetchConfig();
    }, [fetchConfig]);

    const handleSave = async () => {
        if (!fundId) return;
        try {
            setSaving(true);
            await analyticsApi.updateFundRiskConfig(fundId, {
                max_drawdown_threshold: parseFloat(drawdown),
                gross_exposure_limit: parseFloat(grossLimit)
            });
            await fetchConfig();
        } catch (e) {
            logger.error('Failed to update risk config', e);
        } finally {
            setSaving(false);
        }
    };

    const handleToggleKillSwitch = async (active: boolean) => {
        if (!fundId) return;
        if (!confirm(`Are you sure you want to ${active ? 'HALT' : 'RESUME'} all trading for this fund?`)) return;
        
        try {
            setSaving(true);
            await analyticsApi.toggleFundKillSwitch(fundId, { active });
            await fetchConfig();
        } catch (e) {
            logger.error('Failed to toggle kill switch', e);
        } finally {
            setSaving(false);
        }
    };

    const handleTriggerAIReview = async () => {
        if (!fundId) return;
        try {
            setReviewing(true);
            setAiRecommendation(null);
            const res = await analyticsApi.triggerAiRiskReview(fundId);
            if (res.data && res.data.recommendation) {
                setAiRecommendation(res.data.recommendation);
            }
        } catch (e) {
            logger.error('Failed to trigger AI risk review', e);
        } finally {
            setReviewing(false);
        }
    };

    const handleApplyRecommendation = async () => {
        if (!fundId || !aiRecommendation) return;
        try {
            setSaving(true);
            await analyticsApi.applyAiRiskRecommendation(fundId, aiRecommendation);
            setAiRecommendation(null);
            await fetchConfig();
        } catch (e) {
            logger.error('Failed to apply AI recommendation', e);
        } finally {
            setSaving(false);
        }
    };

    if (!fundId) return (
        <div className="flex flex-col items-center justify-center p-12 bg-gray-950/50 border border-dashed border-gray-800 rounded-xl text-gray-500">
            <Shield className="w-12 h-12 mb-4 opacity-20" />
            <p>Select an account to manage fund risk controls</p>
        </div>
    );

    if (loading && !config) return (
        <div className="flex items-center justify-center p-12">
            <RefreshCw className="w-8 h-8 text-accent-blue animate-spin opacity-20" />
        </div>
    );

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Thresholds Card */}
                <div className="lg:col-span-2 bg-gray-950/50 border border-gray-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-accent-blue/10 rounded-lg">
                                <Shield className="w-5 h-5 text-accent-blue" />
                            </div>
                            <h3 className="font-semibold text-gray-100">Drawdown & Exposure Limits</h3>
                        </div>
                        <button 
                            onClick={handleSave}
                            disabled={saving}
                            className="flex items-center gap-2 px-4 py-2 bg-accent-blue text-white text-xs font-bold rounded-lg hover:bg-blue-500 disabled:opacity-50 transition-all"
                        >
                            {saving ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                            SAVE CHANGES
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div className="space-y-4">
                            <label className="block">
                                <span className="text-xs font-mono text-gray-500 uppercase">Max Drawdown Threshold (%)</span>
                                <input 
                                    type="number" 
                                    value={drawdown}
                                    onChange={(e) => setDrawdown(e.target.value)}
                                    className="mt-2 w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-accent-blue transition-colors"
                                    placeholder="e.g. 5.0"
                                />
                                <p className="mt-2 text-[10px] text-gray-500 italic">
                                    Breach triggers automatic position liquidation and fund halt.
                                </p>
                            </label>

                            <label className="block">
                                <span className="text-xs font-mono text-gray-500 uppercase">Net Exposure Limit (%)</span>
                                <input 
                                    type="number" 
                                    disabled
                                    className="mt-2 w-full bg-gray-900/50 border border-gray-800 rounded-lg px-4 py-3 text-sm text-gray-600 cursor-not-allowed"
                                    placeholder="15.0 (Default)"
                                />
                            </label>
                        </div>

                        <div className="space-y-4">
                             <label className="block">
                                <span className="text-xs font-mono text-gray-500 uppercase">Gross Exposure Limit (%)</span>
                                <input 
                                    type="number" 
                                    value={grossLimit}
                                    onChange={(e) => setGrossLimit(e.target.value)}
                                    className="mt-2 w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-accent-blue transition-colors"
                                    placeholder="e.g. 100.0"
                                />
                            </label>

                            <div className="p-4 bg-accent-blue/5 border border-accent-blue/20 rounded-lg">
                                <div className="flex gap-3">
                                    <AlertTriangle className="w-4 h-4 text-accent-blue flex-shrink-0" />
                                    <p className="text-[10px] text-gray-400 leading-relaxed">
                                        Institutional risk controls are enforced at the execution gateway level. 
                                        Changes are immediate and affect all child accounts within this fund.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Kill Switch Card */}
                <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6 flex flex-col">
                    <div className="flex items-center gap-3 mb-8">
                        <div className="p-2 bg-red-400/10 rounded-lg">
                            <Power className="w-5 h-5 text-red-400" />
                        </div>
                        <h3 className="font-semibold text-gray-100">Fund Panic Button</h3>
                    </div>

                    <div className="flex-1 flex flex-col items-center justify-center space-y-6">
                        <div className="w-full space-y-4">
                            <button 
                                onClick={handleTriggerAIReview}
                                disabled={reviewing || loading}
                                className="w-full py-3 bg-gray-900 border border-gray-800 rounded-xl flex items-center justify-center gap-2 text-xs font-bold text-gray-300 hover:bg-gray-800 transition-all"
                            >
                                {reviewing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <BrainCircuit className="w-4 h-4 text-accent-blue" />}
                                AI RISK ANALYSIS
                            </button>

                            {aiRecommendation && (
                                <div className="p-4 bg-accent-blue/10 border border-accent-blue/30 rounded-xl space-y-3 animate-in fade-in slide-in-from-top-4">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <BrainCircuit className="w-4 h-4 text-accent-blue" />
                                            <span className="text-[10px] font-bold text-accent-blue tracking-widest uppercase">AI Suggestion</span>
                                        </div>
                                        <button onClick={() => setAiRecommendation(null)}>
                                            <XCircle className="w-4 h-4 text-gray-500 hover:text-gray-300" />
                                        </button>
                                    </div>
                                    <p className="text-[10px] text-gray-300 leading-tight">
                                        {aiRecommendation.reasoning || "AI recommends rebalancing risk parameters based on current market pulse."}
                                    </p>
                                    <div className="grid grid-cols-2 gap-2 pb-2">
                                        <div className="bg-gray-950/50 p-2 rounded-lg border border-gray-800">
                                            <span className="block text-[8px] text-gray-500 uppercase font-mono">Drawdown</span>
                                            <span className="text-[10px] font-bold text-gray-100">{aiRecommendation.max_drawdown_threshold}%</span>
                                        </div>
                                        <div className="bg-gray-950/50 p-2 rounded-lg border border-gray-800">
                                            <span className="block text-[8px] text-gray-500 uppercase font-mono">Risk (%)</span>
                                            <span className="text-[10px] font-bold text-gray-100">{aiRecommendation.risk_percentage}%</span>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={handleApplyRecommendation}
                                        className="w-full py-2 bg-accent-blue text-white text-[10px] font-bold rounded-lg hover:bg-blue-500 shadow-lg shadow-blue-500/20"
                                    >
                                        APPLY RECOMMENDATION
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className={`p-8 rounded-full border-4 ${config?.kill_switch_active ? 'bg-red-500/10 border-red-500 shadow-[0_0_30px_rgba(239,68,68,0.2)]' : 'bg-gray-900 border-gray-800'}`}>
                            <Power className={`w-12 h-12 ${config?.kill_switch_active ? 'text-red-500' : 'text-gray-600'}`} />
                        </div>
                        
                        <div className="text-center">
                            <span className={`text-sm font-bold uppercase tracking-widest ${config?.kill_switch_active ? 'text-red-500' : 'text-gray-500'}`}>
                                {config?.kill_switch_active ? 'FUND HALTED' : 'FUND ACTIVE'}
                            </span>
                            <p className="text-[10px] text-gray-500 mt-1 max-w-[180px]">
                                {config?.kill_switch_active 
                                    ? 'Trading is currently suspended for this fund. New orders will be rejected.' 
                                    : 'System is running normally. All risk filters are active.'}
                            </p>
                        </div>

                        <button 
                            disabled={saving}
                            onClick={() => handleToggleKillSwitch(!config?.kill_switch_active)}
                            className={`w-full py-4 rounded-xl text-xs font-bold tracking-widest transition-all ${
                                config?.kill_switch_active 
                                ? 'bg-accent-green hover:bg-green-500 text-white' 
                                : 'bg-red-500 hover:bg-red-600 text-white shadow-[0_4px_12px_rgba(239,68,68,0.3)]'
                            }`}
                        >
                            {config?.kill_switch_active ? 'RESUME FUND' : 'HALT FUND NOW'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
