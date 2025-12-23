
import { apiClient } from './client';
import { APIResponse, PaginatedResponse, StrategyResponse, StrategyCreate } from './types';

export const strategiesApi = {
    // List available templates (SMC, MACD, etc.)
    getTemplates: async (): Promise<APIResponse<any[]>> => {
        const response = await apiClient.get<APIResponse<any[]>>('/api/v1/strategies/templates');
        return response.data;
    },

    // List strategies for a specific fund (or all if fundId undefined)
    listHelper: async (
        fundId?: string,
        page: number = 1,
        perPage: number = 10
    ): Promise<PaginatedResponse<StrategyResponse>> => {
        const params: any = { page, per_page: perPage };
        if (fundId) params.fund_id = fundId;

        const response = await apiClient.get<PaginatedResponse<StrategyResponse>>('/api/v1/strategies/', {
            params,
        });
        return response.data;
    },

    // Create a new strategy instance
    create: async (data: StrategyCreate): Promise<APIResponse<StrategyResponse>> => {
        const response = await apiClient.post<APIResponse<StrategyResponse>>('/api/v1/strategies/', data);
        return response.data;
    },

    // Update configuration (params or risk)
    updateConfig: async (
        id: string,
        config: Partial<{ config_json: any; risk_settings: any; is_active: boolean }>
    ): Promise<APIResponse<StrategyResponse>> => {
        const response = await apiClient.post<APIResponse<StrategyResponse>>(`/api/v1/strategies/${id}/config`, config);
        return response.data;
    },

    // Start/Stop (Action)
    // Note: The backend implemented /start and /stop in Strategy Core, 
    // but Gateway usually proxies or has its own state. 
    // Assuming we use the Gateway endpoints if they exist, or update config is_active=True?
    // The previous implementation used is_active toggle. 
    // Let's stick to updateConfig({ is_active: true }) for now unless explicit start endpoints required.
    // Spec says POST /strategies/{id}/start|stop might exist. Checking logs... 
    // I saw router.post("/strategies/{strategy_id}/start") in Strategy CORE, but not in Gateway router.
    // For now, we rely on is_active toggle in config.
};
