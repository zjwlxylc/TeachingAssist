import { create } from "zustand";

type Role = "teacher" | "student" | null;

interface AuthState {
  role: Role;
  isAuthenticated: boolean;
  setRole: (role: Role) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  role: null,
  isAuthenticated: false,
  setRole: (role) => set({ role, isAuthenticated: role !== null }),
  logout: () => set({ role: null, isAuthenticated: false })
}));
