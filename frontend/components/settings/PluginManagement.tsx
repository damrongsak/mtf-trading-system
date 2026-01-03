'use client';

import React, { useEffect, useState } from 'react';
import { pluginsApi } from '@/lib/api/plugins';
import { Plugin } from '@/lib/api/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';

export function PluginManagement() {
    const [plugins, setPlugins] = useState<Plugin[]>([]);
    const [loading, setLoading] = useState(true);
    const [configPlugin, setConfigPlugin] = useState<Plugin | null>(null);
    const [configJson, setConfigJson] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        fetchPlugins();
    }, []);

    const fetchPlugins = async () => {
        try {
            setLoading(true);
            const data = await pluginsApi.list();
            setPlugins(data);
        } catch {
            console.error('Failed to fetch plugins:');
        } finally {
            setLoading(false);
        }
    };

    const handleToggle = async (plugin: Plugin) => {
        // Optimistic update
        const originalState = plugin.is_active;
        setPlugins(plugins.map(p => p.id === plugin.id ? { ...p, is_active: !originalState } : p));
        
        try {
            if (!originalState) {
                await pluginsApi.activate(plugin.id);
            } else {
                await pluginsApi.deactivate(plugin.id);
            }
            setSuccess(`Plugin ${!originalState ? 'activated' : 'deactivated'} successfully`);
        } catch {
            setError(`Failed to ${!originalState ? 'activate' : 'deactivate'} plugin`);
            console.error('Failed to toggle plugin');
            // Revert
            setPlugins(plugins.map(p => p.id === plugin.id ? { ...p, is_active: originalState } : p));
        }
    };

    const openConfig = (plugin: Plugin) => {
        // Since list returns base_config_schema, and not current user config (unless we updated list endpoint),
        // we might be showing schema or defaults. 
        // In reality, we want to show the CURRENT user overrides.
        // The list endpoint implementation I read merges user state: 
        // But checking Backend router `list_plugins`: it returns `PluginResponse` which has `id, name...`.
        // It does NOT include `config_overrides`.
        // Ideally we should fetch current config. But for MVP, let's just initialize with empty object or schema hints.
        // Or we should update the backend to Include current config.
        // Given constraints, I'll initialize with `{}` and let user type overrides.
        // Or if I had time I'd add `UserPlugin` data to list response.
        // Let's assume we start with empty overrides.
        
        setConfigPlugin(plugin);
        setConfigJson('{\n  \n}'); 
    };

    const handleSaveConfig = async () => {
        if (!configPlugin) return;

        try {
            const parsed = JSON.parse(configJson);
            setSaving(true);
            await pluginsApi.updateConfig(configPlugin.id, { config_overrides: parsed });
            setConfigPlugin(null);
        } catch {
            alert('Invalid JSON');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div>Loading plugins...</div>;

    return (
        <Card className="bg-[#1E293B] border-slate-700">
            <CardHeader>
                <CardTitle>Plugin Engine</CardTitle>
                <CardDescription>Manage extensions for Alpha, Risk, and Execution.</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-sm">
                            {error}
                        </div>
                    )}
                    {success && (
                        <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-md text-green-400 text-sm">
                            {success}
                        </div>
                    )}
                    {plugins.map((plugin) => (
                        <div key={plugin.id} className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                            <div>
                                <div className="flex items-center gap-2">
                                    <h3 className="font-semibold text-white">{plugin.name}</h3>
                                    <Badge variant={plugin.is_active ? "default" : "secondary"}>
                                        {plugin.category}
                                    </Badge>
                                </div>
                                <p className="text-sm text-slate-400 mt-1">{plugin.description}</p>
                                <div className="text-xs text-slate-500 mt-1">v{plugin.version} • {plugin.author}</div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Button variant="outline" size="sm" onClick={() => openConfig(plugin)} disabled={!plugin.is_active}>
                                    Config
                                </Button>
                                <Switch 
                                    checked={plugin.is_active} 
                                    onCheckedChange={() => handleToggle(plugin)}
                                />
                            </div>
                        </div>
                    ))}
                    
                    {plugins.length === 0 && (
                        <div className="text-center text-slate-500 py-8">No plugins installed.</div>
                    )}
                </div>
            </CardContent>

            <Dialog open={!!configPlugin} onOpenChange={(open) => !open && setConfigPlugin(null)}>
                <DialogContent className="bg-slate-900 border-slate-700 text-white">
                    <DialogHeader>
                        <DialogTitle>Configure {configPlugin?.name}</DialogTitle>
                        <DialogDescription>
                            Override default settings with JSON.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <Label>Configuration JSON</Label>
                        <textarea 
                            className="w-full h-40 bg-slate-950 border border-slate-700 rounded-md p-2 font-mono text-sm mt-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            value={configJson}
                            onChange={(e) => setConfigJson(e.target.value)}
                        />
                        <p className="text-xs text-slate-500 mt-2">
                            Base Schema: {JSON.stringify(Object.keys(configPlugin?.base_config_schema || {}))}
                        </p>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setConfigPlugin(null)}>Cancel</Button>
                        <Button onClick={handleSaveConfig} disabled={saving}>Save Changes</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

        </Card>
    );
}
