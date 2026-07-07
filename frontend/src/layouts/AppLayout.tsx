import { PropsWithChildren } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import {
  AppBar,
  Box,
  Button,
  Card,
  Container,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import SchoolIcon from "@mui/icons-material/School";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PersonIcon from "@mui/icons-material/Person";
import GitHubIcon from "@mui/icons-material/GitHub";
import StarIcon from "@mui/icons-material/Star";

import { useAuthStore } from "../store/authStore";
import { useStatusStore } from "../store/statusStore";

const GITHUB_REPO_URL = "https://github.com/zjwlxylc/TeachingAssist";

const navItems = [
  { label: "教师", path: "/teacher", icon: <DashboardIcon fontSize="small" /> },
  { label: "学生", path: "/student", icon: <PersonIcon fontSize="small" /> },
];

export function AppLayout({ children }: PropsWithChildren) {
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  const { isAuthenticated } = useAuthStore();
  const {
    teacherHealthStatus,
    teacherDbIntegrity,
    teacherAccessUrl,
    studentId,
    studentName,
    studentLoggedIn,
  } = useStatusStore();

  const isTeacherRoute = location.pathname.startsWith("/teacher");
  const isStudentRoute = location.pathname.startsWith("/student");

  const statusItems: { label: string; value: string; color: string }[] = isTeacherRoute
    ? [
        { label: "教师工作台", value: teacherHealthStatus ? "运行中" : "检测中", color: teacherHealthStatus ? "success.main" : "text.disabled" },
        { label: "系统管理", value: teacherHealthStatus ? "正常" : "检测中", color: teacherHealthStatus ? "success.main" : "text.disabled" },
        { label: "教师认证", value: isAuthenticated ? "已认证" : "未认证", color: isAuthenticated ? "success.main" : "warning.main" },
        { label: "学生访问地址", value: teacherAccessUrl || "待配置", color: teacherAccessUrl ? "success.main" : "warning.main" },
        { label: "数据库备份", value: teacherDbIntegrity === "ok" ? "正常" : (teacherDbIntegrity || "检测中"), color: teacherDbIntegrity === "ok" ? "success.main" : (teacherDbIntegrity ? "warning.main" : "text.disabled") },
      ]
    : isStudentRoute
    ? [
        { label: "学号", value: studentId || "未填写", color: studentId ? "success.main" : "text.disabled" },
        { label: "姓名", value: studentName || "未填写", color: studentName ? "success.main" : "text.disabled" },
        { label: "登录状态", value: studentLoggedIn ? "已登录" : "未登录", color: studentLoggedIn ? "success.main" : "warning.main" },
      ]
    : [];

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="static" color="inherit" elevation={0}>
        <Toolbar
          sx={{
            borderBottom: "1px solid",
            borderColor: "divider",
            gap: { xs: 0.5, sm: 2 },
            px: { xs: 1, sm: 2 },
          }}
        >
          <SchoolIcon color="primary" sx={{ fontSize: { xs: 20, sm: 24 } }} />
          <Typography
            variant="h2"
            component="div"
            sx={{
              fontSize: { xs: "0.95rem", sm: "1.25rem" },
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            AI课堂辅助
          </Typography>
          {!isMobile && statusItems.length > 0 && (
            <Stack
              direction="row"
              spacing={{ xs: 0.5, sm: 1.5 }}
              sx={{ ml: { xs: 0.5, sm: 2 }, overflow: "hidden" }}
            >
              {statusItems.map((item) => (
                <Box
                  key={item.label}
                  sx={{ display: "flex", alignItems: "center", gap: 0.4, whiteSpace: "nowrap" }}
                >
                  <Box
                    component="span"
                    sx={{ width: 7, height: 7, borderRadius: "50%", bgcolor: item.color, flexShrink: 0 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.4 }}>
                    {item.label}
                  </Typography>
                  <Typography variant="caption" fontWeight={600} sx={{ lineHeight: 1.4 }}>
                    {item.value}
                  </Typography>
                </Box>
              ))}
            </Stack>
          )}
          <Box sx={{ flexGrow: 1 }} />
          <Stack direction="row" spacing={{ xs: 0.25, sm: 1 }}>
            {navItems.map((item) => (
              <Button
                key={item.path}
                component={RouterLink}
                to={item.path}
                startIcon={isMobile ? undefined : item.icon}
                variant={location.pathname.startsWith(item.path) ? "contained" : "text"}
                size={isMobile ? "small" : "medium"}
                sx={{ minWidth: { xs: 52, sm: 100 } }}
              >
                {isMobile ? item.label : `${item.label}端`}
              </Button>
            ))}
          </Stack>
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ py: { xs: 1.5, sm: 3 }, px: { xs: 1, sm: 3 } }}>
        {children}
      </Container>

      {/* 开源仓库固定入口：固定在页面右侧、垂直居中，滚动时常驻可见 */}
      <Box
        component="aside"
        aria-label="开源仓库入口"
        sx={{
          position: "fixed",
          right: { xs: 8, sm: 16 },
          top: { xs: 56, sm: 64 },
          zIndex: (t) => t.zIndex.appBar + 1,
        }}
      >
        <Tooltip
          title={
            <>
              开源项目开发者：李超（浙江万里学院）。
              <br />
              前往 GitHub 为我们点亮 ⭐ Star，您的支持是开源持续前进的动力。
            </>
          }
          placement="left"
          arrow
          componentsProps={{
            tooltip: {
              sx: {
                fontSize: "0.9rem",
                maxWidth: 360,
                whiteSpace: "normal",
                lineHeight: 1.5,
              },
            },
          }}
        >
          <Card
            component="a"
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            elevation={2}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              px: { xs: 0.75, sm: 1.25 },
              py: { xs: 0.4, sm: 0.6 },
              borderRadius: 999,
              border: "1px solid",
              borderColor: "divider",
              bgcolor: "background.paper",
              textDecoration: "none",
              cursor: "pointer",
              transition: "box-shadow 0.2s ease, background-color 0.2s ease",
              "&:hover": {
                boxShadow: 4,
                bgcolor: "action.hover",
              },
            }}
          >
            <GitHubIcon sx={{ fontSize: { xs: 18, sm: 20 }, color: "primary.main" }} />
            <Typography
              component="span"
              sx={{
                fontWeight: 600,
                color: "primary.main",
                fontSize: { xs: "0.7rem", sm: "0.8rem" },
                whiteSpace: "nowrap",
              }}
            >
              开源仓库
            </Typography>
            <StarIcon sx={{ fontSize: { xs: 14, sm: 16 }, color: "warning.main" }} />
          </Card>
        </Tooltip>
      </Box>
    </Box>
  );
}
