import { create } from "zustand";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type UserDTO = components["schemas"]["User"];

interface AuthState {
  user: UserDTO | null;
  checked: boolean;
  setUser: (user: UserDTO | null) => void;
  fetchMe: () => Promise<UserDTO | null>;
  logout: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  checked: false,
  setUser: (user) => set({ user, checked: true }),
  fetchMe: async () => {
    try {
      const { data } = await api.get<UserDTO>("/auth/me");
      set({ user: data, checked: true });
      return data;
    } catch {
      set({ user: null, checked: true });
      return null;
    }
  },
  logout: async () => {
    await api.post("/auth/logout");
    set({ user: null });
  },
}));

window.addEventListener("pawprint:session-expired", () => {
  useAuth.setState({ user: null });
});
