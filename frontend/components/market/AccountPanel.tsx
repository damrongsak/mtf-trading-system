'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Wallet, History, Radio, RefreshCcw, Maximize2, ChevronDown, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

// Helper component for Orders (can be moved to its own file later)
const OrdersTable = ({ orders, loading }: { orders: any[], loading: boolean }) => {
    if (loading && !orders.length) return <div className="p-4 text-center text-gray-500">Loading Orders...</div>;
    if (!orders.length) return <div className="p-8 text-center text-gray-500">No pending orders</div>;

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-white/5 text-gray-500 uppercase font-bold">
                    <tr>
                        <th className="px-4 py-2">ID</th>
                        <th className="px-4 py-2">Symbol</th>
                        <th className="px-4 py-2">Type</th>
                        <th className="px-4 py-2">Side</th>
                        <th className="px-4 py-2">Size</th>
                        <th className="px-4 py-2">Price</th>
                        <th className="px-4 py-2">Time</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                    {orders.map((o: any) => (
                        <tr key={o.id} className="hover:bg-white/5">
                            <td className="px-4 py-2 font-mono text-gray-500">{o.id}</td>
                            <td className="px-4 py-2 font-bold text-gray-200">{o.instrument}</td>
                            <td className="px-4 py-2 text-gray-400">{o.type || 'LIMIT'}</td>
                            <td className="px-4 py-2">
                                <span className={cn(
                                    "px-1.5 py-0.5 rounded text-[10px] font-bold",
                                    parseFloat(o.units) > 0 ? "bg-blue-500/10 text-blue-400" : "bg-rose-500/10 text-rose-400"
                                )}>
                                    {parseFloat(o.units) > 0 ? 'BUY' : 'SELL'}
                                </span>
                            </td>
                            <td className="px-4 py-2 font-mono">{o.units}</td>
                            <td className="px-4 py-2 font-mono text-white">{o.price}</td>
                            <td className="px-4 py-2 text-gray-500">{o.time ? new Date(o.time).toLocaleTimeString() : '-'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

import { getTrades, Trade, getAccountSummary, AccountSummary, getOpenPositions, getPendingOrders } from '@/lib/api/execution';
import { logger } from '@/lib/api/app-logger';
import { TradesTable } from '@/components/trades/TradesTable';
import { Pagination } from '@/components/common';
import { useAccount } from '@/context/AccountContext';

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
    refreshTrigger: number;
    onMaximize: () => void;
    onMinimize: () => void;
}

export const AccountPanel: React.FC<AccountPanelProps> = ({ refreshTrigger, onMaximize, onMinimize }) => {
    const { selectedAccount } = useAccount();
    const accountId = selectedAccount?.id;
    
    const [activeTab, setActiveTab] = useState<'POSITIONS' | 'HISTORY' | 'SUMMARY' | 'ORDERS'>('POSITIONS');
    const [trades, setTrades] = useState<Trade[]>([]);
    const [orders, setOrders] = useState<any[]>([]); // Using any for now, or define Order type
    const [history, setHistory] = useState<Trade[]>([]);
    
    // Pagination State
    const [historyPage, setHistoryPage] = useState(1);
    const [historyPerPage, setHistoryPerPage] = useState(10);
    const [historyTotal, setHistoryTotal] = useState(0);

    const [summary, setSummary] = useState<AccountSummary | null>(null);
    const [loading, setLoading] = useState(false);

    const loadData = useCallback(async () => {
        if (!accountId) return; // Don't fetch if no account selected
        
        setLoading(true);
        try {
            // Parallel fetch
            const [openRes, closedRes, sumRes, pendingRes] = await Promise.all([
                getOpenPositions(accountId),
                getTrades({ status: 'CLOSED', page: historyPage, per_page: historyPerPage, account_id: accountId }),
                getAccountSummary(accountId),
                getPendingOrders(accountId)
            ]);

            setTrades(openRes || []);
            setHistory(closedRes.data || []);
            if (closedRes.meta && typeof closedRes.meta.total === 'number') {
                setHistoryTotal(closedRes.meta.total);
            }
            setSummary(sumRes);
            setOrders(pendingRes || []);
        } catch (e) {
            logger.error("Failed to load account panel data", e);
        }
 finally {
            setLoading(false);
        }
    }, [accountId, historyPage, historyPerPage]);

    useEffect(() => { loadData(); }, [loadData, refreshTrigger]);

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
                        label={`Orders (${orders.length})`} 
                        icon={Activity} 
                        active={activeTab === 'ORDERS'} 
                        onClick={() => setActiveTab('ORDERS')} 
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

                {activeTab === 'ORDERS' && (
                    <div className="h-full">
                         <OrdersTable orders={orders} loading={loading} />
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
