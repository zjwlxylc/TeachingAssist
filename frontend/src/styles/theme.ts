import { createTheme } from "@mui/material";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#2563eb"
    },
    secondary: {
      main: "#0f766e"
    },
    background: {
      default: "#f6f7f9",
      paper: "#ffffff"
    },
    text: {
      primary: "#1f2937",
      secondary: "#5b6472"
    }
  },
  shape: {
    borderRadius: 8
  },
  typography: {
    fontFamily:
      '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif',
    h1: {
      fontSize: "1.75rem",
      fontWeight: 700,
      letterSpacing: 0
    },
    h2: {
      fontSize: "1.25rem",
      fontWeight: 700,
      letterSpacing: 0
    },
    button: {
      letterSpacing: 0,
      textTransform: "none"
    }
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6
        }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: "0 1px 3px rgba(15, 23, 42, 0.08)"
        }
      }
    }
  }
});
