import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

// Custom API Error class
export class ApiError extends Error {
    status?: number;
    details?: unknown;

    constructor(message: string, status?: number, details?: unknown) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.details = details;
        Object.setPrototypeOf(this, ApiError.prototype);
    }
}

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || '',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor - inject auth token
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        // Get token from localStorage
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        // Log requests in development
        if (process.env.NODE_ENV === 'development') {
            console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data);
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor - handle errors globally
apiClient.interceptors.response.use(
    (response) => {
        // Log successful responses in development
        if (process.env.NODE_ENV === 'development') {
            console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
        }
        return response;
    },
    (error: AxiosError) => {
        let message = 'An unexpected error occurred';
        const status = error.response?.status;
        const details = error.response?.data;

        if (error.response) {
            // Server responded with error status
            const data = error.response.data as Record<string, unknown>;
            message = (data?.detail as string) || (data?.message as string) || `Error: ${error.response.status}`;

            // Handle specific status codes
            switch (error.response.status) {
                case 401:
                    message = 'Authentication required. Please log in.';
                    // Optionally redirect to login or trigger logout
                    if (typeof window !== 'undefined') {
                        // You could dispatch a logout event here
                        console.warn('[API] Unauthorized - token may be expired');
                    }
                    break;
                case 403:
                    message = 'You do not have permission to perform this action.';
                    break;
                case 404:
                    message = 'The requested resource was not found.';
                    break;
                case 422:
                    message = 'Validation error. Please check your input.';
                    break;
                case 500:
                    message = 'Server error. Please try again later.';
                    break;
            }
        } else if (error.request) {
            // Request was made but no response received
            message = 'Network error. Please check your connection.';
        } else {
            // Something else happened
            message = error.message || 'An unexpected error occurred';
        }

        // Create proper ApiError instance
        const apiError = new ApiError(message, status, details);

        // Log errors in development
        if (process.env.NODE_ENV === 'development') {
            console.error('[API Error]', {
                message: apiError.message,
                status: apiError.status,
                details: apiError.details,
            });
        }

        throw apiError;
    }
);

export { apiClient, ApiError };
