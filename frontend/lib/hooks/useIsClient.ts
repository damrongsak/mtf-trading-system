import { useState, useEffect } from 'react';

/**
 * Hook to detect if code is running on client side
 * Useful for avoiding SSR issues with browser-only APIs
 */
export function useIsClient(): boolean {
    const [isClient, setIsClient] = useState(false);

    useEffect(() => {
        setIsClient(true);
    }, []);

    return isClient;
}
