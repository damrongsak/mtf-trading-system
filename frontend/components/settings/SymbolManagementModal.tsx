'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Loader2, Search, AlertCircle, CheckCircle2 } from "lucide-react";
import { getBrokerSymbols, updateSymbolStatus, MarketSymbol } from '@/lib/api/data-sources';

interface SymbolManagementModalProps {
    isOpen: boolean;
    onClose: () => void;
    brokerName: string;
}

export function SymbolManagementModal({ isOpen, onClose, brokerName }: SymbolManagementModalProps) {
    const [symbols, setSymbols] = useState<MarketSymbol[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && brokerName) {
            fetchSymbols();
        }
    }, [isOpen, brokerName]);

    const fetchSymbols = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getBrokerSymbols(brokerName);
            setSymbols(data);
        } catch (err) {
            setError("Failed to load symbols");
        } finally {
            setLoading(false);
        }
    };

    const handleToggle = async (symbol: MarketSymbol) => {
        // Optimistic update
        const originalState = symbol.is_active;
        setSymbols(prev => prev.map(s => s.id === symbol.id ? { ...s, is_active: !originalState } : s));
        
        try {
            await updateSymbolStatus(symbol.id, !originalState);
            setSuccessMessage(`Updated ${symbol.symbol}`);
            setTimeout(() => setSuccessMessage(null), 2000);
        } catch (err) {
            // Revert
            setSymbols(prev => prev.map(s => s.id === symbol.id ? { ...s, is_active: originalState } : s));
            setError(`Failed to update ${symbol.symbol}`);
        }
    };

    const filteredSymbols = symbols.filter(s => 
        s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) || 
        (s.display_name && s.display_name.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="bg-gray-900 border-gray-800 max-w-2xl max-h-[80vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>Manage Symbols: {brokerName}</DialogTitle>
                    <DialogDescription>
                        Enable or disable symbols for data collection and analysis.
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
                            <div key={symbol.id} className="flex items-center justify-between p-3 rounded-lg border border-gray-800 bg-gray-950/30 hover:bg-gray-900/50 transition-colors">
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
                                <Switch
                                    checked={symbol.is_active}
                                    onCheckedChange={() => handleToggle(symbol)}
                                />
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
