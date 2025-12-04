'use client';

import { useState } from 'react';
import { BalanceCard, TransactionList, TransactionForm } from '@/components/transactions';
import { useTransactions } from '@/lib/hooks';
import { useFunds } from '@/lib/hooks/useFunds';

export default function TransactionsPage() {
    const [showForm, setShowForm] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const perPage = 10;

    // Get user's funds
    const { funds, loading: fundsLoading } = useFunds();
    const fundId = funds.length > 0 ? funds[0].id : null;

    // Get transactions
    const { transactions, loading, error, refetch, pagination } = useTransactions(fundId, currentPage, perPage);

    const handleTransactionCreated = () => {
        setShowForm(false);
        refetch();
    };

    if (fundsLoading) {
        return (
            <div className="flex justify-center items-center min-h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (!fundId) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                    <h2 className="text-lg font-medium text-yellow-800 dark:text-yellow-400 mb-2">
                        No Fund Found
                    </h2>
                    <p className="text-sm text-yellow-700 dark:text-yellow-300">
                        Please create a fund in Settings before managing transactions.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    Transactions
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    Manage your fund deposits and withdrawals
                </p>
            </div>

            {/* Balance Card */}
            <div className="mb-8">
                <BalanceCard fundId={fundId} />
            </div>

            {/* Action Buttons */}
            <div className="mb-6 flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                    Transaction History
                </h2>
                <button
                    onClick={() => setShowForm(true)}
                    className="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                >
                    + Add Transaction
                </button>
            </div>

            {/* Transaction Form Modal */}
            {showForm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                            New Transaction
                        </h3>
                        <TransactionForm
                            fundId={fundId}
                            onSuccess={handleTransactionCreated}
                            onCancel={() => setShowForm(false)}
                        />
                    </div>
                </div>
            )}

            {/* Transaction List */}
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                {error ? (
                    <div className="p-6">
                        <p className="text-red-600 dark:text-red-400">Error: {error}</p>
                        <button
                            onClick={refetch}
                            className="mt-2 text-sm text-primary hover:underline"
                        >
                            Try again
                        </button>
                    </div>
                ) : (
                    <>
                        <TransactionList transactions={transactions} loading={loading} />

                        {/* Pagination */}
                        {pagination.totalPages > 1 && (
                            <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-between">
                                <div className="text-sm text-gray-700 dark:text-gray-300">
                                    Showing {((currentPage - 1) * perPage) + 1} to {Math.min(currentPage * perPage, pagination.total)} of {pagination.total} transactions
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                        disabled={currentPage === 1}
                                        className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        Previous
                                    </button>
                                    <button
                                        onClick={() => setCurrentPage(p => Math.min(pagination.totalPages, p + 1))}
                                        disabled={currentPage === pagination.totalPages}
                                        className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        Next
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
