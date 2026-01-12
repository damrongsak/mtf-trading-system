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
    startDate: string; // ISO Date String YYYY-MM-DD
    endDate: string;   // ISO Date String YYYY-MM-DD
    code: string; 
    isRunning: boolean;
    result: AlphaResult | null;
    error: string | null;

    // Actions
    setFormula: (formula: string) => void;
    setSymbol: (symbol: string) => void;
    setTimeframe: (tf: string) => void;
    setStartDate: (date: string) => void;
    setEndDate: (date: string) => void;
    setCode: (code: string) => void;
    runAlpha: (mode?: 'full' | 'preview') => Promise<void>;
}

export const useAlphaStore = create<AlphaStore>((set, get) => ({
    formula: 'rank(close / delay(close, 5))',
    symbol: 'XAU_USD',
    timeframe: 'H1',
    startDate: '', // Default empty (backend handles defaults)
    endDate: '',
    code: 'rank(close / delay(close, 5))', 
    isRunning: false,
    result: null,
    error: null,

    setFormula: (formula: string) => set({ formula }),
    setSymbol: (symbol: string) => set({ symbol }),
    setTimeframe: (timeframe: string) => set({ timeframe }),
    setStartDate: (startDate: string) => set({ startDate }),
    setEndDate: (endDate: string) => set({ endDate }),
    setCode: (code: string) => set({ code }),

    runAlpha: async (mode = 'full') => {
        const { formula, symbol, timeframe, startDate, endDate } = get();

        // Don't run empty formula
        if (!formula.trim()) return;

        if (mode === 'full') {
            set({ isRunning: true, error: null });
        }

        try {
            const endpoint = mode === 'preview' ? '/api/v1/alpha/preview' : '/api/v1/alpha/test';

            // Construct payload with optional dates
            // Backend expects ISO strings or just dates. 
            // If inputs are YYYY-MM-DD, we might want to append T00:00:00Z to be safe, 
            // but let's send what the input provides and let backend parse or standardise.
            const payload: any = {
                formula,
                symbol,
                timeframe
            };

            if (startDate) payload.start_date = new Date(startDate).toISOString();
            if (endDate) payload.end_date = new Date(endDate).toISOString();

            // Use apiClient to handle authentication automatically
            const res = await apiClient.post(endpoint, payload);

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
