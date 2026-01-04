'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient } from '@/lib/api/client';

export interface BrokerInstrumentDetails {
    pipLocation?: number;
    displayPrecision?: number;
    marginRate?: string;
    maximumOrderUnits?: string;
    minimumTradeSize?: string;
    displayName?: string;
    mode?: string; // e.g., "MKT" (Market), "LMT" (Limit)
    financing?: {
        longRate: string;
        shortRate: string;
    };
    [key: string]: any;
}

export interface BrokerSymbol {
    id: string;
    symbol: string;
    display_name: string;
    category: string;
    details: BrokerInstrumentDetails | null;
}

interface BrokerReferenceContextType {
    symbols: Map<string, BrokerSymbol>;
    loading: boolean;
    error: string | null;
    getInstrument: (symbol: string) => BrokerSymbol | undefined;
    formatPrice: (symbol: string, price: number) => string;
    refresh: () => Promise<void>;
}

const BrokerReferenceContext = createContext<BrokerReferenceContextType | undefined>(undefined);

export function BrokerReferenceProvider({ children }: { children: ReactNode }) {
    const [symbols, setSymbols] = useState<Map<string, BrokerSymbol>>(new Map());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchSymbols = async () => {
        try {
            setLoading(true);
            // Default to OANDA for Global Reference for now. 
            // In future, this could be dynamic based on selected account context.
            const response = await apiClient.get<any>('/api/v1/market/symbols?data_source=OANDA');
            
            const data = response.data?.data || [];
            const map = new Map<string, BrokerSymbol>();
            
            data.forEach((s: any) => {
                map.set(s.symbol, s);
                // Also map display name for fuzzy search if needed?
            });
            
            setSymbols(map);
            setError(null);
        } catch (err: any) {
             console.error("Failed to load broker reference:", err);
            // Don't block app flow, just log error.
            setError("Failed to load global broker data");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSymbols();
    }, []);

    const getInstrument = (symbol: string) => {
        return symbols.get(symbol);
    };

    const formatPrice = (symbol: string, price: number) => {
        const inst = symbols.get(symbol);
        if (!inst || !inst.details || typeof inst.details.displayPrecision === 'undefined') {
            return price.toFixed(5); // Default fallback
        }
        return price.toFixed(inst.details.displayPrecision);
    };

    return (
        <BrokerReferenceContext.Provider value={{ 
            symbols, 
            loading, 
            error, 
            getInstrument, 
            formatPrice,
            refresh: fetchSymbols
        }}>
            {children}
        </BrokerReferenceContext.Provider>
    );
}

export function useBrokerReference() {
    const context = useContext(BrokerReferenceContext);
    if (context === undefined) {
        throw new Error('useBrokerReference must be used within a BrokerReferenceProvider');
    }
    return context;
}
