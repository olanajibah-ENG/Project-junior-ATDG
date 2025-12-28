import axios, { type InternalAxiosRequestConfig, type AxiosResponse, type AxiosError } from 'axios';

const apiClient = axios.create({
    baseURL: '/api/upm', // يتطابق مع Backend
    timeout: 15000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Flag to prevent infinite refresh loops
let isRefreshing = false;
let failedQueue: Array<{
    resolve: (value?: unknown) => void;
    reject: (error?: unknown) => void;
}> = [];

const processQueue = (error: AxiosError | null, token: string | null = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

// Request interceptor: Add access token to all requests
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        // Skip token injection for auth endpoints
        const authEndpoints = ['/login/', '/signup/', '/api/token/refresh/', '/auth/token/verify/'];
        const isAuthEndpoint = authEndpoints.some(endpoint => config.url?.includes(endpoint));
        
        if (!isAuthEndpoint) {
            const accessToken = localStorage.getItem('access_token');
            if (accessToken) {
                config.headers.Authorization = `Bearer ${accessToken}`;
            }
        }
        
        return config;
    },
    (error: AxiosError) => {
        return Promise.reject(error);
    }
);

// Response interceptor: Handle 401 errors and refresh tokens
apiClient.interceptors.response.use(
    (response: AxiosResponse) => {
        return response;
    },
    async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // Handle 401 Unauthorized errors
        if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
            // Skip refresh for auth endpoints
            const authEndpoints = ['/login/', '/signup/', '/api/token/refresh/', '/auth/token/verify/'];
            const isAuthEndpoint = authEndpoints.some(endpoint => originalRequest.url?.includes(endpoint));
            
            if (isAuthEndpoint) {
                return Promise.reject(error);
            }

            if (isRefreshing) {
                // If already refreshing, queue this request
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                    .then((token) => {
                        if (originalRequest.headers) {
                            originalRequest.headers.Authorization = `Bearer ${token}`;
                        }
                        return apiClient(originalRequest);
                    })
                    .catch((err) => {
                        return Promise.reject(err);
                    });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            const refreshToken = localStorage.getItem('refresh_token');

            if (!refreshToken) {
                // No refresh token, logout user
                processQueue(error, null);
                isRefreshing = false;
                handleLogout();
                return Promise.reject(error);
            }

            try {
                // Attempt to refresh the token
                const response = await axios.post<{ access: string }>(
                    '/api/token/refresh/',
                    { refresh: refreshToken }
                );

                const { access } = response.data;

                // Update access token in localStorage
                localStorage.setItem('access_token', access);

                // Update the original request with new token
                if (originalRequest.headers) {
                    originalRequest.headers.Authorization = `Bearer ${access}`;
                }

                // Process queued requests
                processQueue(null, access);
                isRefreshing = false;

                // Retry the original request
                return apiClient(originalRequest);
            } catch (refreshError) {
                // Refresh failed, logout user
                processQueue(refreshError as AxiosError, null);
                isRefreshing = false;
                handleLogout();
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

// Helper function to handle logout
const handleLogout = () => {
    // Clear all auth data
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    
    // Dispatch custom event for AuthContext to handle
    window.dispatchEvent(new CustomEvent('auth:logout'));
};

export default apiClient;