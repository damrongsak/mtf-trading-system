'use client';

import React from 'react';
import { useBrokerReference } from '@/context/BrokerReferenceContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, RefreshCw, AlertCircle, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function BrokerReferenceDashboard() {
    const { symbols, loading, error, refresh } = useBrokerReference();

    const symbolsList = Array.from(symbols.values());

    return (
        <Card className="bg-gray-950/50 backdrop-blur-sm border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle className="text-xl text-white">Global Broker Reference</CardTitle>
                    <CardDescription>
                        Live instrument specifications synced from your active broker (OANDA).
                        These rules are enforced globally for all manual and automated trades.
                    </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={() => refresh()} disabled={loading}>
                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                    Refresh
                </Button>
            </CardHeader>
            <CardContent>
                {error && (
                    <div className="mb-4 p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-400 flex items-center gap-2">
                        <AlertCircle className="h-5 w-5" />
                        {error}
                    </div>
                )}

                {loading && symbols.size === 0 ? (
                     <div className="flex justify-center py-12">
                        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
                    </div>
                ) : symbols.size === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                        No symbols found. Please go to Settings and Sync your Broker Account.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left text-gray-400">
                            <thead className="text-xs text-gray-500 uppercase bg-gray-900/50">
                                <tr>
                                    <th className="px-4 py-3 rounded-tl-lg">Symbol</th>
                                    <th className="px-4 py-3">Pip Location</th>
                                    <th className="px-4 py-3">Precision</th>
                                    <th className="px-4 py-3">Margin Rate</th>
                                    <th className="px-4 py-3">Max Units</th>
                                    <th className="px-4 py-3 text-right rounded-tr-lg">Source</th>
                                </tr>
                            </thead>
                            <tbody>
                                {symbolsList.map((sym) => {
                                    const details = sym.details || {};
                                    return (
                                        <tr key={sym.symbol} className="border-b border-gray-800 hover:bg-gray-900/20 transition-colors">
                                            <td className="px-4 py-3 font-medium text-white">
                                                {sym.display_name || sym.symbol}
                                                <span className="block text-xs text-gray-500">{sym.symbol}</span>
                                            </td>
                                            <td className="px-4 py-3 font-mono">
                                                {details.pipLocation !== undefined ? Math.pow(10, details.pipLocation).toFixed(details.displayPrecision || 4) : '-'}
                                                <span className="text-xs text-gray-600 block">10^{details.pipLocation}</span>
                                            </td>
                                            <td className="px-4 py-3">{details.displayPrecision ?? '-'}</td>
                                            <td className="px-4 py-3">
                                                {details.marginRate ? (
                                                    <span className="px-2 py-1 rounded bg-blue-500/10 text-blue-400 text-xs font-mono">
                                                        {(parseFloat(details.marginRate) * 100).toFixed(1)}% (1:{(1/parseFloat(details.marginRate)).toFixed(0)})
                                                    </span>
                                                ) : '-'}
                                            </td>
                                            <td className="px-4 py-3 text-xs font-mono">
                                                <div className="flex flex-col gap-1">
                                                    <span>Max: {details.maximumOrderUnits ? parseInt(details.maximumOrderUnits).toLocaleString() : 'Unlim'}</span>
                                                    <span>Min: {details.minimumTradeSize ?? '-'}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-800 text-gray-300">
                                                    {sym.category}
                                                </span>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
                
                <div className="mt-6 p-4 bg-gray-900/30 rounded-lg border border-gray-800 text-xs text-gray-500 flex items-start gap-3">
                    <Info className="h-5 w-5 text-blue-500 shrink-0" />
                    <p>
                        This data is fetched directly from the Oanda v20 API via your connected account. 
                        It ensures that the &quot;Risk Citadel&quot; and &quot;Strategy Core&quot; modules respect the exact 
                        limitations of your specific account type (e.g. FIFO rules, Hedging capability, Leverage limits).
                        <br/><br/>
                        For example, if you trade XAU/USD, the system knows that 1 pip = 0.01 (not 0.0001) and calculates risk accordingly.
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}
