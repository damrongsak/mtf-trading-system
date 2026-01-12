import { Time, CandlestickData, HistogramData, WhitespaceData } from 'lightweight-charts';

// Type guard for valid numbers
const isValidNumber = (val: any): val is number => {
    return typeof val === 'number' && !Number.isNaN(val) && Number.isFinite(val);
};

export const cleanCandleData = (data: any[]): CandlestickData<Time>[] => {
    return data
        .map((item) => {
            const time = new Date(item.timestamp).getTime() / 1000;
            if (isNaN(time) ||
                !isValidNumber(Number(item.open)) ||
                !isValidNumber(Number(item.high)) ||
                !isValidNumber(Number(item.low)) ||
                !isValidNumber(Number(item.close))) {
                return null;
            }
            return {
                time: time as Time,
                open: Number(item.open),
                high: Number(item.high),
                low: Number(item.low),
                close: Number(item.close),
            };
        })
        .filter((item): item is CandlestickData<Time> => item !== null)
        .sort((a, b) => (a.time as number) - (b.time as number));
};

export const cleanLineSeriesData = (data: any[], timeKey: string = 'time', valueKey: string = 'value'): { time: Time, value: number }[] => {
    return data.map(d => {
        let val = d[valueKey];
        // LineSeries SUPPORTS NaN for gaps, so we convert null/undefined to NaN
        if (val === null || val === undefined || !Number.isFinite(val)) {
            val = NaN;
        }

        let time = d[timeKey];
        // Ensure time is valid
        if (typeof time !== 'number' && d.timestamp) {
            time = new Date(d.timestamp).getTime() / 1000;
        }

        return {
            time: time as Time,
            value: val
        };
    });
    // Note: We do NOT filter out NaNs here because LineSeries uses them for gaps
};

export const cleanHistogramData = (
    data: any[],
    colorPos: string = '#26a69a',
    colorNeg: string = '#ef5350',
    timeKey: string = 'time',
    valueKey: string = 'value'
): HistogramData<Time>[] => {
    return data
        .filter(d => {
            const val = d[valueKey];
            const histVal = d['hist']; // Handle special case for MACD-like structures if passed directly?
            // Actually, let's keep it generic.
            // If the user passes raw objects, we need to know where the value is.
            // Support both direct valueKey OR 'hist' property if valueKey finds nothing? 
            // Better to be explicit in args.

            // Check value
            const checkVal = val !== undefined ? val : (d.hist !== undefined ? d.hist : undefined);

            return checkVal !== null && checkVal !== undefined && isValidNumber(checkVal);
        })
        .map(d => {
            const val = d[valueKey] !== undefined ? d[valueKey] : d.hist;
            let time = d[timeKey];
            // Ensure time is valid
            if (typeof time !== 'number' && d.timestamp) {
                time = new Date(d.timestamp).getTime() / 1000;
            }

            return {
                time: time as Time,
                value: val,
                color: (val >= 0 ? colorPos : colorNeg)
            };
        });
};
