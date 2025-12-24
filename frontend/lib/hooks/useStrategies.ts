import { useState, useEffect, useCallback } from 'react';
import { getStrategies } from '../api/strategies';
import { StrategyResponse } from '../api/types';
import { ApiError } from '../api/errors';

interface UseStrategiesReturn {
    strategies: StrategyResponse[];
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
    total: number;
    page: number;
    setPage: (page: number) => void;
    perPage: number;
    setPerPage: (perPage: number) => void;
    totalPages: number;
}

/**
 * Custom hook to fetch strategies with pagination
 */
export function useStrategies(initialPage: number = 1, initialPerPage: number = 10): UseStrategiesReturn {
    const [strategies, setStrategies] = useState<StrategyResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(initialPage);
    const [perPage, setPerPage] = useState(initialPerPage);
    const [totalPages, setTotalPages] = useState(0);

    const fetchStrategies = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            // NOTE: getStrategies currently returns all items or paginated response.
            // We will handle Client-Side pagination for now if the API returns an array,
            // or Server-Side if it returns a PaginatedResponse.
            // The current getStrategies implementation handles the response wrapper.
            // For strictly client-side pagination wrapping:
            const data = await getStrategies();

            // Assume Response is ALL items for now based on current backend implementation
            // We simulate pagination here for consistency with the hook interface
            // UNLESS the backend was updated to support ?page= query params which it is partially (in code)
            // but client getStrategies doesn't pass params yet.

            // Let's implement Client-Side slicing here to match the "Table with Pagination" requirement
            // while keeping the hook interface ready for Server-Side.

            setTotal(data.length);
            setTotalPages(Math.ceil(data.length / perPage));

            const start = (page - 1) * perPage;
            const end = start + perPage;
            setStrategies(data.slice(start, end));

        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Failed to fetch strategies');
            }
        } finally {
            setLoading(false);
        }
    }, [page, perPage]);

    useEffect(() => {
        fetchStrategies();
    }, [fetchStrategies]);

    return {
        strategies,
        loading,
        error,
        refetch: fetchStrategies,
        total,
        page,
        setPage,
        perPage,
        setPerPage,
        totalPages
    };
}
