
import { apiClient } from './client';
import { Deployment, DeploymentCreate } from './types';

import { PaginatedResponse, StrategyLog } from './types';

export const getDeployments = async (page = 1, limit = 10): Promise<PaginatedResponse<Deployment>> => {
    const skip = (page - 1) * limit;
    const response = await apiClient.get<PaginatedResponse<Deployment>>(`/api/v1/deployments/?skip=${skip}&limit=${limit}`);
    return response.data;
};

export const createDeployment = async (data: DeploymentCreate): Promise<Deployment> => {
    const response = await apiClient.post<Deployment>('/api/v1/deployments/', data);
    return response.data;
};

export const getDeployment = async (id: string): Promise<Deployment> => {
    const response = await apiClient.get<Deployment>(`/api/v1/deployments/${id}`);
    return response.data;
};

export const stopDeployment = async (id: string): Promise<Deployment> => {
    const response = await apiClient.post<Deployment>(`/api/v1/deployments/${id}/stop`);
    return response.data;
};

export const restartDeployment = async (id: string): Promise<Deployment> => {
    const response = await apiClient.post<Deployment>(`/api/v1/deployments/${id}/restart`);
    return response.data;
};

export const getDeploymentLogs = async (id: string, page = 1, limit = 50): Promise<PaginatedResponse<StrategyLog>> => {
    const skip = (page - 1) * limit;
    const response = await apiClient.get<PaginatedResponse<StrategyLog>>(`/api/v1/deployments/${id}/logs?skip=${skip}&limit=${limit}`);
    return response.data;
};
