/**
 * Cliente HTTP único. Todas las llamadas pasan por el proxy de Next (/api/proxy),
 * que agrega el token desde la cookie httpOnly y renueva la sesión si expira (F4-05).
 * La URL real de Django (NEXT_PUBLIC_API_URL / API_INTERNAL_URL) solo la conoce el servidor.
 */
import axios from "axios";

const api = axios.create({
  baseURL: "/api/proxy",
  timeout: 20_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (r) => r,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401 && typeof window !== "undefined") {
      // El proxy ya intentó renovar la sesión: si sigue en 401, la sesión terminó.
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
      }
    }
    return Promise.reject(error);
  },
);

export default api;
