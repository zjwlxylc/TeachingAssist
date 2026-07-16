import { Alert, Box, Button, Snackbar } from "@mui/material";
import { useEffect, useState } from "react";

export type ConnectionStatus = "connected" | "connecting" | "disconnected";

interface ConnectionIndicatorProps {
  status: ConnectionStatus;
  onRetry?: () => void;
}

/**
 * WebSocket 连接状态指示器
 * 显示在页面右下角，提示用户当前连接状态
 */
export function ConnectionIndicator({ status, onRetry }: ConnectionIndicatorProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    // 连接中或断开时显示提示
    if (status === "connecting" || status === "disconnected") {
      setOpen(true);
    } else {
      // 连接成功后，延迟1秒关闭提示
      const timer = setTimeout(() => setOpen(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [status]);

  const getStatusConfig = () => {
    switch (status) {
      case "connected":
        return {
          severity: "success" as const,
          icon: "🟢",
          message: "已连接",
          showRetry: false,
        };
      case "connecting":
        return {
          severity: "warning" as const,
          icon: "🟡",
          message: "重新连接中...",
          showRetry: false,
        };
      case "disconnected":
        return {
          severity: "error" as const,
          icon: "🔴",
          message: "连接已断开",
          showRetry: true,
        };
    }
  };

  const config = getStatusConfig();

  return (
    <Snackbar
      open={open}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      sx={{ bottom: { xs: 80, sm: 24 } }}
    >
      <Alert
        severity={config.severity}
        onClose={status === "disconnected" ? () => setOpen(false) : undefined}
        action={
          config.showRetry && onRetry ? (
            <Button color="inherit" size="small" onClick={onRetry}>
              重试
            </Button>
          ) : undefined
        }
        sx={{ alignItems: "center" }}
      >
        <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <span>{config.icon}</span>
          <span>{config.message}</span>
        </Box>
      </Alert>
    </Snackbar>
  );
}
