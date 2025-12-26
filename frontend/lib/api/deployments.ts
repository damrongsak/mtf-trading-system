
import { apiClient } from './client';
import { Deployment, DeploymentCreate } from './types';

export const getDeployments = async (): Promise<Deployment[]> => {
    const response = await apiClient.get<Deployment[]>('/api/v1/deployments/');
    return response.data;
};

export const createDeployment = async (data: DeploymentCreate): Promise<Deployment> => {
    const response = await apiClient.post<Deployment>('/api/v1/deployments/', data);
    return response.data;
};

export const stopDeployment = async (id: string): Promise<Deployment> => {
    const response = await apiClient.post<Deployment>(`/api/v1/deployments/${id}/stop`);
    return response.data;
};
