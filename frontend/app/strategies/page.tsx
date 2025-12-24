'use client';

import React, { useState } from 'react';
import { useStrategies } from '@/lib/hooks/useStrategies';
import { stopStrategy, startStrategy, deleteStrategy } from '@/lib/api/strategies';
import { Pagination, Modal } from '@/components/common';
import Link from 'next/link';
import { Loader2, Play, Square, Trash2, LayoutDashboard, List as ListIcon } from 'lucide-react';

const StrategiesPage: React.FC = () => {
    // Note: Layout toggler state kept for future extensibility (e.g. detailed view), 
    // defaulting to LIST for now as per requirement.
    const [view, setView] = useState<'LIST' | 'GRID'>('LIST'); 

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
    } = useStrategies();

    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);
    const [processingId, setProcessingId] = useState<string | null>(null);

    const handleToggle = async (id: string, currentlyActive: boolean) => {
        try {
            setProcessingId(id);
            if (currentlyActive) {
                await stopStrategy(id);
            } else {
                await startStrategy(id);
            }
            await refetch();
        } catch (err) {
            alert("Failed to toggle strategy: " + (err instanceof Error ? err.message : String(err)));
        } finally {
            setProcessingId(null);
        }
    };

    const handleDeleteClick = (id: string) => {
        setDeleteId(id);
    };

    const confirmDelete = async () => {
        if (!deleteId) return;

        try {
            setIsDeleting(true);
            await deleteStrategy(deleteId);
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
                   <h1 className="text-4xl font-bold text-center md:text-left text-emerald-400">Active Strategies</h1>
                   <p className="text-gray-400 mt-2">Manage your fleet of automated trading bots.</p>
                </div>
                
                <div className="flex gap-4">
                     {/* View Toggler (Optional, consistent with Journal) */}
                    <div className="bg-gray-800 p-1 rounded-lg flex border border-gray-700 h-fit">
                        <button
                            onClick={() => setView('LIST')}
                            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all duration-300 ${
                                view === 'LIST' 
                                    ? 'bg-emerald-600 text-white shadow-lg' 
                                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                            }`}
                        >
                            <ListIcon size={18} />
                            <span className="font-medium hidden sm:inline">List</span>
                        </button>
                         {/* Placeholder for future Grid/Analytics view */}
                         <div className="px-4 py-2 text-gray-600 cursor-not-allowed hidden sm:flex items-center gap-2">
                            <LayoutDashboard size={18} />
                            <span className="font-medium">Grid</span>
                         </div>
                    </div>

                    <Link
                        href="/strategies/new"
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out flex items-center gap-2 h-fit"
                    >
                        <span>+ Launch Strategy</span>
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
                    No active strategies found. Launch one above!
                </div>
            ) : (
                <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden shadow-xl animate-in fade-in duration-500">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-gray-700 bg-gray-800/50">
                                    <th className="text-left py-4 px-6 font-medium text-gray-300">Name / Template</th>
                                    <th className="text-left py-4 px-6 font-medium text-gray-300">Symbol</th>
                                    <th className="text-left py-4 px-6 font-medium text-gray-300">Timeframe</th>
                                    <th className="text-right py-4 px-6 font-medium text-gray-300">Risk</th>
                                    <th className="text-center py-4 px-6 font-medium text-gray-300">Status</th>
                                    <th className="text-right py-4 px-6 font-medium text-gray-300">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {strategies.map((strategy) => (
                                    <tr
                                        key={strategy.id}
                                        className="border-b border-gray-800 hover:bg-gray-800/30 transition-colors"
                                    >
                                        <td className="py-4 px-6">
                                            <div className="font-semibold text-gray-200">{strategy.name}</div>
                                            <div className="text-xs text-gray-500 font-mono">{strategy.template_id}</div>
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className="font-medium text-gray-300">
                                                 {strategy.config_json?.symbol || 'N/A'}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className="bg-gray-800 text-gray-300 py-1 px-2 rounded text-xs font-mono">
                                                {strategy.config_json?.timeframe || 'N/A'}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6 text-right">
                                             <span className="font-mono font-bold text-red-400">
                                                ${strategy.risk_settings?.max_risk_usd || 'N/A'}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6 text-center">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                                                strategy.is_active
                                                    ? 'bg-green-900/50 text-green-400'
                                                    : 'bg-gray-700 text-gray-400'
                                            }`}>
                                                {strategy.is_active ? "RUNNING" : "STOPPED"}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6 text-right">
                                            <div className="flex justify-end gap-3">
                                                 <button
                                                    onClick={() => handleToggle(strategy.id, strategy.is_active)}
                                                    disabled={!!processingId}
                                                    className="text-gray-400 hover:text-emerald-400 transition-colors"
                                                    title={strategy.is_active ? "Stop Strategy" : "Start Strategy"}
                                                >
                                                    {processingId === strategy.id ? (
                                                        <Loader2 className="h-5 w-5 animate-spin" />
                                                    ) : strategy.is_active ? (
                                                        <Square className="h-5 w-5 fill-current text-orange-500" />
                                                    ) : (
                                                        <Play className="h-5 w-5 fill-current text-emerald-500" />
                                                    )}
                                                </button>
                                                
                                                <button
                                                    onClick={() => handleDeleteClick(strategy.id)}
                                                    disabled={!!processingId}
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
                title="Confirm Delete"
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
                    <p>Are you sure you want to delete this strategy?</p>
                    <p className="text-sm text-gray-500 mt-2">This will permanently remove the strategy configuration and stop any active trading.</p>
                </div>
            </Modal>
        </div>
    );
};

export default StrategiesPage;
