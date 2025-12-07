import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { useJournalEntries } from '@/lib/hooks';
import Link from 'next/link';

const JournalList: React.FC = () => {
  const { authToken } = useAuth();
  const { entries: journalEntries, loading, error } = useJournalEntries();

  if (!authToken) {
    return (
      <div className="flex justify-center items-center h-64 text-xl text-red-500">
        Authentication token not found. Please log in.
      </div>
    );
  }

  if (loading) {
    return <div className="flex justify-center items-center h-64 text-xl text-emerald-500">Loading journal entries...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center h-64 text-xl text-red-500">Error: {error}</div>;
  }

  return (
    <div className="animate-in fade-in duration-500">
      <div className="flex justify-end mb-6">
        <Link 
          href="/journal/new"
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out flex items-center gap-2"
        >
          <span>+ New Entry</span>
        </Link>
      </div>

      {journalEntries.length === 0 ? (
        <div className="text-center text-gray-500 text-2xl mt-20">
          No journal entries found. Start by creating a new one!
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {journalEntries.map((entry) => (
            <div key={entry.id} className="bg-gray-800/80 backdrop-blur p-6 rounded-xl shadow-md hover:shadow-xl transition-all duration-300 border border-gray-700 hover:border-emerald-500/50 group">
              <div className="flex justify-between items-start mb-3">
                 <h2 className="text-2xl font-semibold text-emerald-300 group-hover:text-emerald-200">{entry.symbol}</h2>
                 <span className={`px-2 py-1 rounded text-xs font-bold ${entry.direction === 'LONG' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                    {entry.direction}
                 </span>
              </div>
              
              <div className="space-y-2 mb-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400 text-sm">P&L</span>
                    <span className={`font-bold font-mono ${entry.pnl_amount && entry.pnl_amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        ${entry.pnl_amount?.toFixed(2) || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400 text-sm">R-Multiple</span>
                    <span className="font-medium text-gray-200">{entry.pnl_r?.toFixed(2) || 'N/A'}R</span>
                  </div>
                   <div className="flex justify-between items-center">
                    <span className="text-gray-400 text-sm">Game Level</span>
                    <span className={`font-bold text-xs px-2 py-0.5 rounded ${
                        entry.game_level === 'A_GAME' ? 'bg-green-500/20 text-green-400' : 
                        entry.game_level === 'B_GAME' ? 'bg-yellow-500/20 text-yellow-400' : 
                        'bg-red-500/20 text-red-400'
                    }`}>
                        {entry.game_level?.replace('_', ' ') || 'N/A'}
                    </span>
                  </div>
              </div>

              <div className="pt-4 border-t border-gray-700 flex justify-between items-center">
                 <span className="text-gray-500 text-xs">{new Date(entry.created_at).toLocaleDateString()}</span>
                 {/* <Link href={`/journal/${entry.id}`} className="text-emerald-500 text-sm hover:underline">View Details</Link> */}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default JournalList;
