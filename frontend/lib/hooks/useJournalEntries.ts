import { useState, useEffect } from 'react';
import { getJournalEntries } from '../api/journal';
import { JournalEntry, ApiError } from '../api/types';

interface UseJournalEntriesReturn {
  entries: JournalEntry[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  total: number;
  page: number;
  totalPages: number;
}

/**
 * Custom hook to fetch journal entries
 */
export function useJournalEntries(): UseJournalEntriesReturn {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  const fetchEntries = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getJournalEntries(page, 10);

      // Extract data from PaginatedResponse
      setEntries(response.data);
      setTotal(response.meta.total || 0);
      setPage(response.meta.page || 1);
      setTotalPages(response.meta.total_pages || 0);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.message || 'Failed to fetch journal entries');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, [page]);

  return {
    entries,
    loading,
    error,
    refetch: fetchEntries,
    total,
    page,
    totalPages,
  };
}
