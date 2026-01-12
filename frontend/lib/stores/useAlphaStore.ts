import { create } from 'zustand';
import { toast } from 'sonner';
import { apiClient } from '../api/client';
import { ApiError } from '../api/errors';

// Define types locally or import from generated API if verified
export interface AlphaResult {
    signal: number[];
    metrics: {
        sharpe?: number;
        ic?: number;
        [key: string]: string | number | boolean | undefined;
    };
    timestamps: string[];
}

interface AlphaStore {
    // State
    formula: string;
    symbol: string;
    timeframe: string;
    code: string; // Add missing property
    isRunning: boolean;
    result: AlphaResult | null;
    error: string | null;

    // Actions
    setFormula: (formula: string) => void;
    setSymbol: (symbol: string) => void;
    setTimeframe: (tf: string) => void;
    setCode: (code: string) => void; // Add missing action
    runAlpha: (mode?: 'full' | 'preview') => Promise<void>;
}

export const useAlphaStore = create<AlphaStore>((set, get) => ({
    formula: 'rank(close / delay(close, 5))',
    symbol: 'XAU_USD',
    timeframe: 'H1',
    code: 'rank(close / delay(close, 5))', // Initialize matches formula
    isRunning: false,
    result: null,
    error: null,

    setFormula: (formula: string) => set({ formula }),
    setSymbol: (symbol: string) => set({ symbol }),
    setTimeframe: (timeframe: string) => set({ timeframe }),
    setCode: (code: string) => set({ code }),

    runAlpha: async (mode = 'full') => {
        const { formula, symbol, timeframe } = get();

        // Don't run empty formula
        if (!formula.trim()) return;

        // For preview, don't set global loading if handled optimistically, 
        // but here we just use isRunning for simplicity or separate isPreviewing.
        if (mode === 'full') {
            set({ isRunning: true, error: null });
        }

        try {
            const endpoint = mode === 'preview' ? '/api/v1/alpha/preview' : '/api/v1/alpha/test';

            // Use apiClient to handle authentication automatically
            const res = await apiClient.post(endpoint, {
                formula,
                symbol,
                timeframe
            });

            if (res.data.status === 'success') {
                set({ result: res.data.data });
                if (mode === 'full') toast.success('Alpha simulation complete');
            } else {
                set({ error: res.data.error || 'Unknown error' });
                if (mode === 'full') toast.error(res.data.error || 'Simulation failed');
            }

        } catch (err: unknown) {
            console.error(err);
            let msg = 'Unknown error';
            
            if (err instanceof ApiError) {
                msg = err.message;
            } else if (err instanceof Error) {
                msg = err.message;
            }
            
            set({ error: msg });
            if (mode === 'full') toast.error(msg);
        } finally {
            if (mode === 'full') {
                set({ isRunning: false });
            }
        }
    }
}));
