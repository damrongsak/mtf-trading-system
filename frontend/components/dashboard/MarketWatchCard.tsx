import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLivePrices } from "@/lib/hooks/useLivePrices";
import { ArrowUpIcon, ArrowDownIcon, Loader2 } from "lucide-react";
import { getMarketCategories, MarketCategory } from "@/lib/api/market_data";
import { useAsync } from "@/lib/hooks";
import { useEffect, useMemo } from "react";

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

    if (categoriesLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Market Watch</CardTitle>
                </CardHeader>
                 <CardContent className="flex justify-center py-6">
                    <Loader2 className="h-6 w-6 animate-spin" />
                </CardContent>
            </Card>
        )
    }

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle>Market Watch</CardTitle>
                <Badge variant={isConnected ? "default" : "destructive"}>
                    {isConnected ? "Live" : "Connecting..."}
                </Badge>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {categories?.map((category) => (
                        <div key={category.id}>
                            <h3 className="text-sm font-medium text-muted-foreground mb-2">{category.name}</h3>
                            <div className="space-y-2">
                                {category.items.length === 0 ? (
                                    <p className="text-xs text-muted-foreground pl-2">No symbols</p>
                                ) : (
                                    category.items.map((item) => {
                                        const price = getPriceData(item.symbol);
                                        // Mock change for now
                                        const change = 0; 
                                        
                                        return (
                                            <div key={item.id} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
                                                <div className="flex flex-col">
                                                    <span className="font-bold">{item.display_name || item.symbol}</span>
                                                    <span className="text-xs text-muted-foreground">{item.symbol}</span>
                                                </div>
                                                <div className="flex flex-col items-end">
                                                    <span className="font-mono font-medium">{price.bid ? price.bid.toFixed(5) : "---"}</span>
                                                    <div className={`flex items-center text-xs ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                        {change >= 0 ? <ArrowUpIcon className="h-3 w-3 mr-1" /> : <ArrowDownIcon className="h-3 w-3 mr-1" />}
                                                        {Math.abs(change).toFixed(2)}%
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    ))}
                    {!categories?.length && (
                         <div className="text-center text-muted-foreground p-4">
                            No market categories defined.
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
