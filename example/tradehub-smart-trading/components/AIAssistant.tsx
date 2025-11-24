import React, { useState } from 'react';
import { Sparkles, Send, X } from 'lucide-react';
import { getMarketAnalysis } from '../services/geminiService';

const AIAssistant: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleAnalysis = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResponse(null);
    try {
      const result = await getMarketAnalysis(query);
      setResponse(result);
    } catch (e) {
      setResponse("An error occurred while fetching analysis.");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 bg-gradient-to-r from-purple-600 to-blue-600 text-white p-4 rounded-full shadow-lg shadow-purple-900/50 hover:scale-105 transition-transform z-50 flex items-center gap-2 group"
      >
        <Sparkles size={20} className="animate-pulse" />
        <span className="font-medium pr-1 hidden group-hover:inline-block transition-all duration-300">Ask AI</span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-80 sm:w-96 bg-surfaceHighlight border border-gray-700 rounded-xl shadow-2xl z-50 flex flex-col overflow-hidden animate-fade-in-up">
      <div className="bg-gradient-to-r from-purple-900 to-blue-900 p-4 flex justify-between items-center">
        <div className="flex items-center gap-2 text-white font-medium">
          <Sparkles size={16} className="text-purple-300" />
          <span>Market Assistant</span>
        </div>
        <button onClick={() => setIsOpen(false)} className="text-white/70 hover:text-white">
          <X size={18} />
        </button>
      </div>

      <div className="p-4 flex-1 min-h-[200px] max-h-[400px] overflow-y-auto bg-[#0b0e11]">
        {!response && !loading && (
          <p className="text-slate-500 text-sm text-center mt-8">
            Ask about market trends, glossary terms, or general trading advice.
          </p>
        )}
        
        {loading && (
          <div className="flex items-center justify-center h-full gap-2 text-purple-400 text-sm">
            <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-400"></span>
            Analyzing market data...
          </div>
        )}

        {response && (
          <div className="bg-surface p-3 rounded-lg border border-gray-800">
            <p className="text-slate-300 text-sm leading-relaxed">{response}</p>
          </div>
        )}
      </div>

      <div className="p-3 bg-surface border-t border-gray-800">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAnalysis()}
            placeholder="E.g., Outlook for JPY?"
            className="w-full bg-[#0b0e11] border border-gray-700 rounded-lg pl-3 pr-10 py-2 text-sm text-white focus:outline-none focus:border-purple-500 transition-colors placeholder-gray-600"
          />
          <button 
            onClick={handleAnalysis}
            disabled={!query.trim() || loading}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-purple-500 hover:text-purple-400 disabled:opacity-50"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;