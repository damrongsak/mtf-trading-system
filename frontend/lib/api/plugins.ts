import { apiClient } from './client';
import { Plugin, PluginConfigUpdate, SystemHooks, APIResponse } from './types';

export const pluginsApi = {
    // List all plugins
    list: async (): Promise<Plugin[]> => {
        const response = await apiClient.get<APIResponse<Plugin[]>>('/api/v1/plugins');
        return response.data.data || [];
    },

    // Activate a plugin
    activate: async (pluginId: string): Promise<void> => {
        await apiClient.post(`/api/v1/plugins/${pluginId}/activate`);
    },

    // Deactivate a plugin
    deactivate: async (pluginId: string): Promise<void> => {
        await apiClient.post(`/api/v1/plugins/${pluginId}/deactivate`);
    },

    // Update plugin configuration
    updateConfig: async (pluginId: string, config: PluginConfigUpdate): Promise<void> => {
        await apiClient.put(`/api/v1/plugins/${pluginId}/config`, config);
    },

    // Upload a plugin zip
    upload: async (file: File): Promise<void> => {
        const formData = new FormData();
        formData.append('file', file);
        await apiClient.post('/api/v1/plugins/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },

    // Sync plugins with strategy core
    sync: async (): Promise<void> => {
        await apiClient.post('/api/v1/plugins/sync');
    },

    // Get system hooks
    getHooks: async (): Promise<SystemHooks> => {
        const response = await apiClient.get<APIResponse<SystemHooks>>('/api/v1/plugins/hooks');
        return response.data.data!;
    }
};
