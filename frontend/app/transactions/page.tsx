'use client';

import { useState } from 'react';
import { BalanceCard, TransactionList, TransactionForm, FilterBar, EditDialog, ImportDialog, BalanceChart } from '@/components/transactions';
import { Pagination } from '@/components/common';
import { useTransactions, useFunds, useBalance } from '@/lib/hooks';
import { Transaction } from '@/lib/api/types';
import { exportToCSV, exportToPDF } from '@/lib/utils/exportTransactions';
import { deleteTransaction } from '@/lib/api';
import type { TransactionFilters } from '@/components/transactions/FilterBar';

export default function TransactionsPage() {
    const [showForm, setShowForm] = useState(false);
    const [showImport, setShowImport] = useState(false);
    const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [perPage, setPerPage] = useState(10);
    const [filters, setFilters] = useState<TransactionFilters>({ type: 'ALL', dateFrom: '', dateTo: '' });
    const [showExportMenu, setShowExportMenu] = useState(false);

    // Get user's funds
    const { funds, loading: fundsLoading } = useFunds();
    const fundId = funds.length > 0 ? funds[0].id : null;

    // Get transactions and balance
    const { transactions, loading, error, refetch, pagination } = useTransactions(fundId, currentPage, perPage);
    const { balance, currency } = useBalance(fundId);

    const handleTransactionCreated = () => {
        setShowForm(false);
        refetch();
    };

    const handleTransactionUpdated = () => {
        setEditingTransaction(null);
        refetch();
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this transaction?')) return;
        
        try {
            await deleteTransaction(id);
            refetch();
        } catch (err) {
            alert('Failed to delete transaction: ' + (err instanceof Error ? err.message : 'Unknown error'));
        }
    };

    const handleExportCSV = () => {
        exportToCSV(transactions, `transactions_${new Date().toISOString().split('T')[0]}.csv`);
        setShowExportMenu(false);
    };

    const handleExportPDF = () => {
        exportToPDF(transactions, balance, currency, `transactions_${new Date().toISOString().split('T')[0]}.pdf`);
        setShowExportMenu(false);
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

            {/* Balance Chart */}
            <div className="mb-8">
                <BalanceChart transactions={transactions} />
            </div>

            {/* Filters */}
            <FilterBar onFilterChange={setFilters} />

            {/* Action Buttons */}
            <div className="mb-6 flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                    Transaction History
                </h2>
                <div className="flex gap-2">
                    {/* Export Menu */}
                    <div className="relative">
                        <button
                            onClick={() => setShowExportMenu(!showExportMenu)}
                            disabled={transactions.length === 0}
                            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
                        >
                            Export ▾
                        </button>
                        {showExportMenu && (
                            <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10">
                                <button
                                    onClick={handleExportCSV}
                                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-t-lg"
                                >
                                    Export as CSV
                                </button>
                                <button
                                    onClick={handleExportPDF}
                                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-b-lg"
                                >
                                    Export as PDF
                                </button>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={() => setShowImport(true)}
                        className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    >
                        Import
                    </button>
                    <button
                        onClick={() => setShowForm(true)}
                        className="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    >
                        + Add Transaction
                    </button>
                </div>
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

            {/* Import Dialog */}
            {showImport && (
                <ImportDialog
                    fundId={fundId}
                    onSuccess={() => { setShowImport(false); refetch(); }}
                    onCancel={() => setShowImport(false)}
                />
            )}

            {/* Edit Dialog */}
            {editingTransaction && (
                <EditDialog
                    transaction={editingTransaction}
                    onSuccess={handleTransactionUpdated}
                    onCancel={() => setEditingTransaction(null)}
                />
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
                        <TransactionList 
                            transactions={transactions} 
                            loading={loading}
                            onEdit={setEditingTransaction}
                            onDelete={handleDelete}
                        />

                        {/* Pagination */}
                        <Pagination
                            currentPage={currentPage}
                            totalPages={pagination.totalPages}
                            perPage={perPage}
                            total={pagination.total}
                            onPageChange={setCurrentPage}
                            onPerPageChange={setPerPage}
                        />
                    </>
                )}
            </div>
        </div>
    );
}
