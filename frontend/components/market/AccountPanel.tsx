'use client';

import React, { useState, useEffect } from 'react';
import { getTrades, Trade, getAccountSummary, AccountSummary } from '@/lib/api/execution';
import { TradesTable } from '@/components/trades/TradesTable'; // Reuse existing table
import { Pagination } from '@/components/common/Pagination';

import { Wallet, History, Radio, RefreshCcw, Maximize2, ChevronDown } from 'lucide-react';
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

import { useAccount } from '@/context/AccountContext';

interface AccountPanelProps {
    refreshTrigger: number;
    onMaximize: () => void;
    onMinimize: () => void;
}

export const AccountPanel: React.FC<AccountPanelProps> = ({ refreshTrigger, onMaximize, onMinimize }) => {
    const { selectedAccount } = useAccount();
    const accountId = selectedAccount?.id;
    
    const [activeTab, setActiveTab] = useState<'POSITIONS' | 'HISTORY' | 'SUMMARY'>('POSITIONS');
    const [trades, setTrades] = useState<Trade[]>([]);
    const [history, setHistory] = useState<Trade[]>([]);
    
    // Pagination State
    const [historyPage, setHistoryPage] = useState(1);
    const [historyPerPage, setHistoryPerPage] = useState(10);
    const [historyTotal, setHistoryTotal] = useState(0);

    const [summary, setSummary] = useState<AccountSummary | null>(null);
    const [loading, setLoading] = useState(false);

    const loadData = async () => {
        if (!accountId) return; // Don't fetch if no account selected
        
        setLoading(true);
        try {
            // Parallel fetch
            const [openRes, closedRes, sumRes] = await Promise.all([
                getTrades({ status: 'OPEN', page: 1, per_page: 50, account_id: accountId }),
                getTrades({ status: 'CLOSED', page: historyPage, per_page: historyPerPage, account_id: accountId }),
                getAccountSummary(accountId)
            ]);

            setTrades(openRes.data || []);
            setHistory(closedRes.data || []);
            if (closedRes.meta && typeof closedRes.meta.total === 'number') {
                setHistoryTotal(closedRes.meta.total);
            }
            setSummary(sumRes);
        } catch (e) {
            console.error("Failed to load account data", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, [accountId, refreshTrigger, historyPage, historyPerPage]);

    // Reset page when account changes
    useEffect(() => {
        setHistoryPage(1);
    }, [accountId]);

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
                 <div className="flex items-center gap-1">
                     <button onClick={loadData} className="p-2 text-gray-500 hover:text-white transition-colors" title="Refresh Data">
                         <RefreshCcw size={14} className={cn(loading && "animate-spin")} />
                     </button>
                     <div className="w-px h-4 bg-white/10 mx-1" />
                     <button onClick={onMinimize} className="p-2 text-gray-500 hover:text-white transition-colors" title="Minimize">
                         <ChevronDown size={14} />
                     </button>
                     <button onClick={onMaximize} className="p-2 text-gray-500 hover:text-white transition-colors" title="Maximize">
                         <Maximize2 size={14} />
                     </button>
                 </div>
            </div>

            {/* Content Content - Scrollable */}
            <div className="flex-1 overflow-auto bg-gray-950/30 p-2 min-h-[250px]">
                {activeTab === 'POSITIONS' && (
                    <div className="h-full">
                         <TradesTable trades={trades} loading={loading} />
                    </div>
                )}
                
                {activeTab === 'HISTORY' && (
                    <div className="h-full flex flex-col">
                         <div className="flex-1 overflow-auto">
                            <TradesTable trades={history} loading={loading} />
                         </div>
                         <div className="shrink-0 mt-2">
                            <Pagination 
                                currentPage={historyPage}
                                totalPages={Math.ceil(historyTotal / historyPerPage)}
                                perPage={historyPerPage}
                                total={historyTotal}
                                onPageChange={setHistoryPage}
                                onPerPageChange={setHistoryPerPage}
                            />
                         </div>
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
