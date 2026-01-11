import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { ApiError } from './errors';

export const handleApiError = (error: unknown): ApiError => {
    if (error instanceof ApiError) return error;
    if (axios.isAxiosError(error)) {
        return new ApiError(error.message, error.response?.status, error.response?.data);
    }
    return new ApiError(error instanceof Error ? error.message : 'Unknown error');
};

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || '',
    timeout: 310000,
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
            if (config.data) {
                console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data);
            } else {
                console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
            }
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
            if (!data?.detail && !data?.message) {
                switch (error.response.status) {
                    case 401:
                        message = 'Authentication required. Please log in.';
                        // Optionally redirect to login or trigger logout
                        if (typeof window !== 'undefined') {
                            // You could dispatch a logout event here
                            if (process.env.NODE_ENV === 'development') console.warn('[API] Unauthorized - token may be expired');
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
            // specific status codes that are expected/handled
            if (status !== 401 && status !== 404) {
                console.error(`[API Error] ${status || 'Unknown'}: ${message}`, details ? details : '');
            }
        }

        throw apiError;
    }
);


import { Configuration, DefaultApi, AnalysisApi, FoundryApi } from './generated';

const apiConfig = new Configuration({
    basePath: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
});

// Initialize API clients with the axios instance that handles auth/logging
export const defaultApi = new DefaultApi(apiConfig, undefined, apiClient);
export const analysisApi = new AnalysisApi(apiConfig, undefined, apiClient);
export const foundryApi = new FoundryApi(apiConfig, undefined, apiClient);

export { apiClient };

