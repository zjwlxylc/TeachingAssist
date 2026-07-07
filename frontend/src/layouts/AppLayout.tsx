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

const GITHUB_REPO_URL = "https://github.com/zjwlxylc/TeachingAssist";

const navItems = [
  { label: "教师", path: "/teacher", icon: <DashboardIcon fontSize="small" /> },
  { label: "学生", path: "/student", icon: <PersonIcon fontSize="small" /> },
];

export function AppLayout({ children }: PropsWithChildren) {
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

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
              flexGrow: 1,
              fontSize: { xs: "0.95rem", sm: "1.25rem" },
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {isMobile ? "教学辅助" : "大学教学过程辅助软件"}
          </Typography>
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
          title="前往 GitHub 为我们点亮 ⭐ Star，您的支持是开源持续前进的动力。"
          placement="left"
          arrow
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
