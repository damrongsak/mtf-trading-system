import { apiClient } from './client';

export interface MarketCategorySymbol {
    id: string;
    symbol: string;
    display_name: string;
    broker?: string;
    category_id: string;
    order_index: number;
}

export interface MarketCategory {
    id: string;
    name: string;
    order_index: number;
    items: MarketCategorySymbol[];
}

export async function getMarketCategories(): Promise<MarketCategory[]> {
    const response = await apiClient.get<MarketCategory[]>('/api/v1/market/categories');
    return response.data;
}

export async function createMarketCategory(name: string): Promise<MarketCategory> {
    const response = await apiClient.post<MarketCategory>('/api/v1/market/categories', { name });
    return response.data;
}

export async function addSymbolToCategory(categoryId: string, symbol: string, displayName?: string): Promise<MarketCategorySymbol> {
    const response = await apiClient.post<MarketCategorySymbol>(`/api/v1/market/categories/${categoryId}/symbols`, {
        symbol,
        display_name: displayName
    });
    return response.data;
}
