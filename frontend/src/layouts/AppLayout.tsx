import { PropsWithChildren } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import {
  AppBar,
  Box,
  Button,
  Container,
  Stack,
  Toolbar,
  Typography
} from "@mui/material";
import SchoolIcon from "@mui/icons-material/School";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PersonIcon from "@mui/icons-material/Person";

const navItems = [
  { label: "教师端", path: "/teacher", icon: <DashboardIcon fontSize="small" /> },
  { label: "学生端", path: "/student", icon: <PersonIcon fontSize="small" /> }
];

export function AppLayout({ children }: PropsWithChildren) {
  const location = useLocation();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="static" color="inherit" elevation={0}>
        <Toolbar sx={{ borderBottom: "1px solid", borderColor: "divider", gap: 2 }}>
          <SchoolIcon color="primary" />
          <Typography variant="h2" component="div" sx={{ flexGrow: 1 }}>
            大学教学过程辅助软件
          </Typography>
          <Stack direction="row" spacing={1}>
            {navItems.map((item) => (
              <Button
                key={item.path}
                component={RouterLink}
                to={item.path}
                startIcon={item.icon}
                variant={location.pathname.startsWith(item.path) ? "contained" : "text"}
              >
                {item.label}
              </Button>
            ))}
          </Stack>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        {children}
      </Container>
    </Box>
  );
}
