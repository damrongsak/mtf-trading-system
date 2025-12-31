import { useState, useEffect, useCallback } from 'react';
import { getSavedStrategies } from '../api/saved_strategies';
import { SavedStrategy } from '../api/types';
import { ApiError } from '../api/errors';

interface UseSavedStrategiesReturn {
    strategies: SavedStrategy[];
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
    // Pagination fields (Client-side simulation)
    total: number;
    page: number;
    setPage: (page: number) => void;
    perPage: number;
    setPerPage: (perPage: number) => void;
    totalPages: number;
}

/**
 * Custom hook to fetch Saved Strategies (Library)
 */
export function useSavedStrategies(initialPage: number = 1, initialPerPage: number = 10): UseSavedStrategiesReturn {
    const [allStrategies, setAllStrategies] = useState<SavedStrategy[]>([]);
    const [strategies, setStrategies] = useState<SavedStrategy[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Pagination State
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(initialPage);
    const [perPage, setPerPage] = useState(initialPerPage);
    const [totalPages, setTotalPages] = useState(0);

    const fetchStrategies = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch ALL saved strategies
            const data = await getSavedStrategies(false); // false = not just public, get mine

            setAllStrategies(data);
            setTotal(data.length);
            setTotalPages(Math.ceil(data.length / perPage));

        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Failed to fetch saved strategies');
            }
        } finally {
            setLoading(false);
        }
    }, [perPage]); // Dependency on perPage to recalc pages provided total changes

    // Handle Client-Side Pagination Slicing
    useEffect(() => {
        const start = (page - 1) * perPage;
        const end = start + perPage;
        setStrategies(allStrategies.slice(start, end));
        setTotalPages(Math.ceil(allStrategies.length / perPage));
    }, [allStrategies, page, perPage]);

    useEffect(() => {
        fetchStrategies();
    }, [fetchStrategies]);

    return {
        strategies, // The current page slice
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
