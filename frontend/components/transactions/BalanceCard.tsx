'use client';

import { useBalance } from '@/lib/hooks';

interface BalanceCardProps {
    fundId: string | null;
}

export function BalanceCard({ fundId }: BalanceCardProps) {
    const { balance, currency, loading, error, refetch } = useBalance(fundId);

    if (error) {
        return (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
                <p className="text-red-600 dark:text-red-400">Error loading balance: {error}</p>
                <button
                    onClick={refetch}
                    className="mt-2 text-sm text-red-700 dark:text-red-300 hover:underline"
                >
                    Try again
                </button>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-br from-primary/10 to-primary/5 dark:from-primary/20 dark:to-primary/10 border border-primary/20 dark:border-primary/30 rounded-lg p-6">
            <div className="flex items-center justify-between">
                <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                        Portfolio Balance
                    </p>
                    {loading ? (
                        <div className="h-10 w-48 bg-gray-200 dark:bg-gray-700 animate-pulse rounded"></div>
                    ) : (
                        <p className={`text-4xl font-bold ${balance >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                            {currency} {balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                    )}
                </div>
                <button
                    onClick={refetch}
                    disabled={loading}
                    className="p-2 rounded-lg hover:bg-white/50 dark:hover:bg-gray-800/50 transition-colors disabled:opacity-50"
                    aria-label="Refresh balance"
                >
                    <svg
                        className={`w-6 h-6 text-gray-600 dark:text-gray-400 ${loading ? 'animate-spin' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                    </svg>
                </button>
            </div>
        </div>
    );
}
