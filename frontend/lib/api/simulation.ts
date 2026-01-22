import { SimulationConfig, SimulationResult } from './types';
import { apiClient } from './client';
import { logger } from '@/lib/api/app-logger';

/**
 * Run a GRID simulation via the backend
 */
export async function runSimulation(config: SimulationConfig): Promise<SimulationResult> {
    try {
        const response = await apiClient.post<SimulationResult>('/api/v1/simulation/', config);

        if (response.status === 200 || response.status === 201) {
            return response.data;
        }

        throw new Error('Simulation failed with status: ' + response.status);
    } catch (error) {
        logger.error('Simulation API Error:', error);
        throw error;
    }
}
