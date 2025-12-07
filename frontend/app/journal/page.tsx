'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import JournalList from '@/components/journal/JournalList';
import JournalAnalytics from '@/components/journal/JournalAnalytics';
import { LayoutDashboard, List as ListIcon } from 'lucide-react';

type ViewMode = 'LIST' | 'ANALYTICS';

const JournalPage: React.FC = () => {
  const { authToken } = useAuth();
  const [view, setView] = useState<ViewMode>('LIST');

  if (!authToken) {
    return (
      <div className="flex justify-center items-center min-h-screen text-xl text-red-500">
        Authentication token not found. Please log in.
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 bg-gray-900 min-h-screen text-white">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
          <h1 className="text-4xl font-bold text-center md:text-left text-emerald-400">Trading Journal</h1>
          
          {/* View Toggler */}
          <div className="bg-gray-800 p-1 rounded-lg flex border border-gray-700">
              <button
                  onClick={() => setView('LIST')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all duration-300 ${
                      view === 'LIST' 
                          ? 'bg-emerald-600 text-white shadow-lg' 
                          : 'text-gray-400 hover:text-white hover:bg-gray-700'
                  }`}
              >
                  <ListIcon size={18} />
                  <span className="font-medium">Entries</span>
              </button>
              <button
                  onClick={() => setView('ANALYTICS')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all duration-300 ${
                      view === 'ANALYTICS' 
                          ? 'bg-emerald-600 text-white shadow-lg' 
                          : 'text-gray-400 hover:text-white hover:bg-gray-700'
                  }`}
              >
                  <LayoutDashboard size={18} />
                  <span className="font-medium">Analytics</span>
              </button>
          </div>
      </div>

      {view === 'LIST' ? <JournalList /> : <JournalAnalytics />}
    </div>
  );
};

export default JournalPage;
