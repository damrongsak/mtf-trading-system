

'use client';

import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { useJournalEntries } from '@/lib/hooks';
import Link from 'next/link';

const JournalListPage: React.FC = () => {
  const { authToken } = useAuth();
  const { entries: journalEntries, loading, error } = useJournalEntries();

  if (!authToken) {
    return (
      <div className="flex justify-center items-center min-h-screen text-xl text-red-500">
        Authentication token not found. Please log in.
      </div>
    );
  }

  if (loading) {
    return <div className="flex justify-center items-center min-h-screen text-xl">Loading journal entries...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center min-h-screen text-xl text-red-500">Error: {error}</div>;
  }

  return (
    <div className="container mx-auto p-4 bg-gray-900 min-h-screen text-white">
      <h1 className="text-4xl font-bold mb-8 text-center text-emerald-400">Trading Journal</h1>
      <div className="flex justify-end mb-6">
        <Link 
          href="/journal/new"
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out"
        >
          Create New Entry
        </Link>
      </div>

      {journalEntries.length === 0 ? (
        <div className="text-center text-gray-500 text-2xl mt-20">
          No journal entries found. Start by creating a new one!
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {journalEntries.map((entry) => (
            <div key={entry.id} className="bg-gray-800 p-6 rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 ease-in-out border border-gray-700">
              <h2 className="text-2xl font-semibold mb-3 text-emerald-300">{entry.symbol} - {entry.direction}</h2>
              <p className="text-gray-400 mb-2">P&L: <span className={`font-bold ${entry.pnl_amount && entry.pnl_amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>${entry.pnl_amount?.toFixed(2) || 'N/A'}</span></p>
              <p className="text-gray-400 mb-2">R-Multiple: <span className="font-medium">{entry.pnl_r?.toFixed(2) || 'N/A'}</span></p>
              <p className="text-gray-400 mb-2">Game Level: <span className={`font-medium ${entry.game_level === 'A_GAME' ? 'text-green-400' : entry.game_level === 'B_GAME' ? 'text-yellow-400' : 'text-red-400'}`}>{entry.game_level?.replace('_', ' ') || 'N/A'}</span></p>
              <p className="text-gray-500 text-sm mt-4">Created: {new Date(entry.created_at).toLocaleString()}</p>
              {/* <Link href={`/journal/${entry.id}`}>
                <a className="mt-4 inline-block bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out">
                  View Details
                </a>
              </Link> */}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default JournalListPage;
