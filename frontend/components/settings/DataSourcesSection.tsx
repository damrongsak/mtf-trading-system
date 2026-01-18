'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Plus, Trash2, Edit2, Database, AlertCircle, CheckCircle2 } from "lucide-react";
import { ConfirmationModal } from "@/components/ui/confirmation-modal";
import { getDataSources, createDataSource, updateDataSource, deleteDataSource, DataSource, DataSourceCreate, DataSourceType, DataSourceProvider } from '@/lib/api/data-sources';
import { BackfillModal } from './BackfillModal';
import { SymbolManagementModal } from './SymbolManagementModal';
import { List } from "lucide-react";

const TEMPLATES = {
    OANDA_LIVE: {
        token: "YOUR_LIVE_TOKEN",
        account_id: "YOUR_ACCOUNT_ID",
        hostname: "api-fxtrade.oanda.com",
        streaming_hostname: "stream-fxtrade.oanda.com"
    },
    OANDA_DEMO: {
        token: "YOUR_DEMO_TOKEN",
        account_id: "YOUR_ACCOUNT_ID",
        hostname: "api-fxpractice.oanda.com",
        streaming_hostname: "stream-fxpractice.oanda.com"
    },
    BINANCE_LIVE: {
        api_key: "YOUR_API_KEY",
        secret_key: "YOUR_SECRET_KEY",
        testnet: false,
        stream_url: "wss://stream.binance.com:9443/ws"
    },
    BINANCE_TESTNET: {
        api_key: "YOUR_TESTNET_API_KEY",
        secret_key: "YOUR_TESTNET_SECRET_KEY",
        testnet: true,
        stream_url: "wss://testnet.binance.vision/ws"
    },
    CTRADER_LIVE: {
        host: "live.ctraderapi.com",
        port: 5035,
        client_id: "YOUR_APP_ID",
        client_secret: "YOUR_SECRET",
        account_id: "YOUR_ACCOUNT_ID",
        token: "YOUR_ACCESS_TOKEN",
        refresh_token: "YOUR_REFRESH_TOKEN"
    },
    CTRADER_DEMO: {
        host: "demo.ctraderapi.com",
        port: 5035,
        client_id: "YOUR_APP_ID",
        client_secret: "YOUR_SECRET",
        account_id: "YOUR_ACCOUNT_ID",
        token: "YOUR_ACCESS_TOKEN",
        refresh_token: "YOUR_REFRESH_TOKEN"
    }
};

export function DataSourcesSection() {
    const [sources, setSources] = useState<DataSource[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Modal States
    const [isAdding, setIsAdding] = useState(false);
    const [editingSource, setEditingSource] = useState<DataSource | null>(null);
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    // Backfill Modal State
    const [backfillSource, setBackfillSource] = useState<DataSource | null>(null);
    const [manageSymbolsSource, setManageSymbolsSource] = useState<DataSource | null>(null);

    // Form State
    const [formData, setFormData] = useState<DataSourceCreate>({
        name: '',
        provider: 'OANDA',
        type: 'api',
        config_json: {},
        is_active: true
    });
    const [configString, setConfigString] = useState('{}');
    const [selectedTemplate, setSelectedTemplate] = useState<string | undefined>(undefined);

    const detectTemplate = (config: Record<string, unknown>): string | undefined => {
        if (!config || Object.keys(config).length === 0) return undefined;
        
        // Check for OANDA keys
        if ('token' in config && 'account_id' in config && 'hostname' in config && typeof config.hostname === 'string') {
            return config.hostname.includes('practice') ? 'OANDA_DEMO' : 'OANDA_LIVE';
        }
        
        // Check for Binance keys
        if ('api_key' in config && 'secret_key' in config && 'stream_url' in config) {
            return config.testnet ? 'BINANCE_TESTNET' : 'BINANCE_LIVE';
        }

        // Check for cTrader keys
        if ('client_id' in config && 'client_secret' in config) {
            return (config.host as string)?.includes('demo') ? 'CTRADER_DEMO' : 'CTRADER_LIVE';
        }
        
        return undefined;
    };

    useEffect(() => {
        fetchSources();
    }, []);

    const fetchSources = async () => {
        try {
            setLoading(true);
            const data = await getDataSources();
            setSources(data);
        } catch (err) {
            setError("Failed to load data sources");
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({ name: '', provider: 'OANDA', type: 'api', config_json: {}, is_active: true });
        setConfigString('{}');
        setEditingSource(null);
        setIsAdding(false);
        setError(null);
        setSelectedTemplate(undefined);
    };

    const handleEditClick = (source: DataSource) => {
        setEditingSource(source);
        setFormData({
            name: source.name,
            provider: (source.provider || 'OANDA') as DataSourceProvider,
            type: source.type.toLowerCase() as DataSourceType,
            config_json: source.config_json,
            is_active: source.is_active
        });
        setConfigString(JSON.stringify(source.config_json, null, 2));
        setSelectedTemplate(detectTemplate(source.config_json));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);
        setSuccess(null);

        try {
            // Validate JSON
            let parsedConfig = {};
            try {
                parsedConfig = JSON.parse(configString);
            } catch (e) {
                throw new Error("Invalid JSON configuration");
            }

            const payload = { ...formData, config_json: parsedConfig };

            if (editingSource) {
                await updateDataSource(editingSource.id, payload);
                setSuccess("Data Source updated successfully");
            } else {
                await createDataSource(payload);
                setSuccess("Data Source created successfully");
            }

            await fetchSources();
            resetForm();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Operation failed");
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async () => {
        if (!deleteId) return;
        setSubmitting(true);
        try {
            await deleteDataSource(deleteId);
            setSources(prev => prev.filter(s => s.id !== deleteId));
            setSuccess("Data Source deleted");
        } catch (err) {
            setError("Failed to delete data source");
        } finally {
            setSubmitting(false);
            setDeleteId(null);
        }
    };

    const handleToggleActive = async (source: DataSource, checked: boolean) => {
        try {
            // Optimistic update
            setSources(prev => prev.map(s => s.id === source.id ? { ...s, is_active: checked } : s));
            await updateDataSource(source.id, { is_active: checked });
        } catch (err) {
            // Revert on error
            setSources(prev => prev.map(s => s.id === source.id ? { ...s, is_active: !checked } : s));
            setError("Failed to update status");
        }
    };

    return (
        <div className="space-y-6">
            <ConfirmationModal
                isOpen={!!deleteId}
                onClose={() => setDeleteId(null)}
                onConfirm={handleDelete}
                title="Delete Data Source"
                message="Are you sure? This might break strategies depending on this source."
                confirmText="Delete"
                isLoading={submitting}
                variant="danger"
            />

            {backfillSource && (
                <BackfillModal 
                    isOpen={!!backfillSource}
                    onClose={() => setBackfillSource(null)}
                    dataSourceId={backfillSource.id}
                    dataSourceName={backfillSource.name}
                />
            )}

            {manageSymbolsSource && (
                <SymbolManagementModal
                    isOpen={!!manageSymbolsSource}
                    onClose={() => setManageSymbolsSource(null)}
                    brokerName={manageSymbolsSource.name}
                    dataSourceId={manageSymbolsSource.id}
                />
            )}

            {(isAdding || editingSource) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <Card className="w-full max-w-lg bg-gray-900 border-gray-800">
                        <CardHeader>
                            <CardTitle>{editingSource ? 'Edit Data Source' : 'Add Data Source'}</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Provider</Label>
                                        <Select 
                                            value={formData.provider} 
                                            onValueChange={(val) => setFormData({...formData, provider: val as DataSourceProvider})}
                                        >
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="OANDA">OANDA</SelectItem>
                                                <SelectItem value="BINANCE">Binance</SelectItem>
                                                <SelectItem value="CTRADER">cTrader</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Category</Label>
                                        <Select 
                                            value={formData.type} 
                                            onValueChange={(val) => setFormData({...formData, type: val as DataSourceType})}
                                        >
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="api">API</SelectItem>
                                                <SelectItem value="csv">CSV File</SelectItem>
                                                <SelectItem value="db">Database</SelectItem>
                                                <SelectItem value="websocket">Websocket</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label>Name (Alias)</Label>
                                    <Input 
                                        value={formData.name}
                                        onChange={e => setFormData({...formData, name: e.target.value})}
                                        placeholder="e.g. My Oanda Account"
                                        required
                                    />
                                </div>

                                <div className="space-y-4">
                                    <div className="flex flex-col space-y-2">
                                        <Label>Configuration Preset (Optional)</Label>
                                        <Select 
                                            value={selectedTemplate || ''}
                                            onValueChange={(val) => {
                                                setSelectedTemplate(val);
                                                if (val && TEMPLATES[val as keyof typeof TEMPLATES]) {
                                                    setConfigString(JSON.stringify(TEMPLATES[val as keyof typeof TEMPLATES], null, 2));
                                                }
                                            }}
                                        >
                                            <SelectTrigger className="w-full">
                                                <SelectValue placeholder="Select a configuration template..." />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="OANDA_LIVE">OANDA Live</SelectItem>
                                                <SelectItem value="OANDA_DEMO">OANDA Demo</SelectItem>
                                                <SelectItem value="BINANCE_LIVE">Binance Live</SelectItem>
                                                <SelectItem value="BINANCE_TESTNET">Binance Testnet</SelectItem>
                                                <SelectItem value="CTRADER_LIVE">cTrader Live</SelectItem>
                                                <SelectItem value="CTRADER_DEMO">cTrader Demo</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="space-y-2">
                                        <Label>Configuration (JSON)</Label>
                                        <Textarea 
                                            value={configString}
                                            onChange={e => setConfigString(e.target.value)}
                                            className="font-mono text-xs h-32 bg-gray-950/50"
                                            placeholder='{"api_url": "...", "api_key": "..."}'
                                        />
                                        <p className="text-xs text-gray-500">
                                            Enter connection details in valid JSON format.
                                        </p>
                                    </div>
                                </div>

                                {error && (
                                    <div className="text-red-400 text-sm flex items-center gap-2">
                                        <AlertCircle className="h-4 w-4" /> {error}
                                    </div>
                                )}

                                <div className="flex justify-end gap-2 mt-4">
                                    <Button type="button" variant="ghost" onClick={resetForm}>Cancel</Button>
                                    <Button type="submit" disabled={submitting}>
                                        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Save
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>
                </div>
            )}

            <Card className="bg-gray-950/50 backdrop-blur-sm border-gray-800">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle>Data Sources</CardTitle>
                        <CardDescription>Configure global market data providers</CardDescription>
                    </div>
                    {!isAdding && !editingSource && (
                        <Button onClick={() => setIsAdding(true)} className="gap-2">
                            <Plus className="h-4 w-4" /> Add Source
                        </Button>
                    )}
                </CardHeader>
                <CardContent>
                    {success && (
                        <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded text-green-400 text-sm flex items-center gap-2">
                            <CheckCircle2 className="h-4 w-4" /> {success}
                        </div>
                    )}
                    
                    {loading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
                        </div>
                    ) : sources.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            No data sources found.
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {sources.map(source => (
                                <div key={source.id} className="flex items-center justify-between p-4 rounded-lg border border-gray-800 bg-gray-900/30 hover:border-gray-700 transition-colors">
                                    <div className="flex items-center gap-4">
                                        <div className="h-10 w-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                                            <Database className="h-5 w-5" />
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <h4 className="font-medium text-gray-200">{source.name}</h4>
                                                <Badge variant="default" className="bg-indigo-500/20 text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/30">{source.provider}</Badge>
                                                <Badge variant="outline" className="text-xs">{source.type}</Badge>
                                                {!source.is_active && (
                                                    <Badge variant="secondary" className="text-xs bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-amber-500/20">Disabled</Badge>
                                                )}
                                            </div>
                                            <p className="text-xs text-gray-500 font-mono mt-1 w-64 truncate">
                                                {JSON.stringify(source.config_json)}
                                            </p>
                                        </div>
                                    </div>
                                    
                                    <div className="flex items-center gap-4">
                                        <div className="flex items-center gap-2 mr-2">
                                            <Label htmlFor={`source-${source.id}`} className="text-xs text-gray-500 cursor-pointer">
                                                {source.is_active ? 'Active' : 'Disabled'}
                                            </Label>
                                            <Switch 
                                                id={`source-${source.id}`}
                                                checked={source.is_active}
                                                onCheckedChange={(c) => handleToggleActive(source, c)}
                                            />
                                        </div>
                                        <div className="h-4 w-px bg-gray-800" />
                                        <Button variant="ghost" size="icon" className="text-gray-500 hover:text-green-400" onClick={() => setBackfillSource(source)} title="Import Data">
                                            <Database className="h-4 w-4" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="text-gray-500 hover:text-indigo-400" onClick={() => setManageSymbolsSource(source)} title="Manage Symbols">
                                            <List className="h-4 w-4" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="text-gray-500 hover:text-blue-400" onClick={() => handleEditClick(source)}>
                                            <Edit2 className="h-4 w-4" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="text-gray-500 hover:text-red-400" onClick={() => setDeleteId(source.id)}>
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
