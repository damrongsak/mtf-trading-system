'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Loader2, Search, AlertCircle, CheckCircle2, Settings2, Save, X, RefreshCw } from "lucide-react";
import { getBrokerSymbols, updateSymbol, fetchDataSourceSymbols, createSymbol, fetchSymbolDetails } from '@/lib/api/data-sources';
import { MarketSymbol } from "@/lib/api/types";
import { logger } from "@/lib/api/app-logger";

interface SymbolManagementModalProps {
    isOpen: boolean;
    onClose: () => void;
    brokerName: string;
    dataSourceId: string;
}

export function SymbolManagementModal({ isOpen, onClose, brokerName, dataSourceId }: SymbolManagementModalProps) {
    const [symbols, setSymbols] = useState<MarketSymbol[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [editingSymbolId, setEditingSymbolId] = useState<string | null>(null);
    const [editDetails, setEditDetails] = useState<string>('');
    const [loadingDetails, setLoadingDetails] = useState(false);

    useEffect(() => {
        if (isOpen && brokerName) {
            fetchSymbols();
        }
    }, [isOpen, brokerName]);

    const fetchSymbols = async () => {
        try {
            setLoading(true);
            setError(null);
            
            logger.debug(`[SymbolManagement] Fetching symbols for broker: ${brokerName}, dataSourceId: ${dataSourceId}`);
            
            // 1. Fetch Active Symbols from DB
            logger.debug(`[SymbolManagement] Fetching active symbols from DB...`);
            const activeSymbols = await getBrokerSymbols(brokerName);
            logger.debug(`[SymbolManagement] Fetched ${activeSymbols?.length || 0} active symbols from DB`);
            
            // 2. Fetch Available Symbols from Provider (may fail if not supported)
            let availableSymbols: string[] = [];
            try {
                logger.debug(`[SymbolManagement] Fetching available symbols from provider...`);
                availableSymbols = await fetchDataSourceSymbols(dataSourceId);
                logger.debug(`[SymbolManagement] Fetched ${availableSymbols?.length || 0} symbols from provider`);
            } catch (e) {
                logger.warn(`[SymbolManagement] Failed to fetch provider symbols:`, e);
                // This is expected for some providers, continue with just active symbols
            }

            // 3. Merge
            logger.debug(`[SymbolManagement] Merging symbols...`);
            const activeMap = new Map((activeSymbols || []).map(s => [s.symbol, s]));
            const merged: MarketSymbol[] = [...(activeSymbols || [])];

            (availableSymbols || []).forEach(sym => {
                if (!activeMap.has(sym)) {
                    merged.push({
                        id: `TEMP_${sym}`,
                        symbol: sym,
                        is_active: false,
                        data_source_id: dataSourceId,
                        details: {}
                    } as MarketSymbol);
                }
            });

            // Sort alphabetically
            merged.sort((a, b) => a.symbol.localeCompare(b.symbol));
            logger.debug(`[SymbolManagement] Successfully merged ${merged.length} total symbols`);
            setSymbols(merged);

        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Unknown error";
            logger.error(`[SymbolManagement] Failed to load symbols:`, err);
            setError(`Failed to load symbols: ${errorMessage}`);
        } finally {
            setLoading(false);
        }
    };

    const handleToggle = async (symbol: MarketSymbol) => {
        const originalState = symbol.is_active;
        // Optimistic update
        setSymbols(prev => prev.map(s => s.id === symbol.id ? { ...s, is_active: !originalState } : s));
        
        try {
            if (symbol.id.startsWith("TEMP_")) {
                // Create logic
                const newSymbol = await createSymbol(brokerName, symbol.symbol);
                // Update state with real ID
                setSymbols(prev => prev.map(s => s.symbol === symbol.symbol ? newSymbol : s));
                setSuccessMessage(`Activated ${symbol.symbol}`);
            } else {
                // Update logic
                await updateSymbol(symbol.id, { is_active: !originalState });
                setSuccessMessage(`Updated ${symbol.symbol}`);
            }
            setTimeout(() => setSuccessMessage(null), 2000);
        } catch (err) {
            // Revert
            setSymbols(prev => prev.map(s => s.id === symbol.id ? { ...s, is_active: originalState } : s));
            setError(`Failed to update ${symbol.symbol}`);
        }
    };

    const startEditing = (symbol: MarketSymbol) => {
        setEditingSymbolId(symbol.id);
        setEditDetails(JSON.stringify(symbol.details || {}, null, 2));
    };

    const loadDetails = async (symbol: MarketSymbol) => {
        try {
            setLoadingDetails(true);
            const details = await fetchSymbolDetails(symbol.symbol);
            setEditDetails(JSON.stringify(details, null, 2));
            setSuccessMessage("Details loaded from Broker");
            setTimeout(() => setSuccessMessage(null), 2000);
        } catch (err) {
            setError("Failed to load details from Broker");
        } finally {
            setLoadingDetails(false);
        }
    };

    const saveDetails = async (symbol: MarketSymbol) => {
        try {
            const parsedDetails = JSON.parse(editDetails);
            await updateSymbol(symbol.id, { details: parsedDetails });
            setSymbols(prev => prev.map(s => s.id === symbol.id ? { ...s, details: parsedDetails } : s));
            setEditingSymbolId(null);
            setSuccessMessage(`Saved details for ${symbol.symbol}`);
            setTimeout(() => setSuccessMessage(null), 2000);
        } catch (err) {
            setError("Invalid JSON format");
        }
    };

    const filteredSymbols = symbols.filter(s => 
        s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) || 
        (s.display_name && s.display_name.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="bg-gray-900 border-gray-800 max-w-2xl max-h-[90vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>Manage Symbols: {brokerName}</DialogTitle>
                    <DialogDescription>
                        Enable symbols and configure instrument details (Pip Location, Margin, etc.).
                    </DialogDescription>
                </DialogHeader>

                <div className="flex items-center gap-2 mb-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-500" />
                        <Input
                            placeholder="Search symbols..."
                            className="pl-8 bg-gray-950/50 border-gray-800"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm flex items-center gap-2">
                        <AlertCircle className="h-4 w-4" /> {error}
                    </div>
                )}
                
                {successMessage && (
                    <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded text-green-400 text-sm flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4" /> {successMessage}
                    </div>
                )}

                <div className="flex-1 overflow-y-auto pr-2 space-y-2 min-h-[300px]">
                    {loading ? (
                        <div className="flex justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
                        </div>
                    ) : filteredSymbols.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                            No symbols found.
                        </div>
                    ) : (
                        filteredSymbols.map(symbol => (
                            <div key={symbol.id} className="flex flex-col p-3 rounded-lg border border-gray-800 bg-gray-950/30 hover:bg-gray-900/50 transition-colors gap-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="flex flex-col">
                                            <span className="font-medium text-gray-200">{symbol.symbol}</span>
                                            {symbol.display_name && (
                                                <span className="text-xs text-gray-500">{symbol.display_name}</span>
                                            )}
                                        </div>
                                        <Badge variant="outline" className={`text-[10px] ${symbol.is_active ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-gray-800 text-gray-500'}`}>
                                            {symbol.is_active ? 'ACTIVE' : 'INACTIVE'}
                                        </Badge>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        {symbol.is_active && !symbol.id.startsWith("TEMP_") && (
                                            <Button 
                                                variant="ghost" 
                                                size="icon" 
                                                className="h-8 w-8 text-gray-400 hover:text-white"
                                                onClick={() => startEditing(symbol)}
                                            >
                                                <Settings2 className="h-4 w-4" />
                                            </Button>
                                        )}
                                        <Switch
                                            checked={symbol.is_active}
                                            onCheckedChange={() => handleToggle(symbol)}
                                        />
                                    </div>
                                </div>

                                {editingSymbolId === symbol.id && (
                                    <div className="mt-2 p-3 bg-black/40 rounded border border-gray-800 space-y-3">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs font-semibold text-gray-400">INSTRUMENT DETAILS (JSON)</span>
                                            <div className="flex gap-2">
                                                <Button 
                                                    size="sm" 
                                                    variant="outline" 
                                                    className="h-7 text-xs border-gray-700 bg-gray-900 hover:bg-gray-800 text-gray-300" 
                                                    onClick={() => loadDetails(symbol)}
                                                    disabled={loadingDetails}
                                                >
                                                    {loadingDetails ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <RefreshCw className="h-3 w-3 mr-1" />}
                                                    Load from Broker
                                                </Button>
                                                <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setEditingSymbolId(null)}>
                                                    <X className="h-3 w-3 mr-1" /> Cancel
                                                </Button>
                                                <Button size="sm" className="h-7 text-xs bg-blue-600 hover:bg-blue-700" onClick={() => saveDetails(symbol)}>
                                                    <Save className="h-3 w-3 mr-1" /> Save
                                                </Button>
                                            </div>
                                        </div>
                                        <textarea
                                            className="w-full h-32 bg-gray-950 border border-gray-800 rounded p-2 text-xs font-mono text-blue-400 focus:outline-none focus:border-blue-500"
                                            value={editDetails}
                                            onChange={(e) => setEditDetails(e.target.value)}
                                        />
                                        <p className="text-[10px] text-gray-500">
                                            Example: {'{ "pipLocation": -4, "marginRate": "0.02" }'}
                                        </p>
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>

                <div className="flex justify-end pt-4 border-t border-gray-800">
                    <Button onClick={onClose}>Close</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
