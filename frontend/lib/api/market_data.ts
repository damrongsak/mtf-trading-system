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

