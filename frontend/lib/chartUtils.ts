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
    return data
        .map(d => {
            const val = d[valueKey];
            let time = d[timeKey];

            // Ensure time is valid
            if (typeof time !== 'number' && d.timestamp) {
                time = new Date(d.timestamp).getTime() / 1000;
            }

            // Check if time is valid
            if (time === null || time === undefined || (typeof time === 'number' && isNaN(time))) {
                return null;
            }

            // Check if value is valid
            if (val === null || val === undefined || !Number.isFinite(val)) {
                return null;
            }

            return {
                time: time as Time,
                value: Number(val)
            };
        })
        .filter((item): item is { time: Time, value: number } => item !== null);
};

export const cleanHistogramData = (
    data: any[],
    colorPos: string = '#26a69a',
    colorNeg: string = '#ef5350',
    timeKey: string = 'time',
    valueKey: string = 'value'
): HistogramData<Time>[] => {
    return data
        .map(d => {
            // valueKey takes precedence
            let val = d[valueKey];

            // If explicit valueKey result is undefined, try 'hist' fallback
            if (val === undefined) {
                val = d['hist'];
            }

            let time = d[timeKey];

            // Ensure time is valid
            if (typeof time !== 'number' && d.timestamp) {
                time = new Date(d.timestamp).getTime() / 1000;
            }

            // Check if time is valid
            if (time === null || time === undefined || (typeof time === 'number' && isNaN(time))) {
                return null;
            }

            // Check validation (Strict checks)
            if (val === null || val === undefined) {
                return null;
            }

            const numVal = Number(val);
            if (!Number.isFinite(numVal)) {
                return null;
            }

            return {
                time: time as Time,
                value: numVal,
                color: (numVal >= 0 ? colorPos : colorNeg)
            };
        })
        .filter((item): item is HistogramData<Time> => item !== null);
};
