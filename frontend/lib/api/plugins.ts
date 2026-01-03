import { apiClient } from './client';
import { Plugin, PluginConfigUpdate } from './types';

export const pluginsApi = {
    // List all plugins
    list: async (): Promise<Plugin[]> => {
        const response = await apiClient.get<Plugin[]>('/api/v1/plugins');
        return response.data;
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
    }
};
