'use client';

import { useState } from 'react';
import { TransactionType } from '@/lib/api/types';

interface FilterBarProps {
    onFilterChange: (filters: TransactionFilters) => void;
}

export interface TransactionFilters {
    type: TransactionType | 'ALL';
    dateFrom: string;
    dateTo: string;
}

export function FilterBar({ onFilterChange }: FilterBarProps) {
    const [filters, setFilters] = useState<TransactionFilters>({
        type: 'ALL',
        dateFrom: '',
        dateTo: ''
    });

    const handleApply = () => {
        onFilterChange(filters);
    };

    const handleReset = () => {
        const resetFilters: TransactionFilters = {
            type: 'ALL',
            dateFrom: '',
            dateTo: ''
        };
        setFilters(resetFilters);
        onFilterChange(resetFilters);
    };

    return (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-4">
            <div className="flex flex-wrap gap-4 items-end">
                {/* Type Filter */}
                <div className="flex-1 min-w-[200px]">
                    <label htmlFor="type" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Type
                    </label>
                    <select
                        id="type"
                        value={filters.type}
                        onChange={(e) => setFilters({ ...filters, type: e.target.value as TransactionType | 'ALL' })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                        <option value="ALL">All Types</option>
                        <option value={TransactionType.DEPOSIT}>Deposit</option>
                        <option value={TransactionType.WITHDRAWAL}>Withdrawal</option>
                    </select>
                </div>

                {/* Date From */}
                <div className="flex-1 min-w-[200px]">
                    <label htmlFor="dateFrom" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        From Date
                    </label>
                    <input
                        id="dateFrom"
                        type="date"
                        value={filters.dateFrom}
                        onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    />
                </div>

                {/* Date To */}
                <div className="flex-1 min-w-[200px]">
                    <label htmlFor="dateTo" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        To Date
                    </label>
                    <input
                        id="dateTo"
                        type="date"
                        value={filters.dateTo}
                        onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    />
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                    <button
                        onClick={handleApply}
                        className="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    >
                        Apply
                    </button>
                    <button
                        onClick={handleReset}
                        className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    >
                        Reset
                    </button>
                </div>
            </div>
        </div>
    );
}
