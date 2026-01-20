'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient } from '@/lib/api/client';
import { useAccount } from './AccountContext';

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
    [key: string]: unknown;
}

export interface BrokerSymbol {
    id: string;
    symbol: string;
    display_name: string;
    category: string;
    details: BrokerInstrumentDetails | null;
}

interface BrokerSymbolsResponse {
    data: BrokerSymbol[];
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

    const { selectedAccount } = useAccount();

    const fetchSymbols = async () => {
        try {
            setLoading(true);
            
            // Determine Data Source from Selected Account
            // Default to OANDA
            let dataSource = 'OANDA';
            
            if (selectedAccount) {
                if (selectedAccount.broker_name === 'CTRADER') {
                    // Mapped to the actual active cTrader Data Source Name
                    dataSource = 'CTRADER'; 
                } 
                // Add other mappings here as needed, e.g. BINANCE
            }
            
            console.log(`[BrokerRef] Fetching symbols for Data Source: ${dataSource}`);

            const response = await apiClient.get<BrokerSymbolsResponse>(`/api/v1/market/symbols?data_source=${dataSource}`);
            
            const data = response.data?.data || [];
            const map = new Map<string, BrokerSymbol>();
            
            data.forEach((s: BrokerSymbol) => {
                map.set(s.symbol, s);
            });
            
            setSymbols(map);
            setError(null);
        } catch (err: unknown) {
             console.error("Failed to load broker reference:", err);
            setError("Failed to load global broker data");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSymbols();
    }, [selectedAccount]);

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
