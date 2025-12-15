import { useState } from 'react';
import { runMarketObserver, AIReportResponse } from '../api/ai';
import { ApiError } from '../api/errors';

export interface UseAIAnalystReturn {
    report: string | null;
    timestamp: string | null;
    loading: boolean;
    error: string | null;
    generateReport: (input?: string) => Promise<void>;
}

export function useAIAnalyst(): UseAIAnalystReturn {
    const [report, setReport] = useState<string | null>(null);
    const [timestamp, setTimestamp] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const generateReport = async (input?: string) => {
        setLoading(true);
        setError(null);
        try {
            const response: AIReportResponse = await runMarketObserver(input);
            setReport(response.report);
            try {
                setTimestamp(new Date(response.timestamp).toLocaleString());
            } catch (e) {
                setTimestamp(response.timestamp);
            }
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Failed to generate report');
            }
        } finally {
            setLoading(false);
        }
    };

    return {
        report,
        timestamp,
        loading,
        error,
        generateReport
    };
}
