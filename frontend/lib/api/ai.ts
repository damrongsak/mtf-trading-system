import { apiClient } from './client';
import { APIResponse } from './types';

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
    getSessions: async (strategyId?: string) => {
        const response = await apiClient.get<APIResponse<any[]>>('/api/v1/ai/chat/sessions', {
            params: { strategy_id: strategyId }
        });
        return response.data.data || [];
    },

    getMessages: async (sessionId: string) => {
        const response = await apiClient.get<APIResponse<any[]>>(`/api/v1/ai/chat/sessions/${sessionId}/messages`);
        return response.data.data || [];
    },

    createSession: async (payload: { strategy_id?: string, initial_message?: string }) => {
        const response = await apiClient.post<APIResponse<any>>('/api/v1/ai/chat/sessions', payload);
        return response.data.data;
    },

    sendMessage: async (sessionId: string, payload: { content: string, context_snapshot?: any }) => {
        const response = await apiClient.post<APIResponse<any>>(`/api/v1/ai/chat/sessions/${sessionId}/messages`, payload);
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
