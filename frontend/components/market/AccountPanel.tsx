'use client';

import React, { useState, useEffect } from 'react';
import { getTrades, Trade, getAccountSummary, AccountSummary } from '@/lib/api/execution';
import { TradesTable } from '@/components/trades/TradesTable'; // Reuse existing table

import { Wallet, History, Radio, RefreshCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

// Simple mocked tabs if shadcn not fully available or for simplicity in this file
interface PanelTabProps {
    active: boolean;
    onClick: () => void;
    icon: React.ElementType;
    label: string;
}

const PanelTab = ({ active, onClick, icon: Icon, label }: PanelTabProps) => (
    <button 
        onClick={onClick}
        className={cn(
            "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors",
            active ? "border-blue-500 text-blue-400 bg-blue-500/5" : "border-transparent text-gray-500 hover:text-gray-300 hover:bg-white/5"
        )}
    >
        <Icon size={16} />
        {label}
    </button>
);

interface AccountPanelProps {
    accountId: string;
    refreshTrigger: number;
}

export const AccountPanel: React.FC<AccountPanelProps> = ({ accountId, refreshTrigger }) => {
    const [activeTab, setActiveTab] = useState<'POSITIONS' | 'HISTORY' | 'SUMMARY'>('POSITIONS');
    const [trades, setTrades] = useState<Trade[]>([]);
    const [history, setHistory] = useState<Trade[]>([]);
    const [summary, setSummary] = useState<AccountSummary | null>(null);
    const [loading, setLoading] = useState(false);

    const loadData = async () => {
        if (!accountId) return; // Don't fetch if no account selected
        
        setLoading(true);
        try {
            // Parallel fetch
            const [openRes, closedRes, sumRes] = await Promise.all([
                getTrades({ status: 'OPEN', page: 1, per_page: 50, account_id: accountId }),
                getTrades({ status: 'CLOSED', page: 1, per_page: 50, account_id: accountId }),
                getAccountSummary(accountId)
            ]);

            setTrades(openRes.data || []);
            setHistory(closedRes.data || []);
            setSummary(sumRes);
        } catch (e) {
            console.error("Failed to load account data", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, [accountId, refreshTrigger]);

    // Expose refresh method to parent if needed via ref, but for now auto-refresh or manual button
    
    return (
        <div className="h-full flex flex-col bg-gray-900/50 backdrop-blur border-t border-white/5">
            {/* Toolbar */}
            <div className="flex items-center justify-between bg-black/20 px-2">
                 <div className="flex">
                    <PanelTab 
                        label={`Positions (${trades.length})`} 
                        icon={Radio} 
                        active={activeTab === 'POSITIONS'} 
                        onClick={() => setActiveTab('POSITIONS')} 
                    />
                    <PanelTab 
                        label="History" 
                        icon={History} 
                        active={activeTab === 'HISTORY'} 
                        onClick={() => setActiveTab('HISTORY')} 
                    />
                    <PanelTab 
                        label="Account Summary" 
                        icon={Wallet} 
                        active={activeTab === 'SUMMARY'} 
                        onClick={() => setActiveTab('SUMMARY')} 
                    />
                 </div>
                 <button onClick={loadData} className="p-2 text-gray-500 hover:text-white transition-colors">
                     <RefreshCcw size={14} className={cn(loading && "animate-spin")} />
                 </button>
            </div>

            {/* Content Content - Scrollable */}
            <div className="flex-1 overflow-auto bg-gray-950/30 p-2 min-h-[250px]">
                {activeTab === 'POSITIONS' && (
                    <div className="h-full">
                         <TradesTable trades={trades} loading={loading} />
                    </div>
                )}
                
                {activeTab === 'HISTORY' && (
                    <div className="h-full">
                         <TradesTable trades={history} loading={loading} />
                    </div>
                )}

                 {activeTab === 'SUMMARY' && (
                    <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-6">
                        {summary ? (
                            <>
                                <SummaryCard label="Balance" value={summary.balance} />
                                <SummaryCard label="Equity / NAV" value={summary.NAV} highlight />
                                <SummaryCard label="Free Margin" value={summary.marginAvailable} />
                                <SummaryCard label="Open Positions" value={summary.openPositionCount.toString()} />
                            </>
                        ) : (
                            <div className="text-gray-500col-span-4">Loading Summary...</div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

interface SummaryCardProps {
    label: string;
    value: string;
    highlight?: boolean;
}

const SummaryCard = ({ label, value, highlight }: SummaryCardProps) => (
    <div className="p-4 bg-gray-800/50 rounded-xl border border-white/5">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
        <div className={cn("text-2xl font-mono font-bold", highlight ? "text-blue-400" : "text-white")}>
            {value.startsWith('$') ? value : `$${value}`} 
            {/* assuming value might come as number string or formatted */}
        </div>
    </div>
);
