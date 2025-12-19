import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { useJournalEntries } from '@/lib/hooks';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { Pagination } from '@/components/common';
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
    setFilters
  } = useJournalEntries();

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
        <h1 className="text-3xl font-bold text-white">Trading Journal</h1>
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
                                    <Link 
                                        href={`/journal/${entry.id}/edit`}
                                        className="text-gray-500 hover:text-emerald-400 transition-colors text-sm"
                                    >
                                        Edit
                                    </Link>
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
    </div>
  );
};

export default JournalList;
