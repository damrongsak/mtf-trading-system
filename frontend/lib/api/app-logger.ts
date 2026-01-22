/**
 * Simple logger utility for the frontend.
 * Provides a central point for logging that can be easily configured or disabled.
 */

const IS_PRODUCTION = process.env.NODE_ENV === 'production';

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

class Logger {
    private isEnabled: boolean = !IS_PRODUCTION;

    constructor() {
        // You could also check for a localStorage flag here for debugging in production
        if (typeof window !== 'undefined' && localStorage.getItem('ENABLE_LOGS') === 'true') {
            this.isEnabled = true;
        }
    }

    private log(level: LogLevel, message: unknown, ...args: unknown[]) {
        if (!this.isEnabled && level !== 'error' && level !== 'warn') return;

        const timestamp = new Date().toISOString();
        const prefix = `[${timestamp}] [${level.toUpperCase()}]`;

        switch (level) {
            case 'debug':
                console.debug(prefix, message, ...args);
                break;
            case 'info':
                console.info(prefix, message, ...args);
                break;
            case 'warn':
                console.warn(prefix, message, ...args);
                break;
            case 'error':
                console.error(prefix, message, ...args);
                break;
        }
    }

    debug(message: unknown, ...args: unknown[]) {
        this.log('debug', message, ...args);
    }

    info(message: unknown, ...args: unknown[]) {
        this.log('info', message, ...args);
    }

    warn(message: unknown, ...args: unknown[]) {
        this.log('warn', message, ...args);
    }

    error(message: unknown, ...args: unknown[]) {
        this.log('error', message, ...args);
    }

    enable() {
        this.isEnabled = true;
    }

    disable() {
        this.isEnabled = false;
    }
}

export const logger = new Logger();
