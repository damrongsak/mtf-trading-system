import { useState, useEffect } from 'react';
import { logger } from '@/lib/api/app-logger';

/**
 * A custom hook that wraps useState to persist values in localStorage.
 * 
 * @param key The unique key for localStorage
 * @param initialValue The default value if no data is found in storage
 * @returns [value, setValue] tuple similar to useState
 */
export function usePersistentState<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void] {
  // Always initialize with default value to ensure server/client match during hydration
  const [state, setState] = useState<T>(initialValue);
  const [isHydrated, setIsHydrated] = useState(false);

  // Effect to read from localStorage only on client-side mount
  // This ensures the first render matches the server (initialValue)
  useEffect(() => {
    try {
      const item = window.localStorage.getItem(key);
      if (item) {
        setState(JSON.parse(item));
      }
    } catch (error) {
      logger.warn(`Error reading localStorage key "${key}":`, error);
    } finally {
      setIsHydrated(true);
    }
  }, [key]);

  // Effect to update localStorage whenever state changes
  // Only write AFTER we have successfully hydrated (read) from storage
  // to avoid overwriting existing data with the default initialValue
  useEffect(() => {
    if (isHydrated) {
      try {
        window.localStorage.setItem(key, JSON.stringify(state));
      } catch (error) {
        logger.warn(`Error writing localStorage key "${key}":`, error);
      }
    }
  }, [key, state, isHydrated]);

  return [state, setState];
}
