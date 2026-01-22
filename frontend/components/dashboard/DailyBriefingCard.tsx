import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { aiApi, Briefing } from '@/lib/api/ai';
import { format } from 'date-fns';
import remarkGfm from 'remark-gfm';
import { logger } from '@/lib/api/app-logger';

export function DailyBriefingCard() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchBriefing() {
      try {
        setLoading(true);
        const data = await aiApi.getDailyBriefing();
        setBriefing(data);
      } catch (err) {
        // It's okay if no briefing exists or AI is offline, show fallback or nothing?
        // Let's show a button to generate one or just an error message.
        logger.warn("Failed to fetch daily briefing", err);
        setError("AI Briefing unavailable.");
      } finally {
        setLoading(false);
      }
    }
    fetchBriefing();
  }, []);

  const handleGenerate = async () => {
      try {
          setLoading(true);
          // Calling getDailyBriefing (which calls GET /briefing) works.
          // But if we want to FORCE generation, we might need a POST.
          // The current GET /briefing endpoint calls POST /agent/briefing in backend,
          // which actually Runs the agent every time. So GET is trigger.
          const data = await aiApi.getDailyBriefing();
          setBriefing(data);
          setError(null);
      } catch (_err) {
          setError("Failed to generate briefing.");
      } finally {
          setLoading(false);
      }
  };

  if (loading && !briefing) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-lg h-full animate-pulse flex items-center justify-center text-gray-500">
        Generating Daily Briefing...
      </div>
    );
  }

  if (error && !briefing) {
      return (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-lg h-full flex flex-col items-center justify-center text-gray-400 gap-3">
           <p className="text-sm">{error}</p>
           <button 
             onClick={handleGenerate}
             className="px-4 py-2 bg-accent-blue/20 hover:bg-accent-blue/30 text-accent-blue rounded-lg text-xs transition-colors"
           >
             Try Again
           </button>
        </div>
      );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-lg relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-4 opacity-50">
        <svg className="w-16 h-16 text-indigo-500/10" viewBox="0 0 24 24" fill="currentColor">
           <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm1 14.93V17a1 1 0 11-2 0v-2.07A7.003 7.003 0 015 8.2V8a1 1 0 012 0v.2a5.002 5.002 0 004.9 5.08 1 1 0 01.9.92zM10 5a2 2 0 114 0 2 2 0 01-4 0z" />
        </svg>
      </div>

      <div className="relative z-10 flex flex-col h-full">
        <div className="flex items-center justify-between mb-4">
           <div className="flex items-center gap-2">
             <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center">
               <svg className="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
               </svg>
             </div>
             <div>
               <h3 className="text-lg font-bold text-gray-100">Daily Briefing</h3>
               {briefing && (
                 <p className="text-xs text-indigo-400/80">Generated {format(new Date(briefing.generated_at), 'HH:mm')}</p>
               )}
             </div>
           </div>
           
           <button 
             onClick={handleGenerate}
             disabled={loading}
             className="text-gray-500 hover:text-white transition-colors"
             title="Regenerate"
           >
              <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
           </button>
        </div>

        <div className="prose prose-invert prose-sm max-w-none flex-grow bg-gray-950/30 rounded-lg p-3 overflow-y-auto max-h-[300px] text-gray-300">
           {briefing ? (
             <ReactMarkdown remarkPlugins={[remarkGfm]}>
               {briefing.content}
             </ReactMarkdown>
           ) : (
             <p className="italic text-gray-500">Generating report...</p>
           )}
        </div>
      </div>
    </div>
  );
}
