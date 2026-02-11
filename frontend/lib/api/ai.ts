import { apiClient } from './client';
import { APIResponse, ChatSession, ChatMessage, CreateChatSessionDto, CreateChatMessageDto } from './types';

export interface Briefing {
    content: string;
    generated_at: string;
}

export interface AIReportResponse {
    report: string;
    timestamp: string;
    // Add other fields if needed
}

export const runMarketObserver = async (instruction: string): Promise<AIReportResponse> => {
    const response = await apiClient.post<APIResponse<AIReportResponse>>('/api/v1/ai/agent/observer/run', {
        input_text: instruction
    });
    return response.data.data!;
};

export const aiApi = {
    getSessions: async (strategyId?: string): Promise<ChatSession[]> => {
        const response = await apiClient.get<APIResponse<ChatSession[]>>('/api/v1/ai/chat/sessions', {
            params: { strategy_id: strategyId }
        });
        return response.data.data || [];
    },

    getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
        const response = await apiClient.get<APIResponse<ChatMessage[]>>(`/api/v1/ai/chat/sessions/${sessionId}/messages`);
        return response.data.data || [];
    },

    createSession: async (payload: CreateChatSessionDto): Promise<ChatSession> => {
        const response = await apiClient.post<APIResponse<ChatSession>>('/api/v1/ai/chat/sessions', payload);
        if (!response.data.data) throw new Error('Failed to create session');
        return response.data.data;
    },

    sendMessage: async (sessionId: string, payload: CreateChatMessageDto): Promise<ChatMessage> => {
        const response = await apiClient.post<APIResponse<ChatMessage>>(`/api/v1/ai/chat/sessions/${sessionId}/messages`, payload);
        if (!response.data.data) throw new Error('Failed to send message');
        return response.data.data;
    },

    getDailyBriefing: async (): Promise<Briefing> => {
        const response = await apiClient.get<APIResponse<{ content: string, timestamp: string }>>('/api/v1/ai/briefing');
        return {
            content: response.data.data!.content,
            generated_at: response.data.data!.timestamp
        };
    }
};
