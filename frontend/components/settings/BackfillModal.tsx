import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, RefreshCw } from "lucide-react";
import { triggerBackfill, fetchDataSourceSymbols } from '@/lib/api/data-sources';
import { toast } from 'sonner';

interface BackfillModalProps {
    isOpen: boolean;
    onClose: () => void;
    dataSourceId: string;
    dataSourceName: string;
}

export function BackfillModal({ isOpen, onClose, dataSourceId, dataSourceName }: BackfillModalProps) {
    const [symbol, setSymbol] = useState('');
    const [timeframe, setTimeframe] = useState('H1');
    const [count, setCount] = useState('500');
    const [loading, setLoading] = useState(false);
    
    const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
    const [fetchingSymbols, setFetchingSymbols] = useState(false);

    useEffect(() => {
        if (isOpen && dataSourceId) {
            loadSymbols();
        }
    }, [isOpen, dataSourceId]);

    const loadSymbols = async () => {
        setFetchingSymbols(true);
        try {
            const symbols = await fetchDataSourceSymbols(dataSourceId);
            setAvailableSymbols(symbols);
        } catch (error) {
            console.error("Failed to fetch symbols", error);
            // Don't show error to user immediately, just let them type manually
        } finally {
            setFetchingSymbols(false);
        }
    };

    const handleBackfill = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await triggerBackfill(dataSourceId, {
                symbol,
                timeframe,
                count: parseInt(count)
            });
            toast.success(`Backfill started for ${symbol}`);
            onClose();
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Failed to start backfill");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="bg-gray-900 border-gray-800 text-gray-100">
                <DialogHeader>
                    <DialogTitle>Backfill Data: {dataSourceName}</DialogTitle>
                    <DialogDescription>
                        Trigger a historical data import from this source.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleBackfill} className="space-y-4">
                    <div className="space-y-2">
                        <Label>Symbol</Label>
                        <div className="relative">
                            <div className="flex gap-2">
                                <div className="relative flex-1">
                                    <Input 
                                        value={symbol}
                                        onChange={(e) => setSymbol(e.target.value)}
                                        placeholder="e.g. XAU_USD"
                                        list="symbol-suggestions"
                                        required
                                    />
                                    <datalist id="symbol-suggestions">
                                        {availableSymbols.map(s => (
                                            <option key={s} value={s} />
                                        ))}
                                    </datalist>
                                </div>
                                <Button 
                                    type="button"
                                    variant="outline" 
                                    size="icon"
                                    onClick={loadSymbols}
                                    className="shrink-0"
                                    disabled={fetchingSymbols}
                                    title="Reload Symbols"
                                >
                                    {fetchingSymbols ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                                </Button>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                                {availableSymbols.length > 0 
                                    ? `Found ${availableSymbols.length} symbols from source.`
                                    : "Type manually or click refresh to fetch available symbols."
                                }
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Timeframe</Label>
                            <Select value={timeframe} onValueChange={setTimeframe}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="M1">M1</SelectItem>
                                    <SelectItem value="M5">M5</SelectItem>
                                    <SelectItem value="M15">M15</SelectItem>
                                    <SelectItem value="M30">M30</SelectItem>
                                    <SelectItem value="H1">H1</SelectItem>
                                    <SelectItem value="H4">H4</SelectItem>
                                    <SelectItem value="D">Daily</SelectItem>
                                    <SelectItem value="W">Weekly</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Count</Label>
                            <Input 
                                type="number" 
                                value={count}
                                onChange={(e) => setCount(e.target.value)}
                                min={1}
                                max={5000}
                                required
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                        <Button type="submit" disabled={loading || !symbol}>
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Start Backfill
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
