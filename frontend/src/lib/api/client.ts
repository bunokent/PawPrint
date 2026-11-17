import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from "axios";

/** Normalized API error surfaced to the UI. */
export class ApiError extends Error {
  code: string;
  status: number;
  fields?: Record<string, unknown>;
  detectedLabels?: string[];
  sessionExpired: boolean;

  constructor(err: AxiosError) {
    const data = err.response?.data as Record<string, { code?: string; message?: string; fields?: Record<string, unknown>; detected_labels?: string[]; session_expired?: boolean }> | undefined;
    const error = data?.error;
    super(error?.message ?? err.message);
    this.name = "ApiError";
    this.code = error?.code ?? "network_error";
    this.status = err.response?.status ?? 0;
    this.fields = error?.fields;
    this.detectedLabels = error?.detected_labels;
    this.sessionExpired = error?.session_expired ?? (err.response?.status === 401);
  }
}

/** Single centralized axios instance — every API call goes through here. */
export const api: AxiosInstance = axios.create({
  baseURL: "/api",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const apiError = new ApiError(error);
    if (apiError.sessionExpired) {
      // Let the auth store react; components read this flag.
      window.dispatchEvent(new CustomEvent("pawprint:session-expired"));
    }
    return Promise.reject(apiError);
  },
);

/** Helper for multipart uploads (keeps JSON default elsewhere; axios adds the boundary). */
export function multipartConfig(): AxiosRequestConfig {
  return { headers: { "Content-Type": "multipart/form-data" } };
}
