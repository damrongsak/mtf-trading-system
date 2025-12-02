'use client';

import React, { useEffect, useState } from 'react';

type MarketSession = 'Asian' | 'London' | 'New York' | 'Closed';

export const MarketStatusBadge: React.FC = () => {
  const [currentSession, setCurrentSession] = useState<MarketSession>('Closed');

  useEffect(() => {
    const updateSession = () => {
      const now = new Date();
      const utcHour = now.getUTCHours();

      // Market session times (UTC)
      // Asian: 00:00 - 09:00 UTC
      // London: 08:00 - 17:00 UTC  
      // New York: 13:00 - 22:00 UTC
      
      const sessions: MarketSession[] = [];
      
      if (utcHour >= 0 && utcHour < 9) sessions.push('Asian');
      if (utcHour >= 8 && utcHour < 17) sessions.push('London');
      if (utcHour >= 13 && utcHour < 22) sessions.push('New York');
      
      if (sessions.length > 0) {
        // If multiple sessions are active, show the first one
        setCurrentSession(sessions[0]);
      } else {
        setCurrentSession('Closed');
      }
    };

    updateSession();
    const interval = setInterval(updateSession, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  const getSessionStyle = (session: MarketSession) => {
    switch (session) {
      case 'Asian':
        return {
          bg: 'bg-yellow-400/10',
          text: 'text-yellow-400',
          border: 'border-yellow-400/20',
          dot: 'bg-yellow-400',
        };
      case 'London':
        return {
          bg: 'bg-accent-blue/10',
          text: 'text-accent-blue',
          border: 'border-accent-blue/20',
          dot: 'bg-accent-blue',
        };
      case 'New York':
        return {
          bg: 'bg-accent-green/10',
          text: 'text-accent-green',
          border: 'border-accent-green/20',
          dot: 'bg-accent-green',
        };
      default:
        return {
          bg: 'bg-gray-500/10',
          text: 'text-gray-500',
          border: 'border-gray-500/20',
          dot: 'bg-gray-500',
        };
    }
  };

  const style = getSessionStyle(currentSession);

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border ${style.bg} ${style.border}`}>
      <div className={`w-2 h-2 rounded-full ${style.dot} ${currentSession !== 'Closed' ? 'animate-pulse' : ''}`} />
      <div className="flex flex-col">
        <span className={`text-xs font-medium ${style.text}`}>
          {currentSession === 'Closed' ? 'Market Closed' : `${currentSession} Session`}
        </span>
        <span className="text-xs text-gray-500 font-mono">
          {new Date().toUTCString().slice(17, 22)} UTC
        </span>
      </div>
    </div>
  );
};
