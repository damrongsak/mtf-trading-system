import { useState, useCallback } from 'react';

interface UseAsyncReturn<T, Args extends unknown[]> {
    data: T | null;
    loading: boolean;
    error: string | null;
    execute: (...args: Args) => Promise<T | null>;
    reset: () => void;
}

/**
 * Generic hook for handling async operations
 * Useful for API calls that need to be triggered manually (e.g., form submissions)
 */
export function useAsync<T, Args extends unknown[] = unknown[]>(
    asyncFunction: (...args: Args) => Promise<T>
): UseAsyncReturn<T, Args> {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const execute = useCallback(
        async (...args: Args): Promise<T | null> => {
            try {
                setLoading(true);
                setError(null);
                const result = await asyncFunction(...args);
                setData(result);
                return result;
            } catch (err: unknown) {
                const errorMessage = err instanceof Error ? err.message : 'An error occurred';
                setError(errorMessage);
                setData(null);
                return null;
            } finally {
                setLoading(false);
            }
        },
        [asyncFunction]
    );

    const reset = useCallback(() => {
        setData(null);
        setError(null);
        setLoading(false);
    }, []);

    return { data, loading, error, execute, reset };
}
