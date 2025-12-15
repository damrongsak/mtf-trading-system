'use client';

import React, { useState, useEffect } from 'react';
import { TradesTable } from '@/components/trades/TradesTable';
import { getTrades, Trade, TradeStatus } from '@/lib/api/execution';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, ChevronLeft, ChevronRight, SlidersHorizontal, ArrowUpDown } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export default function TradesPage() {
    const { user } = useAuth();
    const [trades, setTrades] = useState<Trade[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    
    // Filters
    const [statusFilter, setStatusFilter] = useState<TradeStatus | 'ALL'>('ALL');
    const [symbolFilter, setSymbolFilter] = useState('');
    const [debouncedSymbol, setDebouncedSymbol] = useState('');

    // Debounce Search
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSymbol(symbolFilter);
            setPage(1); // Reset to page 1 on filter change
        }, 500);
        return () => clearTimeout(timer);
    }, [symbolFilter]);

    // Reset pagination when status changes
    useEffect(() => {
        setPage(1);
    }, [statusFilter]);

    const fetchTrades = async () => {
        try {
            setLoading(true);
            const response = await getTrades({
                page,
                per_page: 20, // increased page size for history
                status: statusFilter === 'ALL' ? undefined : statusFilter,
                symbol: debouncedSymbol || undefined
            });
            setTrades(response.data);
            setTotalPages(response.meta?.total_pages || 1);
        } catch (error) {
            console.error("Failed to fetch trades:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTrades();
    }, [page, statusFilter, debouncedSymbol]);


    return (
        <div className="min-h-screen p-6 space-y-6">
             {/* Header */}
             <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Trade History</h1>
                    <p className="text-gray-400">
                        Detailed log of all executed trades across strategies.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={fetchTrades}>
                         <ArrowUpDown className="w-4 h-4 mr-2" />
                         Refresh
                    </Button>
                </div>
            </div>

            {/* Filter Bar */}
            <div className="flex flex-col md:flex-row gap-4 bg-gray-900/40 p-4 rounded-xl border border-gray-800">
                 {/* Symbol Search */}
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input 
                        placeholder="Search by Symbol (e.g. XAU/USD)" 
                        className="pl-9 bg-gray-950/50 border-gray-700"
                        value={symbolFilter}
                        onChange={(e) => setSymbolFilter(e.target.value)}
                    />
                </div>
                
                {/* Status Filter */}
                <div className="w-full md:w-48">
                    <Select 
                        value={statusFilter} 
                        onValueChange={(val) => setStatusFilter(val as TradeStatus | 'ALL')}
                    >
                        <SelectTrigger className="bg-gray-950/50 border-gray-700">
                            <div className="flex items-center gap-2">
                                <SlidersHorizontal className="w-4 h-4 text-gray-400" />
                                <SelectValue placeholder="Status" />
                            </div>
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All Status</SelectItem>
                            <SelectItem value="OPEN">Open</SelectItem>
                            <SelectItem value="CLOSED">Closed</SelectItem>
                            <SelectItem value="REJECTED">Rejected</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* Table */}
            <TradesTable trades={trades} loading={loading} />

            {/* Pagination */}
            <div className="flex items-center justify-between border-t border-gray-800 pt-4">
                <div className="text-sm text-gray-500">
                    Page {page} of {totalPages}
                </div>
                <div className="flex items-center gap-2">
                    <Button 
                        variant="outline" 
                        size="sm" 
                        disabled={page <= 1 || loading}
                        onClick={() => setPage(p => p - 1)}
                    >
                        <ChevronLeft className="w-4 h-4" />
                        Previous
                    </Button>
                    <Button 
                        variant="outline" 
                        size="sm" 
                        disabled={page >= totalPages || loading}
                        onClick={() => setPage(p => p + 1)}
                    >
                        Next
                        <ChevronRight className="w-4 h-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
