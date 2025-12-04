'use client';

import { useState } from 'react';
import { updateTransaction } from '@/lib/api';
import { Transaction, CreateTransactionDto, TransactionType } from '@/lib/api/types';

interface EditDialogProps {
    transaction: Transaction;
    onSuccess: () => void;
    onCancel: () => void;
}

export function EditDialog({ transaction, onSuccess, onCancel }: EditDialogProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [formData, setFormData] = useState({
        type: transaction.type,
        amount: transaction.amount.toString(),
        description: transaction.description || '',
        transaction_date: new Date(transaction.transaction_date).toISOString().split('T')[0]
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const transactionData: CreateTransactionDto = {
                fund_id: transaction.fund_id,
                type: formData.type,
                amount: parseFloat(formData.amount),
                description: formData.description || undefined,
                transaction_date: new Date(formData.transaction_date).toISOString(),
                currency: transaction.currency,
                status: transaction.status
            };

            await updateTransaction(transaction.id, transactionData);
            onSuccess();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update transaction');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Edit Transaction
                </h3>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                        </div>
                    )}

                    <div>
                        <label htmlFor="type" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Type
                        </label>
                        <select
                            id="type"
                            value={formData.type}
                            onChange={(e) => setFormData({ ...formData, type: e.target.value as TransactionType })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                            required
                        >
                            <option value={TransactionType.DEPOSIT}>Deposit</option>
                            <option value={TransactionType.WITHDRAWAL}>Withdrawal</option>
                        </select>
                    </div>

                    <div>
                        <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Amount ({transaction.currency})
                        </label>
                        <input
                            id="amount"
                            type="number"
                            step="0.01"
                            min="0.01"
                            value={formData.amount}
                            onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                            placeholder="0.00"
                            required
                        />
                    </div>

                    <div>
                        <label htmlFor="date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Date
                        </label>
                        <input
                            id="date"
                            type="date"
                            value={formData.transaction_date}
                            onChange={(e) => setFormData({ ...formData, transaction_date: e.target.value })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                            required
                        />
                    </div>

                    <div>
                        <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Description
                        </label>
                        <textarea
                            id="description"
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                            rows={3}
                            placeholder="Enter transaction notes..."
                        />
                    </div>

                    <div className="flex justify-end gap-3 pt-4">
                        <button
                            type="button"
                            onClick={onCancel}
                            disabled={loading}
                            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
                        >
                            {loading ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
