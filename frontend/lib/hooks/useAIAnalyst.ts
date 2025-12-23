import { useState } from 'react';
import { runMarketObserver, AIReportResponse } from '../api/ai';
import { ApiError } from '../api/errors';

export interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

export interface UseAIAnalystReturn {
    messages: Message[];
    loading: boolean;
    error: string | null;
    sendMessage: (input: string) => Promise<void>;
    clearHistory: () => void;
}

export function useAIAnalyst(): UseAIAnalystReturn {
    // Initial welcome message
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content: "Hello! I'm your AI Market Observer. Ask me to analyze a symbol (e.g., 'Check XAU/USD') or check for signals.",
            timestamp: new Date()
        }
    ]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const sendMessage = async (input: string) => {
        if (!input.trim()) return;

        // Add user message immediately
        const userMsg: Message = { role: 'user', content: input, timestamp: new Date() };
        setMessages(prev => [...prev, userMsg]);

        setLoading(true);
        setError(null);

        try {
            const response: AIReportResponse = await runMarketObserver(input);

            // Add AI response
            const aiMsg: Message = {
                role: 'assistant',
                content: response.report,
                timestamp: new Date(response.timestamp)
            };
            setMessages(prev => [...prev, aiMsg]);

        } catch (err) {
            const errorMsg = err instanceof ApiError ? err.message : 'Failed to generate report';
            setError(errorMsg);
            // Optional: Add error as a system message?
        } finally {
            setLoading(false);
        }
    };

    const clearHistory = () => {
        setMessages([{
            role: 'assistant',
            content: "History cleared. Ready for new commands.",
            timestamp: new Date()
        }]);
    }

    return {
        messages,
        loading,
        error,
        sendMessage,
        clearHistory
    };
}
