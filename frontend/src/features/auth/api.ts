import { api, multipartConfig } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type User = components["schemas"]["User"];
type RegisterInput = { email: string; password: string; display_name?: string };
type LoginInput = { email: string; password: string };
type ProfileInput = { display_name?: string; phone?: string };

export const authApi = {
  register: (input: RegisterInput) => api.post<User>("/auth/register", input).then((r) => r.data),
  login: (input: LoginInput) => api.post<User>("/auth/login", input).then((r) => r.data),
  logout: () => api.post("/auth/logout").then((r) => r.data),
  me: () => api.get<User>("/auth/me").then((r) => r.data),
  updateProfile: (input: ProfileInput) => api.patch<User>("/auth/profile", input).then((r) => r.data),
  uploadAvatar: (file: File, onProgress?: (percentage: number) => void) => {
    const form = new FormData();
    form.append("avatar", file);
    return api
      .post<User>("/auth/avatar", form, {
        ...multipartConfig(),
        onUploadProgress: (event) => {
          const total = event.total ?? file.size;
          if (total > 0) onProgress?.(Math.min(100, Math.round((event.loaded / total) * 100)));
        },
      })
      .then((r) => r.data);
  },
  googleUrl: (redirectUri: string) =>
    api.post<{ url: string }>("/auth/google/url", { redirect_uri: redirectUri }).then((r) => r.data),
  googleCallback: (code: string, redirectUri: string) =>
    api
      .post<{ user: User; created: boolean }>("/auth/google/callback", { code, redirect_uri: redirectUri })
      .then((r) => r.data),
};

export const REDIRECT_URI = `${window.location.origin}/auth/login`;
