import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import SettingsEthernetIcon from "@mui/icons-material/SettingsEthernet";
import LoginIcon from "@mui/icons-material/Login";
import BackupIcon from "@mui/icons-material/Backup";
import LogoutIcon from "@mui/icons-material/Logout";

import { fetchAuthStatus, login, setupPassword, AuthStatus } from "../api/auth";
import {
  createBackup,
  fetchAccessInfo,
  fetchBackups,
  fetchHealth,
  fetchStartupStatus,
  updateAccessInfo,
  AccessInfo,
  BackupRecord,
  HealthStatus,
  StartupStatus
} from "../api/system";
import { AppSnackbar } from "../components/AppSnackbar";
import { useAuthStore } from "../store/authStore";

export function TeacherPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [startup, setStartup] = useState<StartupStatus | null>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [accessInfo, setAccessInfo] = useState<AccessInfo | null>(null);
  const [backups, setBackups] = useState<BackupRecord[]>([]);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [selectedIp, setSelectedIp] = useState("");
  const [selectedPort, setSelectedPort] = useState<number | "">("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const { isAuthenticated, setTeacherSession, logout: clearSession } = useAuthStore();

  useEffect(() => {
    Promise.all([fetchHealth(), fetchStartupStatus(), fetchAuthStatus()])
      .then(([healthData, startupData, authData]) => {
        setHealth(healthData);
        setStartup(startupData);
        setAuthStatus(authData);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    Promise.all([fetchAccessInfo(), fetchBackups()])
      .then(([accessData, backupData]) => {
        setAccessInfo(accessData);
        setSelectedIp(accessData.selected_ip);
        setSelectedPort(accessData.port);
        setBackups(backupData);
      })
      .catch((err: Error) => setError(err.message));
  }, [isAuthenticated]);

  async function submitSetup() {
    try {
      const result = await setupPassword(password, confirmPassword);
      setTeacherSession(result.token, result.teacher.name);
      setAuthStatus({ password_set: true, locked: false, locked_until: null, failed_login_count: 0 });
      setMessage("教师密码已设置");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function submitLogin() {
    try {
      const result = await login(password);
      setTeacherSession(result.token, result.teacher.name);
      setMessage("登录成功");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function refreshAccessInfo() {
    if (!selectedIp) {
      return;
    }
    const data = await updateAccessInfo(selectedIp, selectedPort === "" ? undefined : selectedPort);
    setAccessInfo(data);
    setSelectedIp(data.selected_ip);
    setSelectedPort(data.port);
    setMessage("访问地址已更新");
  }

  async function handleBackup() {
    try {
      await createBackup();
      setBackups(await fetchBackups());
      setMessage("数据库备份已完成");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function handleLogout() {
    clearSession();
    setAccessInfo(null);
    setBackups([]);
    setMessage("已退出登录");
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h1">教师工作台</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.75 }}>
          系统管理、教师认证、访问地址和数据库备份已接入。
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {!health && !authStatus && !error && <CircularProgress size={28} />}

      {authStatus && !isAuthenticated && (
        <Card sx={{ maxWidth: 520 }}>
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="h2">{authStatus.password_set ? "教师登录" : "首次设置教师密码"}</Typography>
              <TextField
                label="密码"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                fullWidth
              />
              {!authStatus.password_set && (
                <TextField
                  label="确认密码"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  fullWidth
                />
              )}
              {authStatus.locked && <Alert severity="warning">登录已锁定至 {authStatus.locked_until}</Alert>}
              <Button
                variant="contained"
                startIcon={<LoginIcon />}
                onClick={authStatus.password_set ? submitLogin : submitSetup}
              >
                {authStatus.password_set ? "登录教师端" : "设置并进入"}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}

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

      {startup && isAuthenticated && (
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

      {isAuthenticated && accessInfo && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={7}>
            <Card>
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction="row" alignItems="center" justifyContent="space-between">
                    <Typography variant="h2">访问地址</Typography>
                    <Button startIcon={<LogoutIcon />} onClick={handleLogout}>
                      退出
                    </Button>
                  </Stack>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <FormControl fullWidth>
                        <InputLabel id="network-ip-label">访问 IP</InputLabel>
                        <Select
                          labelId="network-ip-label"
                          label="访问 IP"
                          value={selectedIp}
                          onChange={(event) => setSelectedIp(event.target.value)}
                        >
                          {accessInfo.candidates.map((item) => (
                            <MenuItem key={item.ip} value={item.ip}>
                              {item.name}：{item.ip}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <TextField
                        label="端口"
                        type="number"
                        value={selectedPort}
                        onChange={(event) => setSelectedPort(Number(event.target.value))}
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Button variant="outlined" onClick={refreshAccessInfo} fullWidth sx={{ height: "100%" }}>
                        更新
                      </Button>
                    </Grid>
                  </Grid>
                  <Alert severity="success">课堂访问地址：{accessInfo.access_url}</Alert>
                  <Alert severity={accessInfo.firewall.rule_exists ? "success" : "warning"}>
                    {accessInfo.firewall.message}
                  </Alert>
                  <Typography color="text.secondary">管理员命令：{accessInfo.firewall.admin_command}</Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={5}>
            <Card>
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction="row" alignItems="center" justifyContent="space-between">
                    <Typography variant="h2">数据库备份</Typography>
                    <Button variant="contained" startIcon={<BackupIcon />} onClick={handleBackup}>
                      立即备份
                    </Button>
                  </Stack>
                  <Stack spacing={1}>
                    {backups.length === 0 && <Typography color="text.secondary">暂无备份记录</Typography>}
                    {backups.slice(0, 5).map((backup) => (
                      <Box key={backup.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                        <Typography>{backup.backup_type} / {backup.target} / {backup.status}</Typography>
                        <Typography color="text.secondary" sx={{ wordBreak: "break-all" }}>
                          {backup.file_path}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <AppSnackbar open={Boolean(message)} message={message} severity="success" onClose={() => setMessage("")} />
    </Stack>
  );
}
