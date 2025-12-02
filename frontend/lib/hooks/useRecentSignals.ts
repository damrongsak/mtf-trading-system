import { useState, useEffect, useCallback } from 'react';
import { getRecentSignals } from '../api/dashboard';
import { RecentSignal, ApiError } from '../api/types';

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
export function useRecentSignals(limit: number = 5): UseRecentSignalsReturn {
    const [signals, setSignals] = useState<RecentSignal[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchSignals = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getRecentSignals(limit);
            setSignals(data);
        } catch (err: unknown) {
            const apiError = err as ApiError;
            setError(apiError.message || 'Failed to fetch recent signals');
        } finally {
            setLoading(false);
        }
    }, [limit]);

    useEffect(() => {
        fetchSignals();
    }, [fetchSignals]);

    return { signals, loading, error, refetch: fetchSignals };
}
