import { create } from "zustand";

interface StatusState {
  // 教师端状态（由 TeacherPage 同步写入）
  teacherHealthStatus: string | null;
  teacherDbIntegrity: string | null;
  teacherAccessUrl: string | null;
  // 学生端状态（由 StudentPage 同步写入）
  studentId: string;
  studentName: string;
  studentLoggedIn: boolean;
  // setters
  setTeacherStatus: (healthStatus: string | null, dbIntegrity: string | null) => void;
  setTeacherAccessUrl: (url: string | null) => void;
  setStudentInfo: (id: string, name: string) => void;
  setStudentLoggedIn: (loggedIn: boolean) => void;
}

export const useStatusStore = create<StatusState>((set) => ({
  teacherHealthStatus: null,
  teacherDbIntegrity: null,
  teacherAccessUrl: null,
  studentId: "",
  studentName: "",
  studentLoggedIn: false,
  setTeacherStatus: (healthStatus, dbIntegrity) =>
    set({ teacherHealthStatus: healthStatus, teacherDbIntegrity: dbIntegrity }),
  setTeacherAccessUrl: (url) => set({ teacherAccessUrl: url }),
  setStudentInfo: (id, name) => set({ studentId: id, studentName: name }),
  setStudentLoggedIn: (loggedIn) => set({ studentLoggedIn: loggedIn }),
}));
