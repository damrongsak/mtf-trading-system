import React from 'react';
import { PriceUpdate } from '@/lib/api/types'; // added import
import { Loader2 } from 'lucide-react';

interface MarketWatchCardProps {
    symbols?: string[];
    prices?: Record<string, PriceUpdate>;
    connected?: boolean;
}

export const MarketWatchCard: React.FC<MarketWatchCardProps> = ({ 
    symbols = ['EUR_USD', 'XAU_USD', 'GBP_USD', 'USD_JPY'],
    prices = {},
    connected = false
}) => {
    // Removed internal hook


    return (
        <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 h-full">
            <div className="flex items-center justify-between mb-4">
                 <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold text-gray-100">Market Watch</h2>
                    {connected ? (
                        <span className="flex h-2 w-2 rounded-full bg-green-500 animate-pulse" title="Live" />
                    ) : (
                        <span className="flex h-2 w-2 rounded-full bg-red-500" title="Disconnected" />
                    )}
                </div>
            </div>

            <div className="space-y-4">
                {symbols.map(symbol => {
                    const data = prices[symbol];
                    const isUp = data ? (data.bid > data.ask) ? true : false : false; // Naive trend 
                    // Actually we don't store previous price to check trend in hook yet. 
                    // For now, let's just display raw Bid/Ask.
                    
                    return (
                        <div key={symbol} className="flex items-center justify-between p-3 bg-gray-900/50 rounded-lg hover:bg-gray-800/50 transition-colors border border-gray-800/50">
                            <div className="flex items-center gap-3">
                                <div className={`w-1 h-8 rounded-full ${connected && data ? 'bg-accent-blue' : 'bg-gray-700'}`} />
                                <div>
                                    <h3 className="font-bold text-gray-200">{symbol.replace('_', '/')}</h3>
                                    <p className="text-xs text-gray-500 font-mono">
                                        {data ? data.time.split('T')[1].split('.')[0] : '--:--:--'}
                                    </p>
                                </div>
                            </div>
                            
                            {data ? (
                                <div className="text-right flex items-center gap-4">
                                    <div>
                                        <p className="text-xs text-gray-500 uppercase">Bid</p>
                                        <p className="font-mono text-gray-300 font-medium">{data.bid.toFixed(5)}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-gray-500 uppercase">Ask</p>
                                        <p className="font-mono text-gray-300 font-medium">{data.ask.toFixed(5)}</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-gray-600 text-sm italic">
                                    <Loader2 className="w-4 h-4 animate-spin inline mr-1" />
                                    Loading...
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
