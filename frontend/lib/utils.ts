import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Format a date string to a localized date/time format
 */
export function formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString();
}

/**
 * Format a date string to a localized date format
 */
export function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

/**
 * Format a number as currency (USD)
 */
export function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(amount);
}

/**
 * Format a number as percentage
 */
export function formatPercentage(value: number, decimals: number = 2): string {
    return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Calculate R-multiple from P&L and risk amount
 */
export function calculateRMultiple(pnl: number, riskAmount: number): number {
    if (riskAmount === 0) return 0;
    return pnl / riskAmount;
}

/**
 * Get color class for P&L display
 */
export function getPnLColorClass(pnl: number): string {
    if (pnl > 0) return 'text-green-500';
    if (pnl < 0) return 'text-red-500';
    return 'text-gray-500';
}

/**
 * Get color class for game level
 */
export function getGameLevelColor(gameLevel: string): string {
    switch (gameLevel) {
        case 'A_GAME':
            return 'text-green-400';
        case 'B_GAME':
            return 'text-yellow-400';
        case 'C_GAME':
            return 'text-red-400';
        default:
            return 'text-gray-400';
    }
}

/**
 * Format game level for display
 */
export function formatGameLevel(gameLevel: string): string {
    return gameLevel.replace('_', ' ');
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: never[]) => unknown>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: NodeJS.Timeout | null = null;

    return function executedFunction(...args: Parameters<T>) {
        const later = () => {
            timeout = null;
            func(...args);
        };

        if (timeout) clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function
 */
export function throttle<T extends (...args: never[]) => unknown>(
    func: T,
    limit: number
): (...args: Parameters<T>) => void {
    let inThrottle: boolean;

    return function executedFunction(...args: Parameters<T>) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    };
}

/**
 * Check if code is running on the client side
 */
export function isClient(): boolean {
    return typeof window !== 'undefined';
}

/**
 * Safe localStorage wrapper
 */
export const storage = {
    get(key: string): string | null {
        if (!isClient()) return null;
        try {
            return localStorage.getItem(key);
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return null;
        }
    },

    set(key: string, value: string): void {
        if (!isClient()) return;
        try {
            localStorage.setItem(key, value);
        } catch (error) {
            console.error('Error writing to localStorage:', error);
        }
    },

    remove(key: string): void {
        if (!isClient()) return;
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('Error removing from localStorage:', error);
        }
    },

    clear(): void {
        if (!isClient()) return;
        try {
            localStorage.clear();
        } catch (error) {
            console.error('Error clearing localStorage:', error);
        }
    },
};

/**
 * Class name utility for conditional classes
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}
