'use client';

import React, { useState } from 'react';
import { useSavedStrategies } from '@/lib/hooks/useSavedStrategies';
import { deleteSavedStrategy } from '@/lib/api/saved_strategies';
import { Pagination, Modal } from '@/components/common';
import Link from 'next/link';
import { Loader2, Trash2, LayoutDashboard, List as ListIcon, FileCode, Edit } from 'lucide-react';
import { format } from 'date-fns';

const StrategiesPage: React.FC = () => {


    const {
        strategies,
        loading,
        error,
        page,
        setPage,
        perPage,
        setPerPage,
        total,
        totalPages,
        refetch
    } = useSavedStrategies();

    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const handleDeleteClick = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        e.preventDefault();
        setDeleteId(id);
    };

    const confirmDelete = async () => {
        if (!deleteId) return;

        try {
            setIsDeleting(true);
            await deleteSavedStrategy(deleteId);
            await refetch();
            setDeleteId(null);
        } catch (err) {
            alert('Failed to delete strategy: ' + (err instanceof Error ? err.message : 'Unknown error'));
        } finally {
            setIsDeleting(false);
        }
    };

    if (loading && strategies.length === 0) {
        return (
            <div className="flex justify-center items-center h-screen bg-gray-900">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-4 bg-gray-900 min-h-screen text-white">
            <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
                <div>
                   <h1 className="text-4xl font-bold text-center md:text-left text-emerald-400">Strategy Library</h1>
                   <p className="text-gray-400 mt-2">Manage your algorithmic blueprints and backtests.</p>
                </div>
                
                <div className="flex gap-4">


                    <Link
                        href="/strategies/editor"
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out flex items-center gap-2 h-fit"
                    >
                        <FileCode className="h-5 w-5" />
                        <span>Open Editor</span>
                    </Link>
                </div>
            </div>

            {error && (
                <div className="bg-red-900/20 border border-red-500/50 text-red-500 p-4 rounded-lg mb-6">
                    Error: {error}
                </div>
            )}

            {strategies.length === 0 && !loading ? (
                <div className="text-center text-gray-500 text-2xl mt-20">
                    No strategies found. Open the Editor to create one!
                </div>
            ) : (
                <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden shadow-xl animate-in fade-in duration-500">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-gray-700 bg-gray-800/50">
                                    <th className="text-left py-4 px-6 font-medium text-gray-300">Name</th>
                                    <th className="text-left py-4 px-6 font-medium text-gray-300">Description</th>
                                    <th className="text-left py-4 px-6 font-medium text-gray-300">Last Updated</th>
                                    <th className="text-right py-4 px-6 font-medium text-gray-300">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {strategies.map((strategy) => (
                                    <tr
                                        key={strategy.id}
                                        className="border-b border-gray-800 hover:bg-gray-800/30 transition-colors cursor-pointer"
                                        // Row click goes to editor
                                        onClick={() => window.location.href = `/strategies/editor?id=${strategy.id}`}
                                    >
                                        <td className="py-4 px-6">
                                            <div className="font-semibold text-gray-200 flex items-center gap-2">
                                                <FileCode className="h-4 w-4 text-emerald-500" />
                                                {strategy.name}
                                            </div>
                                            <div className="text-xs text-gray-600 font-mono mt-0.5">{strategy.id}</div>
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className="text-gray-400 text-sm">
                                                 {strategy.description || '-'}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className="text-gray-400 text-sm">
                                                {strategy.updated_at ? format(new Date(strategy.updated_at), 'MMM dd, yyyy') : 'N/A'}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6 text-right">
                                            <div className="flex justify-end gap-3" onClick={(e) => e.stopPropagation()}>
                                                <Link
                                                    href={`/strategies/editor?id=${strategy.id}`}
                                                    className="text-gray-400 hover:text-emerald-400 transition-colors"
                                                    title="Edit Strategy"
                                                >
                                                    <Edit className="h-5 w-5" />
                                                </Link>
                                                
                                                <button
                                                    onClick={(e) => handleDeleteClick(strategy.id, e)}
                                                    className="text-gray-400 hover:text-red-400 transition-colors"
                                                    title="Delete Strategy"
                                                >
                                                    <Trash2 className="h-5 w-5" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <Pagination
                        currentPage={page}
                        totalPages={totalPages}
                        perPage={perPage}
                        total={total}
                        onPageChange={setPage}
                        onPerPageChange={setPerPage}
                    />
                </div>
            )}

            <Modal
                isOpen={!!deleteId}
                onClose={() => setDeleteId(null)}
                title="Delete Strategy"
                footer={
                    <>
                        <button
                            onClick={() => setDeleteId(null)}
                            className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors border border-gray-600"
                            disabled={isDeleting}
                        >
                            Cancel
                        </button>
                        <button
                            onClick={confirmDelete}
                            className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors flex items-center gap-2"
                            disabled={isDeleting}
                        >
                            {isDeleting ? 'Deleting...' : 'Delete'}
                        </button>
                    </>
                }
            >
                <div className="text-gray-300">
                    <p>Are you sure you want to delete this strategy blueprint?</p>
                    <p className="text-sm text-yellow-500/80 mt-2 bg-yellow-900/20 p-2 rounded border border-yellow-900/50">
                        Warning: This will also delete all associated Deployments and Chat Sessions.
                    </p>
                </div>
            </Modal>
        </div>
    );
};

export default StrategiesPage;


