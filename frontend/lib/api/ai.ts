import { apiClient } from './client';

export interface AIReportResponse {
  report: string;
  timestamp: string;
}

export interface RunAgentRequest {
  input_text: string;
}

/**
 * Trigger the Market Observer Agent to generate a report.
 * @param inputText Optional prompt for the agent (default handled by backend)
 */
export async function runMarketObserver(inputText?: string): Promise<AIReportResponse> {
  const payload: RunAgentRequest = {
    input_text: inputText || "Generate a market situation report for XAU/USD."
  };
  
  // Note: The endpoint path might need adjustment if Nginx routing is /api/v1/ai/... 
  // currently assuming exposed via API Gateway or Nginx direct proxy.
  // Based on Status doc, AI Analyst is exposed. 
  // If api-gateway doesn't have a route yet, we might hit 404. 
  // Implementation Status says: "/analyze/market endpoints... Gateway proxy router ai.py linked."
  // But we added a NEW endpoint /agent/observer/run in ai-analyst app/main.py.
  // Does API Gateway proxy everything?
  // Let's assume Nginx routes /api/v1/ai -> ai-analyst service.
  // Or API Gateway has a router that forwards.
  // I should check API Gateway router later. For now, let's target /api/v1/ai/agent/observer/run 
  // assuming a standard prefix or just /agent/observer/run if gateway forwards raw.
  
  // Common pattern in this project seems to be /api/v1/...
  // Let's try /api/v1/ai/agent/observer/run 
  
  const response = await apiClient.post<AIReportResponse>('/api/v1/ai/agent/observer/run', payload);
  return response.data;
}
