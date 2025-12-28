// api.config.ts (الجديد)

const API_BASE_URL_DEV = '/api/upm'; 
const API_VERSION_CURRENT = 'v1';

// API Configuration 
export const API_CONFIG = {
  BASE_URL: API_BASE_URL_DEV,
  VERSION: API_VERSION_CURRENT,
  ENDPOINTS: {
    // ----------------------------------------------------
    // AUTHENTICATION & CORE - تم التعديل
    // ----------------------------------------------------
    SIGNUP: '/signup/', // 👈 تم التعديل
    LOGIN: '/login/',   // 👈 تم التعديل
    TOKEN_REFRESH: '/api/token/refresh/',
    TOKEN_VERIFY: '/auth/token/verify/', // بقي كما هو، قد تحتاج لتعديله إلى '/token/verify/' فقط لاحقاً
    
    // ----------------------------------------------------
    // UPM (المشاريع والمخرجات)
    // ----------------------------------------------------
    PROJECTS: '/projects/',
    // 👈 تم تغيير النوع إلى string فقط
    PROJECT_DETAIL: (id: string) => `/projects/${id}/`, 

    ARTIFACTS: '/artifacts/',
    // 👈 تم تغيير النوع إلى string فقط
    ARTIFACT_DETAIL: (id: string) => `/artifacts/${id}/`,
    // 👈 تم تغيير النوع إلى string فقط
    PROJECT_ARTIFACTS: (projectId: string) => `/projects/${projectId}/artifacts/`,
  },
  TIMEOUT: 15000, 
  // ... (HEADERS and API_RESPONSE_CONFIG remain the same)
} as const;

/**
 * دالة مساعدة لبناء عنوان URL الكامل (النسبي).
 */
export const buildApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// ----------------------------------------------------
// API ENDPOINTS BUILDERS (تنظيم الدوال)
// ----------------------------------------------------
export const API_ENDPOINTS = {
  auth: {
    signup: () => buildApiUrl(API_CONFIG.ENDPOINTS.SIGNUP),
    login: () => buildApiUrl(API_CONFIG.ENDPOINTS.LOGIN),
    refreshToken: () => buildApiUrl(API_CONFIG.ENDPOINTS.TOKEN_REFRESH),
    verifyToken: () => buildApiUrl(API_CONFIG.ENDPOINTS.TOKEN_VERIFY),
  },
  projects: {
    list: () => buildApiUrl(API_CONFIG.ENDPOINTS.PROJECTS),
    create: () => buildApiUrl(API_CONFIG.ENDPOINTS.PROJECTS),
    // 👈 تم تغيير النوع إلى string فقط
    detail: (id: string) => buildApiUrl(API_CONFIG.ENDPOINTS.PROJECT_DETAIL(id)),
  },
  artifacts: {
    list: () => buildApiUrl(API_CONFIG.ENDPOINTS.ARTIFACTS),
    create: () => buildApiUrl(API_CONFIG.ENDPOINTS.ARTIFACTS),
    // 👈 تم تغيير النوع إلى string فقط
    detail: (id: string) => buildApiUrl(API_CONFIG.ENDPOINTS.ARTIFACT_DETAIL(id)),
    // 👈 تم تغيير النوع إلى string فقط
    projectArtifacts: (projectId: string) => buildApiUrl(API_CONFIG.ENDPOINTS.PROJECT_ARTIFACTS(projectId)),
  },
} as const;