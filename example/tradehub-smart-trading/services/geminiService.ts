import { GoogleGenAI, Type, SchemaType } from "@google/genai";

// Initialize the client
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });

export const getMarketAnalysis = async (query: string): Promise<string> => {
  try {
    const model = 'gemini-2.5-flash';
    
    const response = await ai.models.generateContent({
      model: model,
      contents: `You are a professional financial trading assistant. 
      Analyze the following query concisely for a trader: "${query}". 
      Keep the tone professional, objective, and risk-aware. 
      Limit response to 3 sentences.`,
    });

    return response.text || "Analysis currently unavailable.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "Unable to connect to market analysis service at this time.";
  }
};

export const getPortfolioInsight = async (totalBalance: number, pl: number): Promise<string> => {
    try {
        const model = 'gemini-2.5-flash';
        const prompt = `
            I am a trader. My total balance is ${totalBalance} and my current unrealized P/L is ${pl}.
            Give me a very short, 1-sentence motivational or cautionary advice based on this performance.
        `;
        const response = await ai.models.generateContent({
            model: model,
            contents: prompt,
        });
        return response.text || "Keep watching the markets.";
    } catch (e) {
        return "Data analysis unavailable.";
    }
}