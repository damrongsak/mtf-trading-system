'use client';

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';
import { Activity, AlertTriangle, CheckCircle, ServerCrash } from 'lucide-react';
import { logger } from '@/lib/api/app-logger';

interface QueueHealth {
  vip_queue: number;
  retail_queue: number;
  dead_letter_queue: number;
  recently_processed: number;
}

export function QueueHealthMonitor() {
  const [health, setHealth] = useState<QueueHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchHealth = async () => {
      try {
        const response = await apiClient.get('/api/v1/system/queue-health');
        if (mounted && response.data?.data) {
          setHealth(response.data.data);
        }
      } catch (err) {
        logger.error('Failed to fetch queue health:', err);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchHealth();
    const intervalId = setInterval(fetchHealth, 5000); // Poll every 5 seconds
    
    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  if (loading) return <div className="animate-pulse bg-gray-800/30 h-10 w-48 rounded-md" />;

  const isHealthy = health && health.dead_letter_queue === 0;

  return (
    <div className="flex items-center gap-4 bg-gray-900/50 border border-gray-800 p-2 rounded-lg text-sm mb-4">
      <div className="flex items-center gap-2 border-r border-gray-700 pr-4">
        {isHealthy ? (
          <CheckCircle className="w-5 h-5 text-green-500" />
        ) : (
          <AlertTriangle className="w-5 h-5 text-red-500 animate-pulse" />
        )}
        <span className="font-semibold text-gray-200">Execution Gateway</span>
      </div>
      
      <div className="flex gap-4">
        <div className="flex flex-col">
          <span className="text-gray-500 text-xs uppercase">VIP Queue</span>
          <span className="text-gray-200 font-mono">{health?.vip_queue || 0}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-500 text-xs uppercase">Retail</span>
          <span className="text-gray-200 font-mono">{health?.retail_queue || 0}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-500 text-xs uppercase flex items-center gap-1">
            DLQ {health && health.dead_letter_queue > 0 && <ServerCrash className="w-3 h-3 text-red-400" />}
          </span>
          <span className={`font-mono ${health && health.dead_letter_queue > 0 ? 'text-red-400 font-bold' : 'text-gray-200'}`}>
            {health?.dead_letter_queue || 0}
          </span>
        </div>
        <div className="flex flex-col border-l border-gray-700 pl-4 ml-2">
          <span className="text-gray-500 text-xs uppercase">SETNX Locks</span>
          <span className="text-green-400 font-mono">{health?.recently_processed || 0} Mps</span>
        </div>
      </div>
    </div>
  );
}
