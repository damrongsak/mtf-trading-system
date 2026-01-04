import React, { useState, useMemo } from 'react';
import { useBrokerReference, BrokerSymbol } from '@/context/BrokerReferenceContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, RefreshCw, AlertCircle, Info, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Pagination } from '@/components/common/Pagination';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export function BrokerReferenceDashboard() {
    const { symbols, loading, error, refresh } = useBrokerReference();
    
    // Search and Filter State
    const [searchTerm, setSearchTerm] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('ALL');
    
    // Pagination State
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(25);

    // Derived Data: Filtered Symbols
    const filteredSymbols = useMemo(() => {
        const result: BrokerSymbol[] = [];
        const searchLower = searchTerm.toLowerCase();

        symbols.forEach((symbol) => {
            // Filter by Name/Symbol
            const matchesSearch = 
                symbol.symbol.toLowerCase().includes(searchLower) || 
                (symbol.display_name && symbol.display_name.toLowerCase().includes(searchLower));

            // Filter by Category
            const matchesCategory = categoryFilter === 'ALL' || symbol.category === categoryFilter;

            if (matchesSearch && matchesCategory) {
                result.push(symbol);
            }
        });
        
        // Sort alphabetically by symbol
        return result.sort((a, b) => a.symbol.localeCompare(b.symbol));
    }, [symbols, searchTerm, categoryFilter]);

    // Derived Data: Paginated Symbols
    const paginatedSymbols = useMemo(() => {
        const startIndex = (currentPage - 1) * itemsPerPage;
        return filteredSymbols.slice(startIndex, startIndex + itemsPerPage);
    }, [filteredSymbols, currentPage, itemsPerPage]);

    // Handle Search/Filter Change (Reset Page)
    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(e.target.value);
        setCurrentPage(1);
    };

    const handleCategoryChange = (value: string) => {
        setCategoryFilter(value);
        setCurrentPage(1);
    };

    // Extract unique categories for filter
    const categories = useMemo(() => {
        const cats = new Set<string>();
        symbols.forEach(s => s.category && cats.add(s.category));
        return Array.from(cats).sort();
    }, [symbols]);

    return (
        <Card className="bg-gray-950/50 backdrop-blur-sm border-gray-800">
            <CardHeader className="flex flex-col gap-4 border-b border-gray-800 pb-4">
                <div className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="text-xl text-white">Global Broker Reference</CardTitle>
                        <CardDescription>
                            Live instrument specifications synced from your active broker (OANDA).
                        </CardDescription>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => refresh()} disabled={loading}>
                        {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                        Refresh
                    </Button>
                </div>
                
                {/* Search and Filters */}
                <div className="flex items-center gap-3">
                    <div className="relative w-full md:w-64">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
                        <Input
                            placeholder="Search symbol..."
                            value={searchTerm}
                            onChange={handleSearchChange}
                            className="pl-8 bg-gray-900 border-gray-700"
                        />
                    </div>
                    <Select value={categoryFilter} onValueChange={handleCategoryChange}>
                        <SelectTrigger className="w-[180px] bg-gray-900 border-gray-700">
                            <SelectValue placeholder="Category" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All Categories</SelectItem>
                            {categories.map(cat => (
                                <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <div className="flex-1" />
                    <div className="text-sm text-gray-500">
                        {filteredSymbols.length} Instruments
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                {error && (
                    <div className="m-4 p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-400 flex items-center gap-2">
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
                    <>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left text-gray-400">
                                <thead className="text-xs text-gray-500 uppercase bg-gray-900/50">
                                    <tr>
                                        <th className="px-4 py-3 border-b border-gray-800">Symbol</th>
                                        <th className="px-4 py-3 border-b border-gray-800">Pip Location</th>
                                        <th className="px-4 py-3 border-b border-gray-800">Precision</th>
                                        <th className="px-4 py-3 border-b border-gray-800">Margin Rate</th>
                                        <th className="px-4 py-3 border-b border-gray-800">Max Units</th>
                                        <th className="px-4 py-3 text-right border-b border-gray-800">Source</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {paginatedSymbols.map((sym) => {
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
                                    {paginatedSymbols.length === 0 && (
                                        <tr>
                                            <td colSpan={6} className="py-12 text-center text-gray-500">
                                                No results found matching &quot;{searchTerm}&quot;
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                        
                        <Pagination
                            currentPage={currentPage}
                            totalPages={Math.ceil(filteredSymbols.length / itemsPerPage)}
                            perPage={itemsPerPage}
                            total={filteredSymbols.length}
                            onPageChange={setCurrentPage}
                            onPerPageChange={setItemsPerPage}
                        />
                    </>
                )}
                
                <div className="m-4 p-4 bg-gray-900/30 rounded-lg border border-gray-800 text-xs text-gray-500 flex items-start gap-3">
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
