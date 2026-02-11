'use client';

import React, { useEffect, useState } from 'react';
import { 
    Table, 
    TableBody, 
    TableCell, 
    TableHead, 
    TableHeader, 
    TableRow 
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useLiveFeatures, FeatureUpdate } from '@/lib/hooks/useLiveFeatures';
import { getMarketFeatures, MarketFeature } from '@/lib/api/data';
import { logger } from '@/lib/api/app-logger';
import { ArrowUp, ArrowDown, Minus, RefreshCw } from 'lucide-react';

export const FeatureMatrix: React.FC = () => {
    const [initialFeatures, setInitialFeatures] = useState<Record<string, MarketFeature>>({});
    const [isLoading, setIsLoading] = useState(true);
    
    // Subscribe to all symbols (or a selection)
    // For the matrix, we'll try to get all currently cached symbols
    const { features: liveFeatures, connected } = useLiveFeatures(['XAUUSD', 'EURUSD', 'GBPUSD', 'BTCUSD', 'ETHUSD']);

    useEffect(() => {
        const fetchInitial = async () => {
            try {
                const data = await getMarketFeatures();
                const mapped: Record<string, MarketFeature> = {};
                data.forEach(f => {
                    mapped[f.symbol] = f;
                });
                setInitialFeatures(mapped);
            } catch (error) {
                logger.error("Failed to fetch initial features", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchInitial();
    }, []);

    // Merge initial and live features
    const allSymbols = Array.from(new Set([
        ...Object.keys(initialFeatures),
        ...Object.keys(liveFeatures)
    ])).sort();

    const getFeature = (symbol: string): any => {
        return liveFeatures[symbol] || initialFeatures[symbol] || {};
    };

    const renderRSI = (rsi: number | null | undefined) => {
        if (rsi === null || rsi === undefined) return <Minus size={14} className="text-gray-600" />;
        
        let color = "text-gray-400";
        if (rsi >= 70) color = "text-red-500 font-bold";
        if (rsi <= 30) color = "text-green-500 font-bold";
        
        return <span className={color}>{rsi.toFixed(2)}</span>;
    };

    const renderTrend = (ema_short?: number | null, ema_long?: number | null) => {
        if (!ema_short || !ema_long) return <Minus size={14} className="text-gray-600" />;
        
        if (ema_short > ema_long) {
            return <Badge className="bg-green-500/20 text-green-500 border-green-500/30 flex gap-1 items-center">
                <ArrowUp size={12} /> Bullish
            </Badge>;
        }
        return <Badge className="bg-red-500/20 text-red-500 border-red-500/30 flex gap-1 items-center">
            <ArrowDown size={12} /> Bearish
        </Badge>;
    };

    const formatPrice = (price?: number | null) => {
        if (!price) return '-';
        return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 });
    };

    if (isLoading && allSymbols.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 space-y-4">
                <RefreshCw className="animate-spin text-accent-blue" size={32} />
                <p className="text-gray-400">Loading Market Features...</p>
            </div>
        );
    }

    return (
        <Card className="bg-gray-950 border-gray-800 shadow-2xl">
            <CardHeader className="flex flex-row items-center justify-between border-b border-gray-800">
                <div>
                    <CardTitle className="text-xl font-bold text-white tracking-tight">Market Feature Matrix</CardTitle>
                    <p className="text-xs text-gray-500 mt-1">Real-time quantitative technical indicators via ECST Read Model</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-red-500'}`} />
                    <span className="text-xs text-gray-400 uppercase font-bold tracking-widest">
                        {connected ? 'Live' : 'Disconnected'}
                    </span>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <div className="overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow className="border-gray-800 hover:bg-transparent">
                                <TableHead className="text-gray-400 font-bold uppercase text-[10px] tracking-widest pl-6 py-4">Symbol</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase text-[10px] tracking-widest py-4">Price</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase text-[10px] tracking-widest py-4">RSI(14)</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase text-[10px] tracking-widest py-4">ATR(14)</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase text-[10px] tracking-widest py-4 text-center">Trend (9/20)</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase text-[10px] tracking-widest py-4 text-center">Macro (50/200)</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase text-[10px] tracking-widest py-4 text-center">SMC Structure</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase text-[10px] tracking-widest pr-6 py-4 text-right">Last Sync</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {allSymbols.map(symbol => {
                                const f = getFeature(symbol);
                                return (
                                    <TableRow key={symbol} className="border-gray-800 hover:bg-gray-900/40 transition-colors group">
                                        <TableCell className="font-bold text-white pl-6 py-4">
                                            <div className="flex flex-col">
                                                <span>{symbol}</span>
                                                <span className="text-[10px] text-gray-600 font-mono tracking-tighter uppercase">{f.timeframe || 'H1'}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="font-mono text-gray-300">
                                            {formatPrice(f.close)}
                                        </TableCell>
                                        <TableCell className="font-mono">
                                            {renderRSI(f.rsi_14)}
                                        </TableCell>
                                        <TableCell className="font-mono text-gray-400">
                                            {f.atr_14?.toFixed(4) || <Minus size={14} className="text-gray-600" />}
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex justify-center">
                                                {renderTrend(f.ema_9, f.ema_20)}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex justify-center">
                                                {renderTrend(f.ema_50, f.ema_200)}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex justify-center">
                                                {f.smc?.structure?.trend ? (
                                                    <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                                        f.smc.structure.trend === 'bullish' ? 'bg-blue-500/10 text-blue-400' : 'bg-orange-500/10 text-orange-400'
                                                    }`}>
                                                        {f.smc.structure.trend}
                                                    </span>
                                                ) : <Minus size={14} className="text-gray-600" />}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right pr-6 text-[10px] font-mono text-gray-600">
                                            {f.timestamp ? new Date(f.timestamp).toLocaleTimeString() : '-'}
                                        </TableCell>
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    );
};
