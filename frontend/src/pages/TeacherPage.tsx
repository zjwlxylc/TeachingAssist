import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  Typography
} from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import SettingsEthernetIcon from "@mui/icons-material/SettingsEthernet";

import { fetchHealth, fetchStartupStatus, HealthStatus, StartupStatus } from "../api/system";

export function TeacherPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [startup, setStartup] = useState<StartupStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchHealth(), fetchStartupStatus()])
      .then(([healthData, startupData]) => {
        setHealth(healthData);
        setStartup(startupData);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h1">教师工作台</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.75 }}>
          基础框架已接入后端健康检查、数据库初始化和启动检查。
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {!health && !error && <CircularProgress size={28} />}

      {health && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <CheckCircleIcon color="success" />
                  <Box>
                    <Typography variant="h2">服务状态</Typography>
                    <Typography color="text.secondary">{health.status}</Typography>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <StorageIcon color="primary" />
                  <Box>
                    <Typography variant="h2">数据库</Typography>
                    <Chip
                      size="small"
                      color={health.database_integrity === "ok" ? "success" : "warning"}
                      label={health.database_integrity}
                    />
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <SettingsEthernetIcon color="secondary" />
                  <Box>
                    <Typography variant="h2">运行环境</Typography>
                    <Typography color="text.secondary">{health.environment}</Typography>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {startup && (
        <Card>
          <CardContent>
            <Typography variant="h2">启动检查</Typography>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={1}>
              <Typography>数据库位置：{startup.database_path}</Typography>
              <Typography>U 盘路径识别：{startup.removable_root ?? "未配置"}</Typography>
              <Typography>本次迁移：{startup.migrations.length ? startup.migrations.join(", ") : "无"}</Typography>
              <Typography>初始化目录：{startup.directories.join("；")}</Typography>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}
