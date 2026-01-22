import { useState, useEffect, useCallback } from 'react';
import { aiApi } from '../api/ai';
import { ChatSession, ChatMessage } from '../api/types';
import { logger } from '@/lib/api/app-logger';

export function useStrategyChat(strategyId?: string) {
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Load Sessions
    const fetchSessions = useCallback(async () => {
        try {
            setLoading(true);
            const data = await aiApi.getSessions(strategyId);
            setSessions(data);
            if (data.length > 0 && !activeSessionId) {
                // Automatically select the most recent session
                setActiveSessionId(data[0].id);
            }
        } catch (err) {
            setError('Failed to load chat history');
            logger.error('Failed to load sessions:', err);
        } finally {
            setLoading(false);
        }
    }, [strategyId, activeSessionId]);

    // Load Messages for Active Session
    const fetchMessages = useCallback(async () => {
        if (!activeSessionId) {
            setMessages([]);
            return;
        }

        try {
            const data = await aiApi.getMessages(activeSessionId);
            setMessages(data);
        } catch (err) {
            logger.error('Failed to load messages:', err);
        }
    }, [activeSessionId]);

    // Sync effect
    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    useEffect(() => {
        fetchMessages();
    }, [fetchMessages]);

    const createSession = async (initialMessage?: string) => {
        try {
            setSending(true);
            const newSession = await aiApi.createSession({
                strategy_id: strategyId,
                initial_message: initialMessage
            });
            setSessions([newSession, ...sessions]);
            setActiveSessionId(newSession.id);
            return newSession;
        } catch (err) {
            setError('Failed to create new chat');
            throw err;
        } finally {
            setSending(false);
        }
    };

    const sendMessage = async (content: string, contextSnapshot?: Record<string, unknown>) => {
        if (!content.trim()) return;

        let sessionId = activeSessionId;

        // If no active session, create one first
        if (!sessionId) {
            const session = await createSession(content);
            sessionId = session.id;
            // Don't duplicate message sending if createSession handles generic setup, 
            // but here createSession is just the session container.
        }

        // Optimistic Update
        const optimisticMsg: ChatMessage = {
            id: 'temp-' + Date.now(),
            session_id: sessionId!,
            role: 'user',
            content: content,
            created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, optimisticMsg]);
        setSending(true);

        try {
            // Send to API
            await aiApi.sendMessage(sessionId!, {
                content,
                context_snapshot: contextSnapshot
            });

            // Refresh messages to get true IDs and AI response (although endpoint returns AI msg)
            // Wait, endpoint returns the *AI response* message object? 
            // Checking backend: Yes, sends User msg, waits, returns AI msg.
            // So we need to refetch to get the proper User msg ID, or just append AI response.
            // Let's refetch to be safe and consistent.
            await fetchMessages();

        } catch (_err) {
            setError('Failed to send message');
            // Rollback optimistic?
            setMessages(prev => prev.filter(m => m.id !== optimisticMsg.id));
        } finally {
            setSending(false);
        }
    };

    return {
        sessions,
        activeSessionId,
        setActiveSessionId,
        messages,
        loading,
        sending,
        error,
        createSession,
        sendMessage,
        refreshSessions: fetchSessions
    };
}
