import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { PriceUpdate } from '../api/types';

// Determine WS_URL dynamically
const getWsUrl = () => {
    if (typeof window !== 'undefined') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host; // includes port if present
        return `${protocol}//${host}/api/v1/stream/prices`;
    }
    return process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/stream/prices';
};

const WS_URL = getWsUrl();

export function useLivePrices(instruments: string[] = []) {
    const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
    const [connected, setConnected] = useState(false);
    const ws = useRef<WebSocket | null>(null);
    const { authToken } = useAuth();

    // Create a stable key for instruments to avoid infinite re-renders
    const instrumentsList = instruments.map(s => s.replace('/', '_')).join(',');

    // Use refs to handle high-frequency updates without causing infinite render loops
    const pricesRef = useRef<Record<string, PriceUpdate>>({});
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        let isMounted = true;
        let activeSocket: WebSocket | null = null;

        // Cleanup function for the throttle timeout
        const clearThrottle = () => {
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
                timeoutRef.current = null;
            }
        };

        // Wait for auth token
        if (!authToken) return;

        const connect = () => {
            if (!isMounted) return;

            const queryParams = new URLSearchParams();
            if (instrumentsList) {
                queryParams.append('symbols', instrumentsList);
            }
            queryParams.append('token', authToken);

            const socket = new WebSocket(`${WS_URL}?${queryParams.toString()}`);
            activeSocket = socket;
            ws.current = socket;

            socket.onopen = () => {
                if (isMounted) {
                    if (process.env.NODE_ENV === 'development') console.log('Connected to Price Stream');
                    setConnected(true);
                }
            };

            socket.onmessage = (event) => {
                if (!isMounted) return;
                try {
                    const data: PriceUpdate = JSON.parse(event.data);
                    if (data.type === 'PRICE') {
                        // Update ref immediately
                        pricesRef.current[data.instrument] = data;

                        // Throttle state updates to max 5 per second (200ms)
                        // This prevents "Maximum update depth exceeded" errors
                        if (!timeoutRef.current) {
                            timeoutRef.current = setTimeout(() => {
                                if (isMounted) {
                                    setPrices(() => ({ ...pricesRef.current }));
                                }
                                timeoutRef.current = null;
                            }, 500);
                        }
                    }
                } catch (e) {
                    console.error('Error parsing price update:', e);
                }
            };

            socket.onclose = (event) => {
                if (!isMounted) return;

                if (process.env.NODE_ENV === 'development') console.log('Price Stream disconnected', event.reason);
                setConnected(false);
                ws.current = null;

                if (event.code !== 1008) {
                    // Only reconnect if this specific socket instance was the active one
                    // and the component is still mounted.
                    if (activeSocket === socket) {
                        setTimeout(connect, 3000);
                    }
                }
            };
        };

        connect();

        return () => {
            isMounted = false;
            clearThrottle();
            if (activeSocket) {
                activeSocket.close();
            }
            if (ws.current) {
                ws.current.close();
                ws.current = null;
            }
        };
    }, [authToken, instrumentsList]);

    return { prices, connected };
}
