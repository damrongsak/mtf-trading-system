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
    
    const [hooks, setHooks] = useState<{ actions: { tag: string; callbacks: string[] }[], filters: { tag: string; callbacks: string[] }[] } | null>(null);
    const [showHooks, setShowHooks] = useState(false);
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    const fetchPlugins = async () => {
        try {
            setLoading(true);
            const data = await pluginsApi.list();
            setPlugins(data);
        } catch (err) {
            setError("Failed to fetch plugins");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPlugins();
    }, []);

    const handleToggle = async (plugin: Plugin) => {
        try {
            if (plugin.is_active) {
                await pluginsApi.deactivate(plugin.id);
            } else {
                await pluginsApi.activate(plugin.id);
            }
            fetchPlugins();
        } catch (err) {
            setError("Toggle failed");
        }
    };

    const openConfig = (plugin: Plugin) => {
        setConfigPlugin(plugin);
        setConfigJson(JSON.stringify(plugin.base_config_schema || {}, null, 2));
    };

    const handleSaveConfig = async () => {
        if (!configPlugin) return;
        setSaving(true);
        try {
            const overrides = JSON.parse(configJson);
            await pluginsApi.updateConfig(configPlugin.id, { config_overrides: overrides });
            setSuccess("Configuration saved");
            setConfigPlugin(null);
            fetchPlugins();
        } catch (err) {
            setError("Invalid JSON or update failed");
        } finally {
            setSaving(false);
        }
    };

    const handleSync = async () => {
        try {
            setLoading(true);
            await pluginsApi.sync();
            await fetchPlugins();
            setSuccess("Plugins synced with file system");
        } catch {
            setError("Sync failed");
        } finally {
            setLoading(false);
        }
    };

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        try {
            setLoading(true);
            await pluginsApi.upload(file);
            await fetchPlugins();
            setSuccess(`Plugin ${file.name} uploaded successfully`);
        } catch {
            setError("Upload failed");
        } finally {
            setLoading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleViewHooks = async () => {
        try {
            const data = await pluginsApi.getHooks();
            setHooks(data);
            setShowHooks(true);
        } catch {
            setError("Failed to fetch hooks");
        }
    };

    if (loading && !plugins.length) return <div className="p-8 text-center text-slate-400">Loading plugins...</div>;

    return (
        <Card className="bg-[#1E293B] border-slate-700">
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Plugin Engine</CardTitle>
                    <CardDescription>Manage extensions for Alpha, Risk, and Execution.</CardDescription>
                </div>
                <div className="flex gap-2">
                    <input 
                        type="file" 
                        ref={fileInputRef} 
                        className="hidden" 
                        accept=".zip" 
                        onChange={handleFileChange} 
                    />
                    <Button variant="outline" size="sm" onClick={handleViewHooks}>
                        View Hooks
                    </Button>
                    <Button variant="secondary" size="sm" onClick={handleSync}>
                        Sync from Disk
                    </Button>
                    <Button size="sm" onClick={handleUploadClick} className="bg-blue-600 hover:bg-blue-700">
                        Install Plugin
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-sm flex justify-between items-center">
                            {error}
                            <button onClick={() => setError(null)} className="hover:text-white">✕</button>
                        </div>
                    )}
                    {success && (
                        <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-md text-green-400 text-sm flex justify-between items-center">
                            {success}
                            <button onClick={() => setSuccess(null)} className="hover:text-white">✕</button>
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

            {/* Config Dialog */}
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

            {/* Hooks Dialog */}
            <Dialog open={showHooks} onOpenChange={setShowHooks}>
                <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-2xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>System Hook Registry</DialogTitle>
                        <DialogDescription>
                            Active Actions and Filters registered in the Strategy Core.
                        </DialogDescription>
                    </DialogHeader>
                    
                    <div className="space-y-6 pt-4">
                        <div>
                            <h4 className="text-blue-400 font-semibold mb-2 flex items-center gap-2">
                                ⚡ Actions (Events)
                            </h4>
                            {hooks?.actions && hooks.actions.length > 0 ? (
                                <div className="space-y-3">
                                    {hooks.actions.map((h: { tag: string; callbacks: string[] }) => (
                                        <div key={h.tag} className="bg-slate-950 p-3 rounded border border-slate-800">
                                            <div className="font-mono text-sm text-yellow-500 font-bold mb-1">{h.tag}</div>
                                            <div className="pl-4 space-y-1">
                                                {h.callbacks.map((cb: string, i: number) => (
                                                    <div key={i} className="text-xs text-slate-400 font-mono">
                                                        ↳ {cb}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-slate-500 text-sm">No actions registered.</p>
                            )}
                        </div>

                        <div>
                            <h4 className="text-purple-400 font-semibold mb-2 flex items-center gap-2">
                                🛡️ Filters (Pipelines)
                            </h4>
                            {hooks?.filters && hooks.filters.length > 0 ? (
                                <div className="space-y-3">
                                    {hooks.filters.map((h: { tag: string; callbacks: string[] }) => (
                                        <div key={h.tag} className="bg-slate-950 p-3 rounded border border-slate-800">
                                            <div className="font-mono text-sm text-green-500 font-bold mb-1">{h.tag}</div>
                                            <div className="pl-4 space-y-1">
                                                {h.callbacks.map((cb: string, i: number) => (
                                                    <div key={i} className="text-xs text-slate-400 font-mono">
                                                        ↳ {cb}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-slate-500 text-sm">No filters registered.</p>
                            )}
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

        </Card>
    );
}
