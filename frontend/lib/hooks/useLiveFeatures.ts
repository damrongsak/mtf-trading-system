import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { logger } from '@/lib/api/app-logger';

// Feature Payload Structure
export interface FeatureUpdate {
    symbol: string;
    timeframe: string;
    timestamp: string;
    rsi_14?: number | null;
    sma_20?: number | null;
    sma_50?: number | null;
    atr_14?: number | null;
    volatility?: number | null;
    close?: number;
    features_complete?: string;
    [key: string]: unknown;
}

// Determine WS_URL dynamically
const getWsUrl = () => {
    if (typeof window !== 'undefined') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/api/v1/stream/prices`;
    }
    return process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/stream/prices';
};

const WS_URL = getWsUrl();

export function useLiveFeatures(instruments: string[] = ['XAU_USD', 'EUR_USD']) {
    const [features, setFeatures] = useState<Record<string, FeatureUpdate>>({});
    const [connected, setConnected] = useState(false);
    const { authToken } = useAuth();

    // Stable key for instruments
    const instrumentsList = instruments.map(s => s.replace('/', '_')).join(',');

    // Refs for throttling
    const featuresRef = useRef<Record<string, FeatureUpdate>>({});
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        let isMounted = true;
        let activeSocket: WebSocket | null = null;

        if (!authToken) return;

        const connect = () => {
            const queryParams = new URLSearchParams();
            if (instrumentsList) queryParams.append('symbols', instrumentsList);
            queryParams.append('token', authToken);

            const socket = new WebSocket(`${WS_URL}?${queryParams.toString()}`);
            activeSocket = socket;

            socket.onopen = () => {
                if (isMounted) {
                    logger.debug('Connected to Alpha Stream');
                    setConnected(true);
                }
            };

            socket.onmessage = (event) => {
                if (!isMounted) return;
                try {
                    const msg = JSON.parse(event.data);

                    // Check event type from FeatureWorker
                    if (msg.event_type === 'features_calculated' || msg.features_complete === 'true' || msg.type === 'FEATURE') {
                        // The payload might be nested or flat depending on StreamManager broadcast.
                        // StreamManager broadcasts `msg["data"]`.
                        // FeatureWorker payload: { event_type, symbol, features: json_str, ... }
                        // Wait, FeatureWorker sends `data=...` to `xadd`? 
                        // FeatureWorker sends:
                        // payload = { "event_type": ..., "features": json.dumps(features) ... }
                        // Redis publisher creates `msg['data']`.

                        // Redis stream messages are typically dicts.
                        // StreamManager handles `pmessage`. data is the message payload.
                        // The Redis key values are STRINGS.
                        // So `msg` here is the parsed JSON broadcasted by StreamManager?
                        // StreamManager does `await connection.send_text(message)`.

                        // If `data` from redis is a JSON string, then `msg` is the object.
                        // However, FeatureWorker xadds dict where values are strings.
                        // `RedisPublisher` stringifies lists/dicts but NOT simple strings? 
                        // FeatureWorker: `json.dumps(features, default=str)`.

                        // Let's assume the payload structure:
                        // { symbol: "XAU_USD", features: "{\"rsi_14\": ...}" }

                        const symbol = msg.symbol;
                        let featData = msg;

                        if (typeof msg.features === 'string') {
                            // Access inner features if present
                            featData = { ...msg, ...JSON.parse(msg.features) };
                        }

                        featuresRef.current[symbol] = {
                            ...featData,
                            last_updated: new Date().toISOString()
                        };

                        // Throttle
                        if (!timeoutRef.current) {
                            timeoutRef.current = setTimeout(() => {
                                if (isMounted) setFeatures({ ...featuresRef.current });
                                timeoutRef.current = null;
                            }, 500); // 500ms throttle for table
                        }
                    }
                } catch (e) {
                    logger.error("Alpha Stream Parse Error", e);
                }
            };

            socket.onclose = () => {
                if (isMounted) {
                    setConnected(false);
                    setTimeout(connect, 5000);
                }
            };
        };

        connect();

        return () => {
            isMounted = false;
            if (activeSocket) activeSocket.close();
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
        };

    }, [authToken, instrumentsList]);

    return { features, connected };
}
