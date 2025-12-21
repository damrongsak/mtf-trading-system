import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useJournalEntries } from '@/lib/hooks';
import { deleteJournalEntry } from '@/lib/api/journal';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { Pagination, Modal } from '@/components/common';
import JournalFilterBar from '@/components/journal/JournalFilterBar';

const JournalList: React.FC = () => {
  const { authToken } = useAuth();
  const { 
    entries: journalEntries, 
    loading, 
    error,
    page,
    setPage,
    perPage,
    setPerPage,
    total,
    totalPages,
    filters,
    setFilters,
    refetch
  } = useJournalEntries();

  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteClick = (id: string) => {
    setDeleteId(id);
  };

  const confirmDelete = async () => {
    if (!deleteId) return;
    
    try {
      setIsDeleting(true);
      await deleteJournalEntry(deleteId);
      await refetch();
      setDeleteId(null);
    } catch (err) {
      alert('Failed to delete entry: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsDeleting(false);
    }
  };

  if (!authToken) {
    return (
      <div className="flex justify-center items-center h-64 text-xl text-red-500">
        Authentication token not found. Please log in.
      </div>
    );
  }

  if (loading) {
    return (
        <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
        </div>
    );
  }

  if (error) {
    return <div className="flex justify-center items-center h-64 text-xl text-red-500">Error: {error}</div>;
  }

  return (
    <div className="animate-in fade-in duration-500">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-white"></h1>
        <Link 
          href="/journal/new"
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out flex items-center gap-2"
        >
          <span>+ New Entry</span>
        </Link>
      </div>

      <JournalFilterBar currentFilters={filters} onFilterChange={setFilters} />

      {journalEntries.length === 0 ? (
        <div className="text-center text-gray-500 text-2xl mt-20">
            No journal entries found. Start by creating a new one!
        </div>
      ) : (
        <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden shadow-xl">
             <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-gray-700 bg-gray-800/50">
                            <th className="text-left py-4 px-6 font-medium text-gray-300">Date</th>
                            <th className="text-left py-4 px-6 font-medium text-gray-300">Symbol</th>
                            <th className="text-left py-4 px-6 font-medium text-gray-300">Direction</th>
                            <th className="text-left py-4 px-6 font-medium text-gray-300">Game Level</th>
                            <th className="text-right py-4 px-6 font-medium text-gray-300">P&L</th>
                            <th className="text-right py-4 px-6 font-medium text-gray-300">R-Multiple</th>
                            <th className="text-right py-4 px-6 font-medium text-gray-300">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {journalEntries.map((entry) => (
                            <tr 
                                key={entry.id} 
                                className="border-b border-gray-800 hover:bg-gray-800/30 transition-colors"
                            >
                                <td className="py-4 px-6">
                                    <div className="text-sm text-gray-200">
                                        {new Date(entry.created_at).toLocaleDateString()}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        {formatDistanceToNow(new Date(entry.created_at), { addSuffix: true })}
                                    </div>
                                </td>
                                <td className="py-4 px-6">
                                    <span className="font-semibold text-gray-200">{entry.symbol}</span>
                                </td>
                                <td className="py-4 px-6">
                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                                        entry.direction === 'LONG' 
                                            ? 'bg-green-900/50 text-green-400' 
                                            : 'bg-red-900/50 text-red-400'
                                    }`}>
                                        {entry.direction}
                                    </span>
                                </td>
                                <td className="py-4 px-6">
                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-bold ${
                                        entry.game_level === 'A_GAME' ? 'bg-green-500/20 text-green-400' : 
                                        entry.game_level === 'B_GAME' ? 'bg-yellow-500/20 text-yellow-400' : 
                                        entry.game_level === 'C_GAME' ? 'bg-red-500/20 text-red-400' :
                                        'bg-gray-700 text-gray-400'
                                    }`}>
                                        {entry.game_level?.replace('_', ' ') || 'N/A'}
                                    </span>
                                </td>
                                <td className="py-4 px-6 text-right">
                                    <span className={`font-mono font-bold ${
                                        entry.pnl_amount && entry.pnl_amount >= 0 ? 'text-green-500' : 
                                        entry.pnl_amount && entry.pnl_amount < 0 ? 'text-red-500' : 'text-gray-500'
                                    }`}>
                                        {entry.pnl_amount != null ? `$${entry.pnl_amount.toFixed(2)}` : '-'}
                                    </span>
                                </td>
                                <td className="py-4 px-6 text-right">
                                    <span className="font-medium text-gray-300">
                                        {entry.pnl_r != null ? `${entry.pnl_r.toFixed(2)}R` : '-'}
                                    </span>
                                </td>
                                <td className="py-4 px-6 text-right">
                                    <div className="flex justify-end gap-3">
                                        <Link 
                                            href={`/journal/${entry.id}/edit`}
                                            className="text-gray-400 hover:text-emerald-400 transition-colors text-sm font-medium"
                                        >
                                            Edit
                                        </Link>
                                        <button
                                            onClick={() => handleDeleteClick(entry.id)}
                                            className="text-gray-400 hover:text-red-400 transition-colors text-sm font-medium"
                                        >
                                            Delete
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

      {/* Delete Confirmation Modal */}
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
              <p>Are you sure you want to delete this journal entry?</p>
              <p className="text-sm text-gray-500 mt-2">This action cannot be undone.</p>
          </div>
      </Modal>
    </div>
  );
};

export default JournalList;
