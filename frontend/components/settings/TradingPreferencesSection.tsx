'use client';

import { useState, useEffect } from 'react';
import { getPreferences, updatePreferences } from '@/lib/api';

const TIMEFRAMES = ['15m', '1H', '4H', 'D', 'W'];
const SESSIONS = ['ASIA', 'LONDON', 'NY'];

export function TradingPreferencesSection() {
  const [selectedTimeframes, setSelectedTimeframes] = useState<string[]>(['4H', '1H', '15m']);
  const [defaultSymbol, setDefaultSymbol] = useState('XAU/USD');
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      const prefs = await getPreferences();
      setSelectedTimeframes(prefs.preferred_timeframes);
      setDefaultSymbol(prefs.default_symbol);
      setSelectedSessions(prefs.session_preferences || []);
    } catch {
      setMessage({ type: 'error', text: 'Failed to load trading preferences' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);

    try {
      await updatePreferences({
        preferred_timeframes: selectedTimeframes,
        default_symbol: defaultSymbol,
        session_preferences: selectedSessions.length > 0 ? selectedSessions : null,
      });
      setMessage({ type: 'success', text: 'Trading preferences saved successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: (error as Error).message || 'Failed to save preferences' });
    } finally {
      setIsSaving(false);
    }
  };

  const toggleTimeframe = (tf: string) => {
    if (selectedTimeframes.includes(tf)) {
      setSelectedTimeframes(selectedTimeframes.filter((t) => t !== tf));
    } else {
      setSelectedTimeframes([...selectedTimeframes, tf]);
    }
  };

  const toggleSession = (session: string) => {
    if (selectedSessions.includes(session)) {
      setSelectedSessions(selectedSessions.filter((s) => s !== session));
    } else {
      setSelectedSessions([...selectedSessions, session]);
    }
  };

  if (isLoading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-900/20 border border-green-700 text-green-400'
              : 'bg-red-900/20 border border-red-700 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Preferred Timeframes */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Preferred Timeframes</h2>
        <div className="flex flex-wrap gap-3">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => toggleTimeframe(tf)}
              className={`px-6 py-3 rounded-lg font-medium transition-all ${
                selectedTimeframes.includes(tf)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Default Symbol */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Default Symbol</h2>
          <input
            type="text"
            value={defaultSymbol}
            onChange={(e) => setDefaultSymbol(e.target.value.toUpperCase())}
            placeholder="e.g., XAU/USD, EUR/USD, SPX"
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          />
      </div>

      {/* Session Preferences */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Session Preferences</h2>
        <p className="text-sm text-gray-400 mb-4">
          Select the trading sessions you prefer to trade during
        </p>
        <div className="flex gap-3">
          {SESSIONS.map((session) => (
            <button
              key={session}
              onClick={() => toggleSession(session)}
              className={`px-6 py-3 rounded-lg font-medium transition-all ${
                selectedSessions.includes(session)
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {session}
            </button>
          ))}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {isSaving ? 'Saving...' : 'Save Trading Preferences'}
        </button>
      </div>
    </div>
  );
}
