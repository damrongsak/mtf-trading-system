'use client';

import React from 'react';
import { DollarSign, TrendingDown, TrendingUp, BarChart3 } from 'lucide-react';
import { Fund } from '@/lib/api/types';

interface FundOverviewCardsProps {
    funds: Fund[];
    loading?: boolean;
}

export function FundOverviewCards({ funds, loading }: FundOverviewCardsProps) {
    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="bg-gray-950/50 border border-gray-800 rounded-xl p-5 animate-pulse h-28" />
                ))}
            </div>
        );
    }

    const totalFunds = funds.length;
    const activeFunds = funds.filter(f => f.role === 'OWNER').length;
    const avgRiskPct = funds.length > 0
        ? funds.reduce((sum, f) => sum + (f.risk_percentage || 0), 0) / funds.length
        : 0;
    const minDrawdown = funds.reduce((min, f) => {
        const dd = f.max_drawdown_threshold || 100;
        return dd < min ? dd : min;
    }, 100);

    const cards = [
        {
            label: 'Total Funds',
            value: totalFunds.toString(),
            sub: `${activeFunds} owned`,
            icon: <DollarSign className="w-5 h-5" />,
            color: 'text-accent-blue',
            bg: 'bg-accent-blue/10'
        },
        {
            label: 'Avg Risk/Trade',
            value: `${(avgRiskPct * 100).toFixed(2)}%`,
            sub: 'across all funds',
            icon: <BarChart3 className="w-5 h-5" />,
            color: 'text-amber-400',
            bg: 'bg-amber-400/10'
        },
        {
            label: 'Tightest DD Limit',
            value: `${minDrawdown.toFixed(1)}%`,
            sub: 'max drawdown threshold',
            icon: <TrendingDown className="w-5 h-5" />,
            color: 'text-red-400',
            bg: 'bg-red-400/10'
        },
        {
            label: 'Strategy Types',
            value: [...new Set(funds.map(f => f.strategy_type))].length.toString(),
            sub: 'unique strategies',
            icon: <TrendingUp className="w-5 h-5" />,
            color: 'text-emerald-400',
            bg: 'bg-emerald-400/10'
        }
    ];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {cards.map((card) => (
                <div key={card.label} className="bg-gray-950/50 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">{card.label}</span>
                        <div className={`p-2 rounded-lg ${card.bg}`}>
                            <span className={card.color}>{card.icon}</span>
                        </div>
                    </div>
                    <div className="text-2xl font-bold text-gray-100 font-mono">{card.value}</div>
                    <div className="text-[10px] text-gray-600 mt-1">{card.sub}</div>
                </div>
            ))}
        </div>
    );
}
