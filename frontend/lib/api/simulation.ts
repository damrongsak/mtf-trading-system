import { SimulationConfig, SimulationResult } from './types';
import { apiClient } from './client';

/**
 * Run a GRID simulation via the backend
 */
export async function runSimulation(config: SimulationConfig): Promise<SimulationResult> {
    try {
        const response = await apiClient.post<SimulationResult>('/api/v1/simulation/', config);

        // apiClient returns the Axios response object. 
        // Our API wraps data in APIResponse structure, but apiClient generic T implies the data payload.
        // Actually, looking at client.ts, the interceptor might or might not unwrap.
        // Standard Axios: response.data is the payload.
        // Let's assume response.data is the APIResponse<SimulationResult>

        // Wait, looking at other files (e.g. journal.ts), it seems we expect apiClient.get<T> to return AxiosResponse<T>.
        // BUT the backend returns APIResponse<T>.
        // So T in apiClient.get<T> should be APIResponse<T> or the client unwraps it.

        // Let's check how other clients use it.
        // In journal.ts: const response = await apiClient.get<JournalEntry[]>('/api/v1/journal'); return response.data;
        // This implies response.data IS the T (JournalEntry[]).
        // If so, the interceptor must be unwrapping.

        // HOWEVER, the lint error says: "Property 'message' does not exist on type 'AxiosResponse<SimulationResult, any, {}>'".
        // This means `response` is an AxiosResponse.

        // If `response` is AxiosResponse<SimulationResult>, then `response.data` is `SimulationResult`.
        // The check `response.status === ResponseStatus.SUCCESS` is checking the HTTP status or the payload status?
        // `response.status` is HTTP status (number), ResponseStatus.SUCCESS is "success" (string).
        // This confirms the Type Mismatch lint error.

        // FIX: Check HTTP status 200/201, and return response.data.

        if (response.status === 200 || response.status === 201) {
            return response.data;
        }

        throw new Error('Simulation failed with status: ' + response.status);
    } catch (error) {
        console.error('Simulation API Error:', error);
        throw error;
    }
}
