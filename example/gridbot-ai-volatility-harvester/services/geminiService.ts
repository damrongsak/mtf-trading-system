
import { GoogleGenAI, Type } from "@google/genai";
import { BotStats, BotConfig, AIAnalysisResult } from '../types';

const apiKey = process.env.API_KEY || '';

// Initialize safely
const ai = new GoogleGenAI({ apiKey });

export const analyzePerformance = async (stats: BotStats, config: BotConfig): Promise<AIAnalysisResult | null> => {
  if (!apiKey) {
    console.error("API Key missing");
    return null;
  }

  try {
    const prompt = `
      You are a Senior Quantitative Researcher analyzing a Grid Trading Bot.
      
      Current Stats:
      - Equity: $${stats.totalEquity.toFixed(2)} (ROI: ${stats.roi.toFixed(2)}%)
      - Drawdown: ${stats.maxDrawdown.toFixed(2)}%
      - Volatility: ${stats.portfolioVolatility.toFixed(2)}%
      - Status: ${stats.status}
      
      Configuration:
      - Asset: ${config.assetSymbol}
      - Range: ${config.gridBottom} - ${config.gridTop}
      - Grid Count: ${config.gridCount} (${config.spacingType})
      - Sizing: ${config.sizingType}
      - Volatility Setting: ${config.volatility}
      - Trend Mode: ${config.trendMode}

      Task:
      1. Calculate a "Health Score" (0-100) based on risk-adjusted returns (Sharpe-like logic) and configuration safety.
      2. Provide a 2-sentence technical explanation of the score, focusing on risks like "Grid Exhaustion" or "Volatility Mismatch".
      3. Generate 3 distinct "Scenarios" (Conservative, Aggressive, Balanced) with specific configuration overrides to improve performance or adapt to the current regime.
    `;

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            healthScore: { type: Type.NUMBER, description: "0-100 score of strategy health" },
            explanation: { type: Type.STRING, description: "Technical explanation of the score" },
            suggestions: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  name: { type: Type.STRING, description: "Name of the scenario (e.g., 'Conservative Guard')" },
                  description: { type: Type.STRING, description: "Short description of the change" },
                  configOverrides: {
                    type: Type.OBJECT,
                    properties: {
                      gridTop: { type: Type.NUMBER },
                      gridBottom: { type: Type.NUMBER },
                      gridCount: { type: Type.NUMBER },
                      orderSize: { type: Type.NUMBER },
                      riskStopLoss: { type: Type.NUMBER },
                    }
                  }
                },
                required: ["name", "description", "configOverrides"]
              }
            }
          },
          required: ["healthScore", "explanation", "suggestions"]
        }
      }
    });

    return JSON.parse(response.text) as AIAnalysisResult;
  } catch (error) {
    console.error("Gemini analysis failed", error);
    return {
        healthScore: 50,
        explanation: "Analysis service unavailable. Check API connection.",
        suggestions: []
    };
  }
};

export const suggestParameters = async (description: string, currentPrice: number) => {
  if (!apiKey) throw new Error("API Key missing");

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: `Given a market description: "${description}" and a current price of ${currentPrice}, suggest optimal Grid Trading parameters.`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            gridTop: { type: Type.NUMBER },
            gridBottom: { type: Type.NUMBER },
            gridCount: { type: Type.NUMBER },
            volatility: { type: Type.NUMBER, description: "Suggested simulation volatility (0.001 to 0.05)" },
            reasoning: { type: Type.STRING }
          },
          required: ["gridTop", "gridBottom", "gridCount", "volatility", "reasoning"]
        }
      }
    });
    
    return JSON.parse(response.text);
  } catch (error) {
    console.error("Gemini suggestion failed", error);
    throw error;
  }
}
