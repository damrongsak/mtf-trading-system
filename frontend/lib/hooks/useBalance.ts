import { useState, useEffect, useCallback } from 'react';
import { getBalance } from '../api/transactions';
import { BalanceResponse } from '../api/types';

export interface UseBalanceResult {
    balance: number;
    currency: string;
    loading: boolean;
    error: string | null;
    refetch: () => void;
}

export function useBalance(fundId: string | null): UseBalanceResult {
    const [balance, setBalance] = useState<number>(0);
    const [currency, setCurrency] = useState<string>('USD');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchBalance = useCallback(async () => {
        if (!fundId) {
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const data: BalanceResponse = await getBalance(fundId);
            setBalance(data.balance);
            setCurrency(data.currency);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch balance');
        } finally {
            setLoading(false);
        }
    }, [fundId]);

    useEffect(() => {
        fetchBalance();
    }, [fetchBalance]);

    return { balance, currency, loading, error, refetch: fetchBalance };
}
