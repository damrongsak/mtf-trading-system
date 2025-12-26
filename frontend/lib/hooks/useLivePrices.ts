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

    useEffect(() => {
        // If socket exists, close it to reconnect with new symbols (cleanup will handle this, but we want to be explicit if needed)
        // Actually, the cleanup function from the previous effect run will have already closed the socket and set ws.current = null
        // So we don't need to check ws.current here usually, unless strict mode causes double mounts.
        // But to be safe against double-mounts:
        if (ws.current) {
            // If we are here, it means cleanup didn't run or we are in a race.
            // Ideally cleanup runs before next effect.
            // We can proceed.
        }

        // Wait for auth token
        if (!authToken) return;

        const connect = () => {
            const queryParams = new URLSearchParams();
            if (instrumentsList) {
                queryParams.append('symbols', instrumentsList);
            }
            queryParams.append('token', authToken);

            const socket = new WebSocket(`${WS_URL}?${queryParams.toString()}`);

            socket.onopen = () => {
                console.log('Connected to Price Stream');
                setConnected(true);
            };

            socket.onmessage = (event) => {
                try {
                    const data: PriceUpdate = JSON.parse(event.data);
                    if (data.type === 'PRICE') {
                        setPrices(prev => ({
                            ...prev,
                            [data.instrument]: data
                        }));
                    }
                } catch (e) {
                    console.error('Error parsing price update:', e);
                }
            };

            socket.onclose = (event) => {
                console.log('Price Stream disconnected', event.reason);
                setConnected(false);
                ws.current = null;

                // Only reconnect if not closed intentionally by unmount (which calls close())
                // But here we can't easily distinguish. 
                // However, since we return a cleanup function that closes it,
                // we should be careful. 
                // Simplest is to NOT auto-reconnect inside the effect if we rely on effect dependencies.
                // If we want auto-reconnect for network issues, we keep it.
                // But caution: if token is invalid, valid reconnect loop might spam.
                // The backend sends WS_1008_POLICY_VIOLATION for bad token.

                if (event.code !== 1008) {
                    setTimeout(connect, 3000);
                }
            };

            ws.current = socket;
        };

        connect();

        return () => {
            if (ws.current) {
                // Remove onclose to prevent reconnect attempts during cleanup
                ws.current.onclose = null;
                ws.current.close();
                ws.current = null;
            }
        };
    }, [authToken, instrumentsList]);

    return { prices, connected };
}
