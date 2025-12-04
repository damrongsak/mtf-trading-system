import { useState, useEffect } from 'react';
import { getFunds } from '../api/fund';
import { Fund } from '../api/types';

export interface UseFundsResult {
    funds: Fund[];
    loading: boolean;
    error: string | null;
    refetch: () => void;
}

export function useFunds(): UseFundsResult {
    const [funds, setFunds] = useState<Fund[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchFunds = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getFunds();
            setFunds(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch funds');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFunds();
    }, []);

    return { funds, loading, error, refetch: fetchFunds };
}
