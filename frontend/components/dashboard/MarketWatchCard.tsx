import React, { useState, useMemo } from 'react';
import { PriceUpdate } from '@/lib/api/types';
import { Loader2 } from 'lucide-react';

interface MarketWatchCardProps {
    symbols?: string[];
    prices?: Record<string, PriceUpdate>;
    connected?: boolean;
}

const CATEGORIES = ['Forex', 'Crypto', 'Metals', 'Indices', 'All'];

export const MarketWatchCard: React.FC<MarketWatchCardProps> = ({ 
    symbols = ['EUR_USD', 'XAU_USD', 'GBP_USD', 'USD_JPY'],
    prices = {},
    connected = false
}) => {
    const [activeTab, setActiveTab] = useState('Forex');

    const getCategory = (symbol: string) => {
        const s = symbol.toUpperCase();
        if (s.includes('XAU') || s.includes('XAG') || s.includes('GOLD')) return 'Metals';
        if (s.includes('BTC') || s.includes('ETH') || s.includes('SOL') || s.includes('USDT')) return 'Crypto';
        if (s.includes('SPX') || s.includes('NAS') || s.includes('US30')) return 'Indices';
        return 'Forex';
    };

    const filteredSymbols = useMemo(() => {
        let filtered = symbols;
        if (activeTab !== 'All') {
            filtered = symbols.filter(s => getCategory(s) === activeTab);
        }
        return filtered.slice(0, 5);
    }, [symbols, activeTab]);

    return (
        <div className="bg-gray-950/50 backdrop-blur-md border border-gray-800 rounded-xl p-6 flex flex-col">
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

            {/* Tabs */}
            <div className="flex gap-2 mb-4 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-800">
                {CATEGORIES.map(cat => (
                    <button
                        key={cat}
                        onClick={() => setActiveTab(cat)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                            activeTab === cat 
                                ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/40 shadow-sm shadow-accent-blue/10' 
                                : 'bg-gray-900 text-gray-400 border border-transparent hover:bg-gray-800 hover:text-gray-200'
                        }`}
                    >
                        {cat}
                    </button>
                ))}
            </div>

            <div className="space-y-3 overflow-y-auto pr-1 custom-scrollbar">
                {filteredSymbols.length > 0 ? (
                    filteredSymbols.map(symbol => {
                        const data = prices[symbol];
                        
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
                    })
                ) : (
                    <div className="text-center py-8 text-gray-500 text-sm">
                        No symbols in {activeTab}
                    </div>
                )}
            </div>
        </div>
    );
};
