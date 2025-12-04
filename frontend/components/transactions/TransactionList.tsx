'use client';

import { Transaction, TransactionType } from '@/lib/api/types';
import { formatDistanceToNow } from 'date-fns';

interface TransactionListProps {
    transactions: Transaction[];
    loading?: boolean;
    onEdit?: (transaction: Transaction) => void;
    onDelete?: (id: string) => void;
}

export function TransactionList({ transactions, loading, onEdit, onDelete }: TransactionListProps) {
    if (loading) {
        return (
            <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (transactions.length === 0) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500 dark:text-gray-400">No transactions yet</p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                    Create your first transaction to get started
                </p>
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full">
                <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">Date</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">Type</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-700 dark:text-gray-300">Amount</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">Status</th>
                        <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">Description</th>
                        {(onEdit || onDelete) && (
                            <th className="text-right py-3 px-4 font-medium text-gray-700 dark:text-gray-300">Actions</th>
                        )}
                    </tr>
                </thead>
                <tbody>
                    {transactions.map((transaction) => (
                        <tr 
                            key={transaction.id} 
                            className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                        >
                            <td className="py-4 px-4">
                                <div className="text-sm text-gray-900 dark:text-gray-100">
                                    {new Date(transaction.transaction_date).toLocaleDateString()}
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                    {formatDistanceToNow(new Date(transaction.created_at), { addSuffix: true })}
                                </div>
                            </td>
                            <td className="py-4 px-4">
                                <span
                                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                        transaction.type === TransactionType.DEPOSIT
                                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                                    }`}
                                >
                                    {transaction.type}
                                </span>
                            </td>
                            <td className="py-4 px-4 text-right">
                                <span
                                    className={`font-semibold ${
                                        transaction.type === TransactionType.DEPOSIT
                                            ? 'text-green-600 dark:text-green-400'
                                            : 'text-red-600 dark:text-red-400'
                                    }`}
                                >
                                    {transaction.type === TransactionType.DEPOSIT ? '+' : '-'}
                                    {transaction.currency} {transaction.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </span>
                            </td>
                            <td className="py-4 px-4">
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                    {transaction.status}
                                </span>
                            </td>
                            <td className="py-4 px-4">
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                    {transaction.description || '-'}
                                </span>
                            </td>
                            {(onEdit || onDelete) && (
                                <td className="py-4 px-4 text-right">
                                    <div className="flex justify-end gap-2">
                                        {onEdit && (
                                            <button
                                                onClick={() => onEdit(transaction)}
                                                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm"
                                            >
                                                Edit
                                            </button>
                                        )}
                                        {onDelete && (
                                            <button
                                                onClick={() => onDelete(transaction.id)}
                                                className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 text-sm"
                                            >
                                                Delete
                                            </button>
                                        )}
                                    </div>
                                </td>
                            )}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
