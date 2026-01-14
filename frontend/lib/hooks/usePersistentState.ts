import { useState, useEffect } from 'react';

/**
 * A custom hook that wraps useState to persist values in localStorage.
 * 
 * @param key The unique key for localStorage
 * @param initialValue The default value if no data is found in storage
 * @returns [value, setValue] tuple similar to useState
 */
export function usePersistentState<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void] {
  // Initialize state function to read from localStorage only on client-side mount
  const [state, setState] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return initialValue;
    }
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  // Effect to update localStorage whenever state changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(key, JSON.stringify(state));
      } catch (error) {
        console.warn(`Error writing localStorage key "${key}":`, error);
      }
    }
  }, [key, state]);

  return [state, setState];
}
