import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { ApiError } from './types';

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
        // Transform axios error to our custom ApiError
        const apiError: ApiError = {
            message: 'An unexpected error occurred',
            status: error.response?.status,
            details: error.response?.data,
        };

        if (error.response) {
            // Server responded with error status
            const data = error.response.data as Record<string, unknown>;
            apiError.message = (data?.detail as string) || (data?.message as string) || `Error: ${error.response.status}`;

            // Handle specific status codes
            switch (error.response.status) {
                case 401:
                    apiError.message = 'Authentication required. Please log in.';
                    // Optionally redirect to login or trigger logout
                    if (typeof window !== 'undefined') {
                        // You could dispatch a logout event here
                        console.warn('[API] Unauthorized - token may be expired');
                    }
                    break;
                case 403:
                    apiError.message = 'You do not have permission to perform this action.';
                    break;
                case 404:
                    apiError.message = 'The requested resource was not found.';
                    break;
                case 422:
                    apiError.message = 'Validation error. Please check your input.';
                    break;
                case 500:
                    apiError.message = 'Server error. Please try again later.';
                    break;
            }
        } else if (error.request) {
            // Request was made but no response received
            apiError.message = 'Network error. Please check your connection.';
        } else {
            // Something else happened
            apiError.message = error.message || 'An unexpected error occurred';
        }

        // Log errors in development
        if (process.env.NODE_ENV === 'development') {
            console.error('[API Error]', apiError);
        }

        return Promise.reject(apiError);
    }
);

export { apiClient };
export type { ApiError };
