
'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { strategiesApi } from '@/lib/api/strategies';
import { LogicTemplate, StrategyCreate } from '@/lib/api/types';
import Link from 'next/link';

// Simple JSON Editor Component using textarea for now (replace with library later if needed)
function JsonEditor({ value, onChange, label }: { value: any, onChange: (v: any) => void, label: string }) {
    const [text, setText] = useState(JSON.stringify(value, null, 2));
    const [valid, setValid] = useState(true);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newVal = e.target.value;
        setText(newVal);
        try {
            const parsed = JSON.parse(newVal);
            setValid(true);
            onChange(parsed);
        } catch (err) {
            setValid(false);
        }
    };

    return (
        <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300 justify-between flex">
                <span>{label}</span>
                {!valid && <span className="text-red-400 text-xs">Invalid JSON</span>}
            </label>
            <textarea
                value={text}
                onChange={handleChange}
                className={`w-full h-48 bg-gray-950 border ${valid ? 'border-gray-800' : 'border-red-500'} rounded-lg p-4 font-mono text-sm text-gray-200 focus:outline-none focus:border-accent-blue transition-colors`}
            />
        </div>
    );
}

// NOTE: We need a Broker Account Selector. 
// For MVP, since we don't have a hook for 'useBrokerAccounts' yet (only in Execution Service backend?),
// I will mock or fetch from 'settings' if available, or just use a text input/placeholder.
// Actually, 'getAccountSummary' in execution.ts implies we check specific broker.
// We probably need a 'listFunds' or 'listAccounts' endpoint.
// `services/api-gateway/app/routers/broker_account.py` exists in routes list? 
// Let's assume we can fetch accounts. I'll define a dummy selector for now or just text input for UUID.
// Ideally, we fetch from `/api/v1/broker-accounts/`. I'll use a text input for ID for now to unblock.

export default function ConfigureStrategyPage() {
    const router = useRouter();
    const params = useParams(); // { templateId }
    const templateId = typeof params?.templateId === 'string' ? params.templateId : '';
    
    // State
    const [template, setTemplate] = useState<LogicTemplate | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    
    // Form Config
    const [name, setName] = useState('');
    const [brokerAccountId, setBrokerAccountId] = useState('');
    const [fundId, setFundId] = useState('00000000-0000-0000-0000-000000000000'); // Default Fund? Needs valid UUID.
    // Fetch funds?
    
    const [configJson, setConfigJson] = useState<any>({});
    const [riskSettings, setRiskSettings] = useState<any>({});
    
    // Error
    const [error, setError] = useState<string|null>(null);

    // Load Template
    useEffect(() => {
        if (!templateId) return;
        async function load() {
            try {
                // We re-fetch all templates to find the one matching ID (inefficient but safe for MVP)
                const res = await strategiesApi.getTemplates();
                if (res.status === 'success' && res.data) {
                    const found = res.data.find((t: LogicTemplate) => t.id === templateId);
                    if (found) {
                        setTemplate(found);
                        setConfigJson(found.default_config);
                        setRiskSettings(found.default_risk_settings);
                        setName(`${found.name} Instance`);
                    } else {
                        setError('Template not found');
                    }
                }
            } catch (err) {
                setError('Failed to load template details');
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [templateId]);
    
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);
        
        try {
            if (!brokerAccountId) {
                throw new Error("Broker Account ID is required (Check your Database)");
            }
            
            // In a real app we would select the Fund ID from a list.
            // For now, hardcoding a valid UUID or user input if needed.
            // Ideally current user's default fund.
            
            const payload: StrategyCreate = {
                name,
                template_id: templateId,
                fund_id: fundId, // Make sure this is valid in your DB!
                broker_account_id: brokerAccountId,
                config_json: configJson,
                risk_settings: riskSettings
            };
            
            await strategiesApi.create(payload);
            router.push('/dashboard'); // Or back to strategies list
        } catch (err: any) {
            setError(err.message || "Failed to create strategy");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading...</div>;
    if (error && !template) return <div className="p-8 text-center text-red-500">{error}</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-accent-blue to-accent-green bg-clip-text text-transparent">
                    Configure Strategy
                </h1>
                <p className="text-gray-400 mt-2">Customize parameters for <strong>{template?.name}</strong></p>
            </div>

            <form onSubmit={handleSubmit} className="bg-gray-900/40 border border-gray-800 rounded-xl p-8 space-y-8">
                {/* General Info */}
                <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-gray-200 border-b border-gray-800 pb-2">General Information</h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-400">Strategy Name</label>
                            <input 
                                type="text" 
                                value={name}
                                onChange={e => setName(e.target.value)}
                                className="w-full bg-gray-950 border border-gray-800 rounded-lg p-3 text-white focus:outline-none focus:border-accent-blue"
                                required
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-400">Broker Account ID (UUID)</label>
                            <input 
                                type="text"
                                placeholder="e.g. 123e4567-e89b-..." 
                                value={brokerAccountId}
                                onChange={e => setBrokerAccountId(e.target.value)}
                                className="w-full bg-gray-950 border border-gray-800 rounded-lg p-3 text-white focus:outline-none focus:border-accent-blue"
                                required 
                            />
                            <p className="text-xs text-gray-500">Copy a valid ID from the `broker_accounts` table.</p>
                        </div>
                        
                         <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-400">Fund ID (UUID)</label>
                            <input 
                                type="text"
                                placeholder="e.g. 123e4567-e89b-..." 
                                value={fundId}
                                onChange={e => setFundId(e.target.value)}
                                className="w-full bg-gray-950 border border-gray-800 rounded-lg p-3 text-white focus:outline-none focus:border-accent-blue"
                                required 
                            />
                             <p className="text-xs text-gray-500">Required for associating strategy with a fund.</p>
                        </div>
                    </div>
                </div>

                {/* JSON Configuration */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <JsonEditor 
                        label="Strategy Parameters" 
                        value={configJson} 
                        onChange={setConfigJson} 
                    />
                    <JsonEditor 
                        label="Risk Settings" 
                        value={riskSettings} 
                        onChange={setRiskSettings} 
                    />
                </div>
                
                {error && (
                    <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-500 rounded-lg">
                        {error}
                    </div>
                )}

                <div className="flex justify-end gap-4 pt-4 border-t border-gray-800">
                    <Link href="/strategies/new" className="px-6 py-2 rounded-lg hover:bg-gray-800 text-gray-400 transition-colors">
                        Back
                    </Link>
                    <button 
                        type="submit" 
                        disabled={submitting}
                        className="px-8 py-2 bg-accent-blue hover:bg-accent-blue/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                    >
                        {submitting ? "Creating..." : "Launch Strategy"}
                    </button>
                </div>
            </form>
        </div>
    );
}
