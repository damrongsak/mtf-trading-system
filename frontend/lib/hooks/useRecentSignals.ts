import { useState, useEffect, useCallback } from 'react';
import { getRecentSignals } from '../api/dashboard';
import { RecentSignal } from '../api/types';
import { ApiError } from '../api/errors';

interface UseRecentSignalsReturn {
    signals: RecentSignal[];
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook for fetching recent trading signals
 * @param limit - Number of signals to fetch (default: 5)
 */
export function useRecentSignals(limit: number = 5, symbols?: string[]): UseRecentSignalsReturn {
    const [signals, setSignals] = useState<RecentSignal[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchSignals = useCallback(async (isBackground = false) => {
        try {
            if (!isBackground) {
                setLoading(true);
            }
            setError(null);
            const data = await getRecentSignals(limit);
            setSignals(data);
        } catch (err: unknown) {
            const apiError = err as ApiError;
            setError(apiError.message || 'Failed to fetch recent signals');
        } finally {
            if (!isBackground) {
                setLoading(false);
            }
        }
    }, [limit, symbols]); // Add symbols to dependency array

    useEffect(() => {
        fetchSignals();

        // Auto-refresh every 30 seconds
        const interval = setInterval(() => fetchSignals(true), 30000);

        return () => clearInterval(interval);
    }, [fetchSignals]);

    return { signals, loading, error, refetch: fetchSignals };
}
