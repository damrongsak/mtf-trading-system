import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type IndicatorType = 'EMA' | 'RSI' | 'MACD' | 'ATR' | 'ADX' | 'SMC' | 'GAMMA';

export interface ActiveIndicator {
    id: string;
    type: IndicatorType;
    params: Record<string, number | string | boolean>;
    color?: string;
    visible: boolean;
}

interface IndicatorStore {
    indicators: ActiveIndicator[];
    addIndicator: (type: IndicatorType, defaultParams: Record<string, number | string | boolean>, color?: string) => void;
    updateIndicator: (id: string, updates: Partial<ActiveIndicator>) => void;
    removeIndicator: (id: string) => void;
    toggleVisibility: (id: string) => void;
}

const generateId = () => Math.random().toString(36).substring(2, 9);

export const useIndicatorStore = create<IndicatorStore>()(
    persist(
        (set) => ({
            indicators: [
                { id: generateId(), type: 'EMA', params: { period: 200 }, color: '#3b82f6', visible: true },
                { id: generateId(), type: 'ATR', params: { period: 14 }, color: '#ec4899', visible: true },
            ],
            addIndicator: (type, defaultParams, color) => set((state) => ({
                indicators: [...state.indicators, {
                    id: generateId(),
                    type,
                    params: defaultParams,
                    color: color || '#3b82f6',
                    visible: true
                }]
            })),
            updateIndicator: (id, updates) => set((state) => ({
                indicators: state.indicators.map(ind =>
                    ind.id === id ? { ...ind, ...updates } : ind
                )
            })),
            removeIndicator: (id) => set((state) => ({
                indicators: state.indicators.filter(ind => ind.id !== id)
            })),
            toggleVisibility: (id) => set((state) => ({
                indicators: state.indicators.map(ind =>
                    ind.id === id ? { ...ind, visible: !ind.visible } : ind
                )
            }))
        }),
        {
            name: 'mtf-indicators-storage',
        }
    )
);
