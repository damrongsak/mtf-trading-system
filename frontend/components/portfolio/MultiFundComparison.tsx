'use client';

import React from 'react';
import { Fund } from '@/lib/api/types';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface MultiFundComparisonProps {
    funds: Fund[];
    loading?: boolean;
}

export function MultiFundComparison({ funds, loading }: MultiFundComparisonProps) {
    if (loading) {
        return (
            <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6 animate-pulse h-[300px]" />
        );
    }

    if (funds.length === 0) {
        return (
            <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6 flex items-center justify-center h-[200px]">
                <span className="text-gray-600 text-sm">No funds available</span>
            </div>
        );
    }

    // Find best/worst for highlighting
    const riskValues = funds.map(f => f.risk_percentage || 0);
    const ddValues = funds.map(f => f.max_drawdown_threshold || 0);
    const minRisk = Math.min(...riskValues);
    const maxDD = Math.max(...ddValues);

    return (
        <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-6">
            <div className="mb-4">
                <h3 className="text-lg font-semibold text-gray-100">Fund Comparison</h3>
                <p className="text-[10px] text-gray-500 mt-0.5 uppercase tracking-wider">Cross-fund risk metrics</p>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-gray-800">
                            <th className="text-left text-[10px] text-gray-500 uppercase tracking-wider pb-3 pr-4">Fund</th>
                            <th className="text-right text-[10px] text-gray-500 uppercase tracking-wider pb-3 px-3">Type</th>
                            <th className="text-right text-[10px] text-gray-500 uppercase tracking-wider pb-3 px-3">Risk %</th>
                            <th className="text-right text-[10px] text-gray-500 uppercase tracking-wider pb-3 px-3">Max DD</th>
                            <th className="text-right text-[10px] text-gray-500 uppercase tracking-wider pb-3 px-3">Max Risk/Trade</th>
                            <th className="text-right text-[10px] text-gray-500 uppercase tracking-wider pb-3 px-3">Lot Size</th>
                            <th className="text-right text-[10px] text-gray-500 uppercase tracking-wider pb-3 pl-3">Exposure</th>
                        </tr>
                    </thead>
                    <tbody>
                        {funds.map((fund) => {
                            const riskPct = fund.risk_percentage || 0;
                            const drawdown = fund.max_drawdown_threshold || 0;
                            const isBestRisk = riskPct === minRisk && funds.length > 1;
                            const isHighestDD = drawdown === maxDD && funds.length > 1 && maxDD > 0;

                            return (
                                <tr key={fund.id} className="border-b border-gray-800/50 hover:bg-gray-900/30 transition-colors">
                                    <td className="py-3 pr-4">
                                        <div className="flex flex-col">
                                            <span className="text-gray-200 font-medium text-xs">{fund.name}</span>
                                            <span className="text-[9px] text-gray-600">{fund.owner_name}</span>
                                        </div>
                                    </td>
                                    <td className="py-3 px-3 text-right">
                                        <span className="text-[10px] bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full font-mono">
                                            {fund.strategy_type.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td className="py-3 px-3 text-right">
                                        <span className={`font-mono text-xs font-bold ${isBestRisk ? 'text-emerald-400' : 'text-gray-200'}`}>
                                            {(riskPct * 100).toFixed(2)}%
                                        </span>
                                        {isBestRisk && <ArrowDownRight className="w-3 h-3 text-emerald-400 inline ml-1" />}
                                    </td>
                                    <td className="py-3 px-3 text-right">
                                        <span className={`font-mono text-xs font-bold ${isHighestDD ? 'text-red-400' : 'text-gray-200'}`}>
                                            {drawdown > 0 ? `${drawdown.toFixed(1)}%` : '—'}
                                        </span>
                                        {isHighestDD && <ArrowUpRight className="w-3 h-3 text-red-400 inline ml-1" />}
                                    </td>
                                    <td className="py-3 px-3 text-right font-mono text-xs text-gray-300">
                                        ${fund.max_risk_per_trade.toFixed(2)}
                                    </td>
                                    <td className="py-3 px-3 text-right font-mono text-xs text-gray-300">
                                        {fund.default_lot_size}
                                    </td>
                                    <td className="py-3 pl-3 text-right">
                                        {fund.gross_exposure_limit ? (
                                            <span className="font-mono text-xs text-gray-300">{fund.gross_exposure_limit}%</span>
                                        ) : (
                                            <Minus className="w-3 h-3 text-gray-700 inline" />
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
