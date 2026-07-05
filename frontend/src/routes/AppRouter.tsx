import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppLayout } from "../layouts/AppLayout";
import { HomePage } from "../pages/HomePage";
import { StudentPage } from "../pages/StudentPage";
import { TeacherPage } from "../pages/TeacherPage";

export function AppRouter() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/teacher" element={<TeacherPage />} />
          <Route path="/student" element={<StudentPage />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}
