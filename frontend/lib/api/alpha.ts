import { apiClient, handleApiError } from './client';

export interface DeploymentConfig {
    name: string;
    template_id: string;
    fund_id: string;
    broker_account_id: string;
    config_json: {
        formula: string;
        meta_description?: string;
        [key: string]: string | number | boolean | undefined;
    };
    risk_settings?: Record<string, unknown>;
}

export const deployAlphaStrategy = async (config: DeploymentConfig) => {
    try {
        const response = await apiClient.post('/api/v1/strategies/', config);
        return response.data;
    } catch (error: unknown) {
        throw handleApiError(error);
    }
};

export interface CreateChatSessionRequest {
    strategy_id?: string;
    context_type?: string;
}

export interface ChatSession {
    id: string;
    user_id: string;
    created_at: string;
    title?: string;
}

export interface SendMessageRequest {
    content: string;
    context_data?: Record<string, unknown>;
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
}

export const createChatSession = async (data: CreateChatSessionRequest = {}): Promise<ChatSession> => {
    try {
        const response = await apiClient.post('/api/v1/ai/chat/sessions', data);
        return response.data;
    } catch (error: unknown) {
        throw handleApiError(error);
    }
}

export const sendChatMessage = async (sessionId: string, data: SendMessageRequest): Promise<ChatMessage> => {
    try {
        const response = await apiClient.post(`/api/v1/ai/chat/sessions/${sessionId}/messages`, data);
        return response.data.data; // Assuming wrapper
    } catch (error: unknown) {
        throw handleApiError(error);
    }
}

export const getChatHistory = async (sessionId: string): Promise<ChatMessage[]> => {
    try {
        const response = await apiClient.get(`/api/v1/ai/chat/sessions/${sessionId}/messages`);
        return response.data;
    } catch (error: unknown) {
        throw handleApiError(error);
    }
}
