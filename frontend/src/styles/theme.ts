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
      letterSpacing: 0,
      "@media (max-width:600px)": {
        fontSize: "1.375rem",
      },
    },
    h2: {
      fontSize: "1.25rem",
      fontWeight: 700,
      letterSpacing: 0,
      "@media (max-width:600px)": {
        fontSize: "1.125rem",
      },
    },
    button: {
      letterSpacing: 0,
      textTransform: "none",
    },
  },
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 960,
      lg: 1200,
      xl: 1536,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          "@media (max-width:600px)": {
            minHeight: 44,
            padding: "8px 16px",
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: "0 1px 3px rgba(15, 23, 42, 0.08)",
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          "@media (max-width:600px)": {
            "& .MuiInputBase-input": {
              fontSize: "16px",
            },
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          "@media (max-width:600px)": {
            "& .MuiSelect-select": {
              fontSize: "16px",
            },
          },
        },
      },
    },
    MuiTableContainer: {
      styleOverrides: {
        root: {
          "@media (max-width:600px)": {
            overflowX: "auto",
            "& table": {
              minWidth: 500,
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          "@media (max-width:600px)": {
            height: 28,
            "& .MuiChip-label": {
              fontSize: "0.75rem",
              padding: "0 8px",
            },
          },
        },
      },
    },
  },
});
