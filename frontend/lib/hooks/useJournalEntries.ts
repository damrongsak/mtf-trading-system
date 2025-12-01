import { useState, useEffect } from 'react';
import { getJournalEntries } from '../api/journal';
import { JournalEntry, ApiError } from '../api/types';

interface UseJournalEntriesReturn {
  entries: JournalEntry[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Custom hook to fetch journal entries
 */
export function useJournalEntries(): UseJournalEntriesReturn {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEntries = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getJournalEntries();
      setEntries(data);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.message || 'Failed to fetch journal entries');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, []);

  return {
    entries,
    loading,
    error,
    refetch: fetchEntries,
  };
}
