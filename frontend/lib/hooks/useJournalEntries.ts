import { useState, useEffect, useCallback } from 'react';
import { getJournalEntries } from '../api/journal';
import { JournalEntry } from '../api/types';
import { ApiError } from '../api/errors';

interface UseJournalEntriesReturn {
  entries: JournalEntry[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  total: number;
  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;
  totalPages: number;
}

/**
 * Custom hook to fetch journal entries
 */
export function useJournalEntries(initialPage: number = 1, initialPerPage: number = 10): UseJournalEntriesReturn {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(initialPage);
  const [perPage, setPerPage] = useState(initialPerPage);
  const [totalPages, setTotalPages] = useState(0);

  const fetchEntries = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getJournalEntries(page, perPage);

      // Extract data from PaginatedResponse
      setEntries(response.data);
      setTotal(response.meta.total || 0);
      setPage(response.meta.page || 1);
      setTotalPages(response.meta.total_pages || 0);
    } catch (err) {
      // Check if it's our custom ApiError
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to fetch journal entries');
      }
    } finally {
      setLoading(false);
    }
  }, [page, perPage]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  return {
    entries,
    loading,
    error,
    refetch: fetchEntries,
    total,
    page,
    setPage,
    perPage,
    setPerPage,
    totalPages,
  };
}
