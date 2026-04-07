import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserOut {
  id: string;
  tenant_id: string;
  email: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface LogOut {
  id: string;
  tenant_id: string;
  event_type: string;
  severity: "low" | "medium" | "high" | "critical";
  source_ip: string | null;
  endpoint: string | null;
  status_code: number | null;
  anomaly_score: number | null;
  is_anomaly: boolean;
  resolved: boolean;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface LogListResponse {
  items: LogOut[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsResponse {
  total_today: number;
  high_severity: number;
  medium_severity: number;
  anomaly_score_avg: number;
  active_tenants: number;
}

export interface TimeseriesPoint {
  hour: string;
  total: number;
  high: number;
}

export interface LogIngest {
  event_type: string;
  source_ip?: string;
  user_agent?: string;
  endpoint?: string;
  status_code?: number;
  payload?: Record<string, unknown>;
}

// ── Token storage (in-memory — httpOnly cookie preferred in prod) ──

let _accessToken: string | null = null;
let _refreshToken: string | null = null;

export function setTokens(access: string, refresh: string) {
  _accessToken = access;
  _refreshToken = refresh;
  if (typeof window !== "undefined") {
    sessionStorage.setItem("access_token", access);
    sessionStorage.setItem("refresh_token", refresh);
  }
}

export function loadTokens() {
  if (typeof window !== "undefined") {
    _accessToken = sessionStorage.getItem("access_token");
    _refreshToken = sessionStorage.getItem("refresh_token");
  }
}

export function clearTokens() {
  _accessToken = null;
  _refreshToken = null;
  if (typeof window !== "undefined") {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
  }
}

export function getAccessToken() {
  return _accessToken;
}

// ── Axios instance ────────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api`,
  timeout: 15_000,
});

// Attach Bearer token
api.interceptors.request.use((config) => {
  loadTokens();
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`;
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config as AxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !original._retry && _refreshToken) {
      original._retry = true;
      try {
        const res = await axios.post<TokenResponse>(`${BASE_URL}/api/auth/refresh`, {
          refresh_token: _refreshToken,
        });
        setTokens(res.data.access_token, res.data.refresh_token);
        original.headers = {
          ...original.headers,
          Authorization: `Bearer ${res.data.access_token}`,
        };
        return api(original);
      } catch {
        clearTokens();
        if (typeof window !== "undefined") window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth endpoints ────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }),

  logout: () => api.post("/auth/logout"),

  me: () => api.get<UserOut>("/auth/me"),
};

// ── Logs endpoints ────────────────────────────────────────────

export const logsApi = {
  ingest: (body: LogIngest) => api.post<LogOut>("/logs", body),

  list: (params?: {
    severity?: string;
    is_anomaly?: boolean;
    page?: number;
    page_size?: number;
  }) => api.get<LogListResponse>("/logs", { params }),

  stats: () => api.get<StatsResponse>("/logs/stats"),

  timeseries: (hours = 12) =>
    api.get<TimeseriesPoint[]>("/logs/timeseries", { params: { hours } }),

  resolve: (logId: string) => api.patch<LogOut>(`/logs/${logId}/resolve`),
};
