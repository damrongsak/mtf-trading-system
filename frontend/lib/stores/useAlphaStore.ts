import { create } from 'zustand';
import axios from 'axios';
import { toast } from 'sonner';

// Define types locally or import from generated API if verified
// For now, consistent with specs
export interface AlphaResult {
    signal: number[];
    metrics: {
        sharpe?: number;
        ic?: number;
        [key: string]: any;
    };
    timestamps: string[];
}

interface AlphaStore {
    // State
    formula: string;
    symbol: string;
    timeframe: string;
    isRunning: boolean;
    result: AlphaResult | null;
    error: string | null;

    // Actions
    setFormula: (formula: string) => void;
    setSymbol: (symbol: string) => void;
    setTimeframe: (tf: string) => void;
    runAlpha: (mode?: 'full' | 'preview') => Promise<void>;
}

export const useAlphaStore = create<AlphaStore>((set, get) => ({
    formula: 'rank(close / delay(close, 5))',
    symbol: 'XAU_USD',
    timeframe: 'H1',
    isRunning: false,
    result: null,
    error: null,

    setFormula: (formula) => set({ formula }),
    setSymbol: (symbol) => set({ symbol }),
    setTimeframe: (timeframe) => set({ timeframe }),

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

            // Use internal Next.js proxy or direct to API Gateway if configured
            // Assuming Next.js proxies need setup or axios baseURL is set. 
            // lib/api/client sets baseURL usually. Here we use axios directly or need client.
            // Let's assume global axios or import configured client.
            // Better: use relative path if Next rewrites to backend, or full URL.
            // Standard practice here: use configured client.

            // Temporary: direct call assuming proxy in next.config or relative
            const res = await axios.post(endpoint, {
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

        } catch (err: any) {
            console.error(err);
            const msg = err.response?.data?.detail || err.message;
            set({ error: msg });
            if (mode === 'full') toast.error(msg);
        } finally {
            if (mode === 'full') {
                set({ isRunning: false });
            }
        }
    }
}));
