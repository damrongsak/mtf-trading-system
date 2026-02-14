import { analysisApi } from '@/lib/api/client';
import { ChartPriceLine } from '@/components/charts/CandleChart';
import { logger } from '@/lib/api/app-logger';

export interface GammaLevelsData {
    gammaPriceLines: ChartPriceLine[];
    marketRegime: string;
}

export function useGammaLevels(symbol: string, currentPrice: number, enabled: boolean) {
    const [data, setData] = useState<GammaLevelsData>({ gammaPriceLines: [], marketRegime: 'Neutral' });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!enabled || !symbol) {
            setData({ gammaPriceLines: [], marketRegime: 'Neutral' });
            return;
        }

        const fetchGamma = async () => {
            setLoading(true);
            try {
                const response = await analysisApi.analysisGammaLevelsGet(symbol, currentPrice);


                if (response.data && response.data.status === 'success' && response.data.data) {
                    const levels = response.data.data;
                    const lines: ChartPriceLine[] = [];

                    // Call Wall
                    if (levels.call_wall) {
                        lines.push({
                            price: levels.call_wall,
                            color: '#ef4444', // Red
                            title: 'Call Wall',
                            lineWidth: 2,
                            lineStyle: 0, // Solid
                            axisLabelVisible: true
                        });
                    }

                    // Put Wall
                    if (levels.put_wall) {
                        lines.push({
                            price: levels.put_wall,
                            color: '#22c55e', // Green
                            title: 'Put Wall',
                            lineWidth: 2,
                            lineStyle: 0, // Solid
                            axisLabelVisible: true
                        });
                    }

                    // Gamma Flip
                    if (levels.gamma_flip) {
                        lines.push({
                            price: levels.gamma_flip,
                            color: '#a855f7', // Purple
                            title: 'Gamma Flip',
                            lineWidth: 1,
                            lineStyle: 2, // Dashed
                            axisLabelVisible: true
                        });
                    }

                    setData({
                        gammaPriceLines: lines,
                        marketRegime: levels.regime || 'Neutral'
                    });
                }
            } catch (error) {
                logger.error("Failed to fetch Gamma Levels", error);
            } finally {
                setLoading(false);
            }
        };

        fetchGamma();
    }, [symbol, enabled, currentPrice]); // Re-fetch on symbol change or enable toggle. Price change might be too frequent?
    // Maybe debounce price or just fetch once?
    // Gamma Analysis usually valid for the day/session.
    // Let's keep it simple: fetch when enabled or symbol changes.
    // user might want to refresh manually.

    return { ...data, loading };
}
