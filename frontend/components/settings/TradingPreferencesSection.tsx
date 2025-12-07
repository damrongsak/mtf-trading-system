'use client';

import { useState, useEffect } from 'react';
import { getPreferences, updatePreferences } from '@/lib/api';

const TIMEFRAMES = ['15m', '1H', '4H', 'D', 'W'];
const SESSIONS = ['ASIA', 'LONDON', 'NY'];

export function TradingPreferencesSection() {
  const [strategyType, setStrategyType] = useState<string>('MTF_SMC_BASIC');
  const [selectedTimeframes, setSelectedTimeframes] = useState<string[]>(['4H', '1H', '15m']);
  const [defaultSymbol, setDefaultSymbol] = useState('XAU/USD');
  const [supportedSymbols, setSupportedSymbols] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState('');
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
      setStrategyType(prefs.strategy_type);
      setSelectedTimeframes(prefs.preferred_timeframes);
      setDefaultSymbol(prefs.default_symbol);
      setSupportedSymbols(prefs.supported_symbols || []);
      setSelectedSessions(prefs.session_preferences || []);
    } catch (_error) {
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
        supported_symbols: supportedSymbols.length > 0 ? supportedSymbols : null,
        session_preferences: selectedSessions.length > 0 ? selectedSessions : null,
      });
      setMessage({ type: 'success', text: 'Trading preferences saved successfully!' });
    } catch (_error) {
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

  const addSymbol = () => {
    if (newSymbol && !supportedSymbols.includes(newSymbol)) {
      setSupportedSymbols([...supportedSymbols, newSymbol]);
      setNewSymbol('');
    }
  };

  const removeSymbol = (symbol: string) => {
    setSupportedSymbols(supportedSymbols.filter((s) => s !== symbol));
  };

  if (isLoading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  const isBasicStrategy = strategyType === 'MTF_SMC_BASIC';

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
        {isBasicStrategy ? (
          <div>
            <div className="flex items-center gap-3 mb-2">
              <input
                type="text"
                value={defaultSymbol}
                disabled
                className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-400 cursor-not-allowed"
              />
              <span className="text-yellow-500 text-sm">🔒 Locked to XAU/USD for basic strategy</span>
            </div>
            <p className="text-xs text-gray-500">
              Switch to Long/Short, Macro Tactical, or Multi-Asset strategy to trade other symbols
            </p>
          </div>
        ) : (
          <input
            type="text"
            value={defaultSymbol}
            onChange={(e) => setDefaultSymbol(e.target.value.toUpperCase())}
            placeholder="e.g., XAU/USD, EUR/USD, SPX"
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          />
        )}
      </div>

      {/* Supported Symbols (Multi-Asset only) */}
      {!isBasicStrategy && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Supported Symbols</h2>
          <p className="text-sm text-gray-400 mb-4">
            Add symbols you want to trade across multiple asset classes
          </p>
          <div className="flex gap-3 mb-4">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              onKeyPress={(e) => e.key === 'Enter' && addSymbol()}
              placeholder="e.g., EUR/USD, SPX, GC"
              className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            />
            <button
              onClick={addSymbol}
              className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {supportedSymbols.map((symbol) => (
              <div
                key={symbol}
                className="flex items-center gap-2 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg"
              >
                <span className="text-white">{symbol}</span>
                <button
                  onClick={() => removeSymbol(symbol)}
                  className="text-red-400 hover:text-red-300 transition-colors"
                >
                  ✕
                </button>
              </div>
            ))}
            {supportedSymbols.length === 0 && (
              <p className="text-gray-500 text-sm">No additional symbols added</p>
            )}
          </div>
        </div>
      )}

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
