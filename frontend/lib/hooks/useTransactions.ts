import { useState, useEffect, useCallback } from 'react';
import { getTransactions } from '../api/transaction';
import { Transaction, PaginatedResponse } from '../api/types';

export interface UseTransactionsResult {
    transactions: Transaction[];
    loading: boolean;
    error: string | null;
    refetch: () => void;
    pagination: {
        page: number;
        perPage: number;
        total: number;
        totalPages: number;
    };
}

export function useTransactions(
    fundId: string | null,
    page: number = 1,
    perPage: number = 10
): UseTransactionsResult {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [pagination, setPagination] = useState({
        page,
        perPage,
        total: 0,
        totalPages: 0
    });

    const fetchTransactions = useCallback(async () => {
        if (!fundId) {
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const data: PaginatedResponse<Transaction> = await getTransactions(fundId, page, perPage);
            setTransactions(data.data);
            setPagination({
                page: data.meta.page || page,
                perPage: data.meta.per_page || perPage,
                total: data.meta.total || 0,
                totalPages: data.meta.total_pages || 0
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch transactions');
        } finally {
            setLoading(false);
        }
    }, [fundId, page, perPage]);

    useEffect(() => {
        fetchTransactions();
    }, [fetchTransactions]);

    return { transactions, loading, error, refetch: fetchTransactions, pagination };
}
