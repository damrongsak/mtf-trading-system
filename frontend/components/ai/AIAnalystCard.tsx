'use client';

import React, { useState } from 'react';
import { getMarketAnalysis, MarketAnalysisRequest } from '@/lib/api/ai';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Bot, RefreshCw, Loader2 } from 'lucide-react';

export const AIAnalystCard: React.FC = () => {
    const [insight, setInsight] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [lastUpdated, setLastUpdated] = useState<string | null>(null);

    const fetchAnalysis = async () => {
        setLoading(true);
        try {
            const context: MarketAnalysisRequest = {
                trend_4h: "Neutral/Bullish",
                current_price: 2035.50,
                key_levels: [2020.00, 2040.00, 2050.00],
                recent_signals: [{ type: "BULLISH_ENGULFING", timeframe: "15m" }]
            };

            const response = await getMarketAnalysis(context);
            setInsight(response.insight);
            setLastUpdated(new Date(response.timestamp).toLocaleTimeString());
        } catch (err) {
            console.error(err);
            setInsight("Failed to retrieve AI analysis. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="p-6 bg-gradient-to-br from-indigo-950/20 to-purple-950/20 border-indigo-500/30">
            <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2">
                    <Bot className="w-6 h-6 text-indigo-400" />
                    <h3 className="text-lg font-semibold text-indigo-100">AI Market Analyst</h3>
                </div>
                <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={fetchAnalysis} 
                    disabled={loading}
                    className="text-indigo-300 hover:text-indigo-100"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                </Button>
            </div>
            
            <div className="prose prose-invert prose-sm max-w-none text-gray-300">
                {insight ? (
                    <div className="whitespace-pre-wrap">{insight}</div>
                ) : (
                    <div className="text-center py-8 text-gray-500">
                        <p>Click refresh to generate market outlook based on current technicals.</p>
                    </div>
                )}
            </div>
            
            {lastUpdated && (
                <p className="text-xs text-right text-gray-600 mt-4">
                    Generated at {lastUpdated}
                </p>
            )}
        </Card>
    );
};
