import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLivePrices } from "@/lib/hooks/useLivePrices";
import { ArrowUpIcon, ArrowDownIcon, Loader2 } from "lucide-react";
import { getMarketCategories, MarketCategory } from "@/lib/api/market_data";
import { useAsync } from "@/lib/hooks";
import { useEffect, useMemo, useState } from "react";

export function MarketWatchCard() {
    const { data: categories, loading: categoriesLoading, execute: fetchCategories } = useAsync<MarketCategory[]>(getMarketCategories);

    useEffect(() => {
        fetchCategories();
    }, []);

    // Extract all symbols to subscribe to
    const allSymbols = useMemo(() => {
        if (!categories) return [];
        return categories.flatMap(cat => cat.items.map(item => item.symbol));
    }, [categories]);

    // Connect to WebSocket with dynamic symbols
    const { prices, isConnected } = useLivePrices(allSymbols);
    
    // Helper to get price data for a symbol
    const getPriceData = (symbol: string) => {
        return prices[symbol] || { bid: 0, ask: 0, time: new Date().toISOString() };
    };

    const [activeTab, setActiveTab] = useState<string | null>(null);
    const [isExpanded, setIsExpanded] = useState(false);

    // Set default tab when categories load
    useEffect(() => {
        if (categories && categories.length > 0 && !activeTab) {
            setActiveTab(categories[0].id);
        }
    }, [categories, activeTab]);

    // Handle Tab Change
    const handleTabChange = (categoryId: string) => {
        setActiveTab(categoryId);
        setIsExpanded(false); // Reset expansion when switching tabs
    };

    if (categoriesLoading) {
        return (
            <Card className="shadow-lg border-0 bg-card/50 backdrop-blur-sm">
                <CardHeader>
                    <CardTitle>Market Watch</CardTitle>
                </CardHeader>
                 <CardContent className="flex justify-center py-6">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </CardContent>
            </Card>
        )
    }

    const activeCategory = categories?.find(c => c.id === activeTab);
    const displayedItems = activeCategory 
        ? (isExpanded ? activeCategory.items : activeCategory.items.slice(0, 5))
        : [];
    const hasMore = activeCategory ? activeCategory.items.length > 5 : false;

    return (
        <Card className="shadow-lg border-0 bg-card/50 backdrop-blur-sm">
            <CardHeader className="pb-0 space-y-4">
                <div className="flex flex-row items-center justify-between">
                    <CardTitle className="text-xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                        Market Watch
                    </CardTitle>
                    <Badge 
                        variant="outline" 
                        className={`transition-colors duration-300 ${isConnected ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-destructive/10 text-destructive border-destructive/20"}`}
                    >
                        {isConnected ? "Live" : "Connecting..."}
                    </Badge>
                </div>
                
                {/* Tabs Navigation */}
                <div className="flex overflow-x-auto scrollbar-hide -mx-6 px-6 border-b border-gray-800/60">
                     <div className="flex w-full min-w-max">
                        {categories?.map((cat) => (
                            <button
                                key={cat.id}
                                onClick={() => handleTabChange(cat.id)}
                                className={`
                                    relative px-4 py-3 text-sm font-medium transition-all duration-200
                                    border-b-2
                                    ${activeTab === cat.id 
                                        ? "border-accent-blue text-white bg-accent-blue/10" 
                                        : "border-transparent text-gray-400 hover:text-white hover:bg-gray-800/50"
                                    }
                                `}
                            >
                                {cat.name}
                            </button>
                        ))}
                    </div>
                </div>
            </CardHeader>
            
            <CardContent className="pt-4">
                <div className="space-y-2 min-h-[200px]">
                    {!activeCategory ? (
                        <div className="flex flex-col items-center justify-center h-40 text-muted-foreground text-sm">
                           <Loader2 className="h-4 w-4 animate-spin mb-2" />
                           Loading categories...
                        </div>
                    ) : (
                        <>
                           {displayedItems.length === 0 ? (
                                <p className="text-center text-muted-foreground py-8 text-sm">No symbols in this category</p>
                           ) : (
                               displayedItems.map((item) => {
                                   const price = getPriceData(item.symbol);
                                   // Mock change (randomize slightly for visual demo if needed, or 0)
                                   // In real app, `PriceUpdate` should have `change` or `open` to calc.
                                   // For now, keep as 0 or mock.
                                   const change = 0;
                                   
                                   return (
                                       <div 
                                           key={item.id} 
                                           className="group flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors border border-transparent hover:border-border/50"
                                       >
                                           <div className="flex flex-col">
                                               <div className="flex items-center space-x-2">
                                                   <span className="font-bold text-sm">{item.display_name || item.symbol}</span>
                                                   {item.broker && (
                                                       <span className="px-1.5 py-0.5 rounded-full text-[9px] font-medium bg-primary/10 text-primary border border-primary/20">
                                                           {item.broker}
                                                       </span>
                                                   )}
                                               </div>
                                               <span className="text-xs text-muted-foreground font-mono mt-0.5">{item.symbol}</span>
                                           </div>
                                           <div className="flex flex-col items-end">
                                               <span className={`font-mono font-medium text-sm transition-colors duration-300`}>
                                                   {price.bid ? price.bid.toFixed(5) : "---"}
                                               </span>
                                               <div className={`flex items-center text-xs ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                    {change >= 0 ? <ArrowUpIcon className="h-3 w-3 mr-1" /> : <ArrowDownIcon className="h-3 w-3 mr-1" />}
                                                    {Math.abs(change).toFixed(2)}%
                                               </div>
                                           </div>
                                       </div>
                                   );
                               })
                           )}
                           
                           {hasMore && (
                                <button 
                                    onClick={() => setIsExpanded(!isExpanded)}
                                    className="w-full text-center text-xs font-medium text-muted-foreground hover:text-primary mt-4 flex items-center justify-center py-2 transition-colors"
                                >
                                    {isExpanded ? (
                                        <>Show Less <ArrowUpIcon className="ml-1 h-3 w-3" /></>
                                    ) : (
                                        <>Show All ({activeCategory.items.length}) <ArrowDownIcon className="ml-1 h-3 w-3" /></>
                                    )}
                                </button>
                           )}
                        </>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
