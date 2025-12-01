import { apiClient } from './client';
import { LoginResponse, User } from './types';

/**
 * Login with username and password
 * @param username - User's username
 * @param password - User's password
 * @returns Login response with access token
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await apiClient.post<LoginResponse>('/api/v1/auth/token', formData, {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    });

    return response.data;
}

/**
 * Get current user profile
 * @returns User profile data
 */
export async function getProfile(): Promise<User> {
    const response = await apiClient.get<User>('/api/v1/auth/profile');
    return response.data;
}

/**
 * Register a new user
 * @param username - Username for the new account
 * @param email - Email address
 * @param password - Password
 * @returns User data
 */
export async function register(username: string, email: string, password: string): Promise<User> {
    const response = await apiClient.post<User>('/api/v1/auth/register', {
        username,
        email,
        password,
    });
    return response.data;
}
