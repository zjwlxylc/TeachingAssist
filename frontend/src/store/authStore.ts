import { create } from "zustand";
import { setAuthToken } from "../api/http";

type Role = "teacher" | "student" | null;

interface AuthState {
  role: Role;
  isAuthenticated: boolean;
  teacherName: string;
  setRole: (role: Role) => void;
  setTeacherSession: (token: string, teacherName: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  role: localStorage.getItem("teacher_token") ? "teacher" : null,
  isAuthenticated: Boolean(localStorage.getItem("teacher_token")),
  teacherName: "",
  setRole: (role) => set({ role, isAuthenticated: role !== null }),
  setTeacherSession: (token, teacherName) => {
    setAuthToken(token);
    set({ role: "teacher", isAuthenticated: true, teacherName });
  },
  logout: () => {
    setAuthToken(null);
    set({ role: null, isAuthenticated: false, teacherName: "" });
  }
}));
