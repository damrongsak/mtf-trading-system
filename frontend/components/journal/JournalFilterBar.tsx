'use client';

import { useState, useEffect } from 'react';
import { JournalFilters, getPreferences } from '@/lib/api';
import { logger } from '@/lib/api/app-logger';

interface JournalFilterBarProps {
    currentFilters: JournalFilters;
    onFilterChange: (filters: JournalFilters) => void;
}

export default function JournalFilterBar({ currentFilters, onFilterChange }: JournalFilterBarProps) {
    const [filters, setFilters] = useState<JournalFilters>(currentFilters);
    const [supportedSymbols, setSupportedSymbols] = useState<string[]>([]);

    useEffect(() => {
        const fetchSymbols = async () => {
            try {
                const prefs = await getPreferences();
                if (prefs.default_symbol) {
                     setSupportedSymbols([prefs.default_symbol, "XAU_USD", "EUR_USD", "BTC_USD"]);
                } else {
                     setSupportedSymbols(["XAU_USD", "EUR_USD", "BTC_USD"]);
                }
            } catch (error) {
                logger.error('Failed to load supported symbols', error);
            }
        };
        fetchSymbols();
    }, []);

    const handleApply = () => {
        onFilterChange(filters);
    };

    const handleReset = () => {
        const resetFilters: JournalFilters = {
            search: '',
            direction: 'ALL',
            dateFrom: '',
            dateTo: ''
        };
        setFilters(resetFilters);
        onFilterChange(resetFilters);
    };

    // Auto-apply search on Enter
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleApply();
        }
    };

    return (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 mb-6">
            <div className="flex flex-wrap gap-4 items-end">
                {/* Search / Symbol */}
                <div className="flex-1 min-w-[200px]">
                    <label htmlFor="search" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Search Symbol
                    </label>
                    <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span className="text-gray-500 sm:text-sm">🔍</span>
                        </div>
                        <input
                            id="search"
                            type="text"
                            list="supported-symbols-filter"
                            placeholder="e.g. XAU/USD"
                            value={filters.search || ''}
                            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                            onKeyDown={handleKeyDown}
                            className="w-full pl-10 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400"
                        />
                        <datalist id="supported-symbols-filter">
                            {supportedSymbols.map(s => (
                                <option key={s} value={s} />
                            ))}
                        </datalist>
                    </div>
                </div>

                {/* Direction Filter */}
                <div className="w-[150px]">
                    <label htmlFor="direction" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Direction
                    </label>
                    <select
                        id="direction"
                        value={filters.direction || 'ALL'}
                        onChange={(e) => setFilters({ ...filters, direction: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                        <option value="ALL">All Sides</option>
                        <option value="LONG">LONG 🟢</option>
                        <option value="SHORT">SHORT 🔴</option>
                    </select>
                </div>

                {/* Date From */}
                <div className="w-[160px]">
                    <label htmlFor="dateFrom" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        From Date
                    </label>
                    <input
                        id="dateFrom"
                        type="date"
                        value={filters.dateFrom || ''}
                        onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400"
                    />
                </div>

                {/* Date To */}
                <div className="w-[160px]">
                    <label htmlFor="dateTo" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        To Date
                    </label>
                    <input
                        id="dateTo"
                        type="date"
                        value={filters.dateTo || ''}
                        onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400"
                    />
                </div>

                {/* Buttons */}
                <div className="flex gap-2">
                    <button
                        type="button"
                        onClick={handleApply}
                        className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-colors"
                    >
                        Filter
                    </button>
                    <button
                        type="button"
                        onClick={handleReset}
                        className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-colors"
                    >
                        Reset
                    </button>
                </div>
            </div>
        </div>
    );
}
