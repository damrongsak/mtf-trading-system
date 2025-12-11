import { useState, useEffect, useRef } from 'react';
import { PriceUpdate } from '../api/types';

// Use env var or default to current host
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/stream/prices';

export function useLivePrices(instruments: string[] = []) {
    const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
    const [connected, setConnected] = useState(false);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Prevent multiple connections
        if (ws.current) return;

        const connect = () => {
            const socket = new WebSocket(WS_URL);

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

            socket.onclose = () => {
                console.log('Price Stream disconnected');
                setConnected(false);
                ws.current = null;
                // Reconnect after delay
                setTimeout(connect, 3000);
            };

            ws.current = socket;
        };

        connect();

        return () => {
            if (ws.current) {
                ws.current.close();
                ws.current = null;
            }
        };
    }, []);

    return { prices, connected };
}
