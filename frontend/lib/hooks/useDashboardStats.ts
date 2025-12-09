import { useState, useEffect } from 'react';
import { getDashboardStats } from '../api/dashboard';
import { DashboardStats } from '../api/types';
import { ApiError } from '../api/errors';

interface UseDashboardStatsReturn {
    stats: DashboardStats | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook for fetching dashboard statistics
 * Auto-fetches on mount and provides manual refetch capability
 */
export function useDashboardStats(): UseDashboardStatsReturn {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchStats = async (isBackground = false) => {
        try {
            if (!isBackground) {
                setLoading(true);
            }
            setError(null);
            const data = await getDashboardStats();
            setStats(data);
        } catch (err: unknown) {
            const apiError = err as ApiError;
            setError(apiError.message || 'Failed to fetch dashboard statistics');
        } finally {
            if (!isBackground) {
                setLoading(false);
            }
        }
    };

    useEffect(() => {
        fetchStats();

        // Auto-refresh every 30 seconds
        const interval = setInterval(() => fetchStats(true), 30000);

        return () => clearInterval(interval);
    }, []);

    return { stats, loading, error, refetch: fetchStats };
}
