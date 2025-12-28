
import axios, { type AxiosInstance } from 'axios';
import apiClient from './apiClient';
import { API_ENDPOINTS, API_CONFIG } from '../config/api.config';

// Helper to convert full API endpoint URLs to relative paths for apiClient
// Since apiClient already has baseURL: '/api/upm', we need to strip it from endpoints
const getRelativePath = (fullUrl: string): string => {
    const baseUrl = API_CONFIG.BASE_URL;
    if (fullUrl.startsWith(baseUrl)) {
        return fullUrl.substring(baseUrl.length);
    }
    return fullUrl;
};

// ----------------------------------------------------
// تعريف الـ TYPES الأساسية
// ----------------------------------------------------

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

export interface Project {
    id: string; // UUID format
    title: string; // Required, max 255 chars
    description: string; // Optional, can be empty
    user: number; // User ID (read-only)
    username: string; // Username (read-only) - per API docs
    created_at: string; // ISO 8601 datetime (read-only)
    updated_at: string; // ISO 8601 datetime (read-only)
}

export interface CreateProjectData {
    title: string;
    description: string;
}

export interface UpdateProjectData {
    title?: string;
    description?: string;
}

// Auth Types
export interface LoginData {
    username: string;
    password: string;
}

export interface SignupData {
    username: string;
    email: string;
    password: string;
}

// Profile types based on API documentation
export interface UserRole {
    id: number;
    role_name: string;
    description: string;
    permissions_list: Record<string, unknown>;
}

export interface UserProfile {
    full_name: string;
    signup_date: string;
    role: UserRole | null;
}

export interface User {
    id: number;
    username: string;
    email: string;
    profile: UserProfile | null;
}

// Login response includes tokens + user
export interface AuthResponse {
    access: string;
    refresh: string;
    user: User;
}

// Signup response only includes user (no tokens)
export interface SignupResponse {
    id: number;
    username: string;
    email: string;
    profile: UserProfile | null;
}

// User type for context and storage
export interface CurrentUser {
    id: number;
    username: string;
    email: string;
    profile: UserProfile | null;
}

// ----------------------------------------------------
// Error handling helper
// ----------------------------------------------------
export interface ApiError {
    detail?: string;
    [key: string]: string[] | string | undefined; // For field-specific errors
}

export const formatApiError = (error: any): string => {
    if (error.response?.data) {
        const errorData: ApiError = error.response.data;
        
        // Check for detail field first
        if (errorData.detail) {
            return errorData.detail;
        }
        
        // Check for field-specific errors
        const fieldErrors: string[] = [];
        for (const [key, value] of Object.entries(errorData)) {
            if (Array.isArray(value) && value.length > 0) {
                fieldErrors.push(`${key}: ${value.join(', ')}`);
            } else if (typeof value === 'string') {
                fieldErrors.push(`${key}: ${value}`);
            }
        }
        
        if (fieldErrors.length > 0) {
            return fieldErrors.join('; ');
        }
    }
    
    return error.message || 'An unexpected error occurred';
};


// ----------------------------------------------------
// BaseService (الخدمة الأساسية لـ CRUD)
// ----------------------------------------------------
class BaseService {
    protected apiClient: AxiosInstance = apiClient;
    
    protected async get<T>(url: string): Promise<T> {
        const response = await this.apiClient.get<T>(url);
        
        // ✅ التحقق الدفاعي من أن الجسم ليس فارغاً
        if (!response.data) {
             throw new Error(`API returned success for ${url} but the data body was empty.`);
        }
        
        return response.data;
    }
    protected async post<T, D>(url: string, data: D): Promise<T> {
        const response = await this.apiClient.post<T>(url, data);
        return response.data;
    }
    protected async patch<T, D>(url: string, data: D): Promise<T> { 
        const response = await this.apiClient.patch<T>(url, data);
        return response.data;
    }
    protected async delete(url: string): Promise<void> {
        await this.apiClient.delete(url);
    }
}


// ----------------------------------------------------
// AuthService Class
// ----------------------------------------------------
class AuthService extends BaseService {
    async login(credentials: LoginData): Promise<AuthResponse> {
        return this.post<AuthResponse, LoginData>(getRelativePath(API_ENDPOINTS.auth.login()), credentials);
    }

    async signup(data: SignupData): Promise<SignupResponse> {
        return this.post<SignupResponse, SignupData>(getRelativePath(API_ENDPOINTS.auth.signup()), data);
    }

    async refreshToken(refresh: string): Promise<{ access: string }> {
        // Token refresh uses absolute path outside /api/upm, so use axios directly
        const response = await axios.post<{ access: string }>(API_ENDPOINTS.auth.refreshToken(), { refresh });
        return response.data;
    }

    async verifyToken(token: string): Promise<boolean> {
        try {
            await this.post(getRelativePath(API_ENDPOINTS.auth.verifyToken()), { token });
            return true;
        } catch {
            return false;
        }
    }
}

// ----------------------------------------------------
// ApiService Class
// ----------------------------------------------------
export class ApiService extends BaseService {
    // 1. Get list of projects (with pagination support)
    async getProjects(page: number = 1, pageSize: number = 20): Promise<PaginatedResponse<Project>> {
        const basePath = getRelativePath(API_ENDPOINTS.projects.list());
        const url = `${basePath}?page=${page}&page_size=${pageSize}`;
        return this.get<PaginatedResponse<Project>>(url);
    }

    // 2. Get a single project by ID
    async getProject(id: string): Promise<Project> {
        return this.get<Project>(getRelativePath(API_ENDPOINTS.projects.detail(id)));
    }

    // 3. Create a new project
    async createProject(projectData: CreateProjectData): Promise<Project> {
        return this.post<Project, CreateProjectData>(getRelativePath(API_ENDPOINTS.projects.create()), projectData);
    }

    // 4. Update an existing project (PATCH - partial update)
    async updateProject(id: string, projectData: UpdateProjectData): Promise<Project> {
        return this.patch<Project, UpdateProjectData>(getRelativePath(API_ENDPOINTS.projects.detail(id)), projectData);
    }
    
    // 5. Delete a project
    async deleteProject(id: string): Promise<void> {
        await this.delete(getRelativePath(API_ENDPOINTS.projects.detail(id)));
    }
}

// ----------------------------------------------------
// Default Export - API Service Instance
// ----------------------------------------------------
const authService = new AuthService();

const apiService = {
    auth: authService,
};

export default apiService;