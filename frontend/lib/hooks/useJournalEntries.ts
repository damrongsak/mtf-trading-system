import { useState, useEffect, useCallback } from 'react';
import { getJournalEntries, JournalFilters } from '../api/journal';
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
  filters: JournalFilters;
  setFilters: (filters: JournalFilters) => void;
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
  const [filters, setFilters] = useState<JournalFilters>({});

  const fetchEntries = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getJournalEntries(page, perPage, filters);

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
  }, [page, perPage, filters]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const handleSetFilters = (newFilters: JournalFilters) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page when filtering
  };

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
    filters,
    setFilters: handleSetFilters
  };
}
