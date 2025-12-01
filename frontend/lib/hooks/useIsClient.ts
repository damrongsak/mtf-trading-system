import { useSyncExternalStore } from 'react';

const emptySubscribe = () => () => { };

/**
 * Hook to detect if code is running on client side
 * Useful for avoiding SSR issues with browser-only APIs
 */
export function useIsClient(): boolean {
    return useSyncExternalStore(
        emptySubscribe,
        () => true,
        () => false
    );
}
