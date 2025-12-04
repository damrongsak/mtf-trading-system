'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api/client';

interface ImportDialogProps {
    fundId: string;
    onSuccess: () => void;
    onCancel: () => void;
}

export function ImportDialog({ fundId, onSuccess, onCancel }: ImportDialogProps) {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<{ imported: number; skipped: number; errors: string[] } | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError(null);
            setResult(null);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) {
            setError('Please select a file');
            return;
        }

        setError(null);
        setLoading(true);

        try {
            const formData = new FormData();
            formData.append('fund_id', fundId);
            formData.append('file', file);

            const response = await apiClient.post('/api/v1/transactions/import', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            const data = response.data.data;
            setResult({
                imported: data.imported_count,
                skipped: data.skipped_count,
                errors: data.errors || []
            });

            if (data.imported_count > 0) {
                setTimeout(() => onSuccess(), 2000);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to import transactions');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Import Transactions
                </h3>

                {!result ? (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                            </div>
                        )}

                        <div>
                            <label htmlFor="file" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Excel File (.xlsx)
                            </label>
                            <input
                                id="file"
                                type="file"
                                accept=".xlsx,.xls"
                                onChange={handleFileChange}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                                required
                            />
                            {file && (
                                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                    Selected: {file.name}
                                </p>
                            )}
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
                                {loading ? 'Importing...' : 'Import'}
                            </button>
                        </div>
                    </form>
                ) : (
                    <div className="space-y-4">
                        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                            <h4 className="font-medium text-green-800 dark:text-green-400 mb-2">Import Complete!</h4>
                            <p className="text-sm text-green-700 dark:text-green-300">
                                Imported: {result.imported} transaction(s)
                            </p>
                            {result.skipped > 0 && (
                                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                                    Skipped: {result.skipped} (duplicates)
                                </p>
                            )}
                        </div>

                        {result.errors.length > 0 && (
                            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                                <h4 className="font-medium text-red-800 dark:text-red-400 mb-2">Errors:</h4>
                                <ul className="text-sm text-red-700 dark:text-red-300 list-disc list-inside">
                                    {result.errors.map((err, idx) => (
                                        <li key={idx}>{err}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <button
                            onClick={onSuccess}
                            className="w-full px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                        >
                            Close
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
