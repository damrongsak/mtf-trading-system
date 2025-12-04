'use client';

import { Transaction, TransactionType } from '@/lib/api/types';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface BalanceChartProps {
    transactions: Transaction[];
}

export function BalanceChart({ transactions }: BalanceChartProps) {
    // Calculate cumulative balance over time
    const sortedTransactions = [...transactions].sort(
        (a, b) => new Date(a.transaction_date).getTime() - new Date(b.transaction_date).getTime()
    );

    const chartData = sortedTransactions.reduce((acc, t) => {
        const lastBalance = acc.length > 0 ? acc[acc.length - 1].balance : 0;
        const amount = t.type === TransactionType.DEPOSIT ? t.amount : -t.amount;
        const newBalance = lastBalance + amount;

        acc.push({
            date: new Date(t.transaction_date).toLocaleDateString(),
            balance: newBalance,
            amount: amount
        });

        return acc;
    }, [] as Array<{ date: string; balance: number; amount: number }>);

    if (chartData.length === 0) {
        return (
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Balance History
                </h3>
                <p className="text-center text-gray-500 dark:text-gray-400 py-12">
                    No data available
                </p>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Balance History
            </h3>
            <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                    <XAxis 
                        dataKey="date" 
                        className="text-gray-600 dark:text-gray-400 text-xs"
                    />
                    <YAxis className="text-gray-600 dark:text-gray-400 text-xs" />
                    <Tooltip 
                        contentStyle={{
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            border: '1px solid rgba(75, 85, 99, 0.5)',
                            borderRadius: '8px'
                        }}
                        labelStyle={{ color: '#9CA3AF' }}
                        itemStyle={{ color: '#10B981' }}
                    />
                    <Legend />
                    <Line 
                        type="monotone" 
                        dataKey="balance" 
                        stroke="#10B981" 
                        strokeWidth={2}
                        dot={{ fill: '#10B981', r: 4 }}
                        name="Balance"
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
