import { useState, useEffect, useCallback } from 'react';
import { getDeployments } from '../api/deployments';
import { Deployment, PaginatedResponse } from '../api/types';
import { ApiError } from '../api/errors';

interface UseDeploymentsReturn {
    deployments: Deployment[];
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

export function useDeployments(initialPage: number = 1, initialPerPage: number = 10): UseDeploymentsReturn {
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(initialPage);
    const [perPage, setPerPage] = useState(initialPerPage);
    const [totalPages, setTotalPages] = useState(0);

    const fetchDeployments = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const response = await getDeployments(page, perPage);

            setDeployments(response.data);
            setTotal(response.total);
            setTotalPages(Math.ceil(response.total / perPage));

        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Failed to fetch deployments');
            }
        } finally {
            setLoading(false);
        }
    }, [page, perPage]);

    useEffect(() => {
        fetchDeployments();
    }, [fetchDeployments]);

    return {
        deployments,
        loading,
        error,
        refetch: fetchDeployments,
        total,
        page,
        setPage,
        perPage,
        setPerPage,
        totalPages
    };
}
