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
          bgcolor: "#ff7a00",
          color: "#ffffff",
          "& .MuiAlert-icon": { color: "#ffffff" },
          "& .MuiAlert-action": { color: "#ffffff" },
        }}
      >
        {message}
      </Alert>
    </Snackbar>
  );
}
