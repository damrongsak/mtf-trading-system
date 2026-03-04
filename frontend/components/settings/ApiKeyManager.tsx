"use client";

import React, { useState, useEffect } from 'react';
import { getApiKeys, createApiKey, deleteApiKey, ApiKeyResponse } from '@/lib/api/api-keys';
import { Key, Plus, Trash2, Eye, EyeOff, Copy, AlertCircle, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

export const ApiKeyManager: React.FC = () => {
    const [keys, setKeys] = useState<ApiKeyResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreating, setIsCreating] = useState(false);
    const [newKeyName, setNewKeyName] = useState('');
    const [newlyCreatedKey, setNewlyCreatedKey] = useState<ApiKeyResponse | null>(null);

    useEffect(() => {
        loadKeys();
    }, []);

    const loadKeys = async () => {
        try {
            const data = await getApiKeys();
            setKeys(data);
        } catch (error) {
            toast.error("Failed to load API keys");
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newKeyName.trim()) return;

        try {
            const newKey = await createApiKey(newKeyName);
            setNewlyCreatedKey(newKey);
            setNewKeyName('');
            loadKeys();
        } catch (error) {
            toast.error("Failed to create API key");
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to revoke this API key? This action cannot be undone.")) return;

        try {
            await deleteApiKey(id);
            setKeys(keys.filter(k => k.id !== id));
            toast.success("API Key revoked");
        } catch (error) {
            toast.error("Failed to revoke API key");
        }
    };

    const copyToClipboard = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        toast.success(`${label} copied to clipboard`);
    };

    if (loading) return <div className="animate-pulse space-y-4">
        {[1, 2, 3].map(i => <div key={i} className="h-16 bg-slate-800/30 rounded-lg" />)}
    </div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
                        <Key className="w-5 h-5 text-accent-blue" />
                        3rd Party API Keys
                    </h2>
                    <p className="text-sm text-slate-400">Manage keys for external integrations and HFT-lite partners.</p>
                </div>
                <button 
                    onClick={() => setIsCreating(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-accent-blue/10 hover:bg-accent-blue/20 text-accent-blue border border-accent-blue/30 rounded-lg transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    Create Key
                </button>
            </div>

            {/* Creation Modal / Form */}
            {isCreating && !newlyCreatedKey && (
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-md animate-in fade-in zoom-in duration-200">
                    <form onSubmit={handleCreate} className="space-y-4">
                        <h3 className="text-lg font-medium text-slate-200">New API Key</h3>
                        <div className="space-y-2">
                            <label className="text-xs text-slate-500 uppercase font-semibold">Key Name (e.g. MyTradingBot)</label>
                            <input 
                                autoFocus
                                value={newKeyName}
                                onChange={(e) => setNewKeyName(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-accent-blue"
                                placeholder="Enter a descriptive name..."
                            />
                        </div>
                        <div className="flex justify-end gap-3 pt-2">
                            <button 
                                type="button"
                                onClick={() => setIsCreating(false)}
                                className="px-4 py-2 text-slate-400 hover:text-slate-200 text-sm transition-colors"
                            >
                                Cancel
                            </button>
                            <button 
                                type="submit"
                                className="px-4 py-2 bg-accent-blue text-white rounded-lg text-sm font-medium hover:bg-accent-blue/90 transition-colors"
                            >
                                Generate Credentials
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Success Preview (Generated Key) */}
            {newlyCreatedKey && (
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6 space-y-4 animate-in slide-in-from-top-4 duration-300">
                    <div className="flex items-center gap-3 text-emerald-400">
                        <CheckCircle2 className="w-6 h-6" />
                        <h3 className="text-lg font-semibold">API Key Generated Successfully</h3>
                    </div>
                    
                    <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 flex gap-3 text-yellow-500/90 text-sm">
                        <AlertCircle className="w-5 h-5 shrink-0" />
                        <p><strong>Important:</strong> Copy your API Secret now. For security, we won't show it again.</p>
                    </div>

                    <div className="grid gap-4">
                        <div className="space-y-1">
                            <label className="text-xs text-slate-500 uppercase font-semibold">API Key</label>
                            <div className="flex gap-2">
                                <code className="flex-1 bg-slate-950 border border-slate-800 p-2 rounded text-emerald-400 font-mono text-sm break-all">
                                    {newlyCreatedKey.api_key}
                                </code>
                                <button onClick={() => copyToClipboard(newlyCreatedKey.api_key, 'API Key')} className="p-2 bg-slate-800 rounded hover:bg-slate-700 text-slate-300">
                                    <Copy className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-slate-500 uppercase font-semibold">API Secret</label>
                            <div className="flex gap-2">
                                <code className="flex-1 bg-slate-950 border border-slate-800 p-2 rounded text-emerald-400 font-mono text-sm break-all">
                                    {newlyCreatedKey.api_secret}
                                </code>
                                <button onClick={() => copyToClipboard(newlyCreatedKey.api_secret || '', 'API Secret')} className="p-2 bg-slate-800 rounded hover:bg-slate-700 text-slate-300">
                                    <Copy className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="pt-4 flex justify-end">
                        <button 
                            onClick={() => {
                                setNewlyCreatedKey(null);
                                setIsCreating(false);
                            }}
                            className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
                        >
                            I've saved my credentials
                        </button>
                    </div>
                </div>
            )}

            {/* Keys Table */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-md">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-800/50 border-b border-slate-800">
                        <tr>
                            <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Name</th>
                            <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">API Key</th>
                            <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Created</th>
                            <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Last Used</th>
                            <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {keys.length > 0 ? (
                            keys.map((key) => (
                                <tr key={key.id} className="hover:bg-slate-800/30 transition-colors group">
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-slate-200">{key.name}</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <code className="text-xs text-slate-400 font-mono bg-slate-950 p-1 rounded border border-slate-800/50">
                                                {key.api_key.substring(0, 10)}...{key.api_key.substring(key.api_key.length - 4)}
                                            </code>
                                            <button onClick={() => copyToClipboard(key.api_key, 'API Key')} className="text-slate-500 hover:text-accent-blue opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Copy className="w-3 h-3" />
                                            </button>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-500">
                                        {format(new Date(key.created_at), 'MMM dd, yyyy')}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-500">
                                        {key.last_used_at ? format(new Date(key.last_used_at), 'MMM dd, HH:mm') : 'Never'}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button 
                                            onClick={() => handleDelete(key.id)}
                                            className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all"
                                            title="Revoke Key"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                                    No API Keys found. Create one to start trading via 3rd party tools.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
