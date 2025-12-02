import { apiClient } from './client';
import { APIResponse, UserResponse, LoginResult } from './types';

/**
 * Login with username and password
 * @param username - User's username
 * @param password - User's password
 * @returns Login result with user data and auth tokens
 */
export async function login(username: string, password: string): Promise<LoginResult> {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await apiClient.post<APIResponse<UserResponse>>('/api/v1/auth/token', formData, {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    });

    // Extract user data and auth tokens from wrapped response
    if (!response.data.data || !response.data.auth) {
        throw new Error('Invalid response from login endpoint');
    }

    return {
        user: response.data.data,
        auth: response.data.auth,
    };
}

/**
 * Get current user profile
 * @returns User profile data
 */
export async function getProfile(): Promise<UserResponse> {
    const response = await apiClient.get<APIResponse<UserResponse>>('/api/v1/auth/profile');

    if (!response.data.data) {
        throw new Error('Invalid response from profile endpoint');
    }

    return response.data.data;
}

/**
 * Register a new user
 * @param username - Username for the new account
 * @param email - Email address
 * @param password - Password
 * @returns Login result with user data and auth tokens
 */
export async function register(username: string, email: string, password: string): Promise<LoginResult> {
    const response = await apiClient.post<APIResponse<UserResponse>>('/api/v1/auth/register', {
        username,
        email,
        password,
    });

    // Extract user data and auth tokens from wrapped response
    if (!response.data.data || !response.data.auth) {
        throw new Error('Invalid response from register endpoint');
    }

    return {
        user: response.data.data,
        auth: response.data.auth,
    };
}
