/**
 * frontend/lib/api/client.ts
 * Cliente HTTP centralizado con refresh automático de JWT.
 */
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import Cookies from "js-cookie";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
  withCredentials: false,
});

type RetriableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

type TokenRefreshResponse = {
  access: string;
  refresh: string;
};

const clearSession = () => {
  Cookies.remove("access_token");
  Cookies.remove("refresh_token");
  if (typeof window !== "undefined") window.location.href = "/login";
};

export const guardarTokens = (accessToken: string, refreshToken: string) => {
  const opcionesCookie = { secure: process.env.NODE_ENV === "production" };
  Cookies.set("access_token", accessToken, { ...opcionesCookie, expires: 1 / 24 });
  Cookies.set("refresh_token", refreshToken, { ...opcionesCookie, expires: 7 });
};

// ── Request interceptor: adjunta el access token ──────────────────────────────
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = Cookies.get("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

let refreshPromise: Promise<string> | null = null;

const refreshSession = (): Promise<string> => {
  if (!refreshPromise) {
    const refreshToken = Cookies.get("refresh_token");
    if (!refreshToken) {
      clearSession();
      return Promise.reject(new Error("No hay un token de actualización disponible."));
    }

    refreshPromise = axios
      .post<TokenRefreshResponse>(`${BASE_URL}/auth/token/refresh/`, {
        refresh: refreshToken,
      })
      .then(({ data }) => {
        guardarTokens(data.access, data.refresh);
        return data.access;
      })
      .catch((error: unknown) => {
        clearSession();
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

// ── Response interceptor: comparte un único refresh entre peticiones concurrentes ─
api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) return Promise.reject(error);

    const originalRequest = error.config as RetriableRequestConfig | undefined;
    const requestUrl = originalRequest?.url ?? "";

    if (
      !originalRequest ||
      error.response?.status !== 401 ||
      originalRequest._retry ||
      requestUrl.includes("/auth/login/") ||
      requestUrl.includes("/auth/token/refresh/")
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const accessToken = await refreshSession();
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return await api(originalRequest);
    } catch (refreshError) {
      return Promise.reject(refreshError);
    }
  },
);

export default api;
