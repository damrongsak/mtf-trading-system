import { apiClient } from './client';
import {
  SavedStrategy,
  SavedStrategyCreate,
  SavedStrategyUpdate,
  APIResponse
} from './types';

export const getSavedStrategies = async (publicOnly: boolean = false): Promise<SavedStrategy[]> => {
  const response = await apiClient.get<SavedStrategy[]>(`/api/v1/saved-strategies?public_only=${publicOnly}`);
  return response.data;
};

export const getSavedStrategy = async (id: string): Promise<SavedStrategy> => {
  const response = await apiClient.get<SavedStrategy>(`/api/v1/saved-strategies/${id}`);
  return response.data;
};

export const createSavedStrategy = async (data: SavedStrategyCreate): Promise<SavedStrategy> => {
  const response = await apiClient.post<SavedStrategy>('/api/v1/saved-strategies', data);
  return response.data;
};

export const updateSavedStrategy = async (id: string, data: SavedStrategyUpdate): Promise<SavedStrategy> => {
  const response = await apiClient.put<SavedStrategy>(`/api/v1/saved-strategies/${id}`, data);
  return response.data;
};

export const deleteSavedStrategy = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/saved-strategies/${id}`);
};
