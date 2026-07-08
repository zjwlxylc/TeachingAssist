import { Alert, Snackbar } from "@mui/material";

interface AppSnackbarProps {
  open: boolean;
  message: string;
  severity?: "success" | "info" | "warning" | "error";
  onClose: () => void;
}

export function AppSnackbar({ open, message, severity = "info", onClose }: AppSnackbarProps) {
  return (
    <Snackbar open={open} autoHideDuration={4000} onClose={onClose}>
      <Alert
        severity={severity}
        variant="filled"
        onClose={onClose}
        sx={{
          width: "100%",
          // 颜色由 severity 决定（filled 变体已按级别着色），不再硬编码覆盖
          "& .MuiAlert-action": { color: "inherit" },
        }}
      >
        {message}
      </Alert>
    </Snackbar>
  );
}
