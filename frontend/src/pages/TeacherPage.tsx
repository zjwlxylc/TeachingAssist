import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography
} from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import SettingsEthernetIcon from "@mui/icons-material/SettingsEthernet";
import LoginIcon from "@mui/icons-material/Login";
import BackupIcon from "@mui/icons-material/Backup";
import LogoutIcon from "@mui/icons-material/Logout";
import AddIcon from "@mui/icons-material/Add";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import LinkIcon from "@mui/icons-material/Link";
import EventIcon from "@mui/icons-material/Event";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopCircleIcon from "@mui/icons-material/StopCircle";
import FactCheckIcon from "@mui/icons-material/FactCheck";

import {
  ClassGroup,
  ClassroomSession,
  Course,
  ImportJob,
  ImportPreview,
  Student,
  confirmStudentImport,
  createClass,
  createCourse,
  createSession,
  fetchClasses,
  fetchCourses,
  fetchSessions,
  fetchStudents,
  linkCourseClass,
  previewStudentImport,
  uploadStudentExcel
} from "../api/academic";
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
import {
  SignInSummary,
  endClassroomSession,
  fetchSignInSummary,
  startClassroomSession
} from "../api/classroom";
import { AppSnackbar } from "../components/AppSnackbar";
import { useAuthStore } from "../store/authStore";

export function TeacherPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [startup, setStartup] = useState<StartupStatus | null>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [accessInfo, setAccessInfo] = useState<AccessInfo | null>(null);
  const [backups, setBackups] = useState<BackupRecord[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [classes, setClasses] = useState<ClassGroup[]>([]);
  const [sessions, setSessions] = useState<ClassroomSession[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [courseName, setCourseName] = useState("");
  const [teacherName, setTeacherName] = useState("");
  const [className, setClassName] = useState("");
  const [selectedCourseId, setSelectedCourseId] = useState<number | "">("");
  const [selectedClassId, setSelectedClassId] = useState<number | "">("");
  const [sessionTitle, setSessionTitle] = useState("");
  const [sessionNo, setSessionNo] = useState<number | "">("");
  const [sessionStart, setSessionStart] = useState("");
  const [sessionEnd, setSessionEnd] = useState("");
  const [isMakeup, setIsMakeup] = useState(false);
  const [importJob, setImportJob] = useState<ImportJob | null>(null);
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({});
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [signInSummary, setSignInSummary] = useState<SignInSummary | null>(null);
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
    Promise.all([fetchAccessInfo(), fetchBackups(), fetchCourses(), fetchClasses(), fetchSessions(), fetchStudents()])
      .then(([accessData, backupData, courseData, classData, sessionData, studentData]) => {
        setAccessInfo(accessData);
        setSelectedIp(accessData.selected_ip);
        setSelectedPort(accessData.port);
        setBackups(backupData);
        setCourses(courseData);
        setClasses(classData);
        setSessions(sessionData);
        setStudents(studentData);
      })
      .catch((err: Error) => setError(err.message));
  }, [isAuthenticated]);

  async function reloadAcademic() {
    const [courseData, classData, sessionData, studentData] = await Promise.all([
      fetchCourses(),
      fetchClasses(),
      fetchSessions(),
      fetchStudents()
    ]);
    setCourses(courseData);
    setClasses(classData);
    setSessions(sessionData);
    setStudents(studentData);
  }

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

  async function handleCreateCourse() {
    try {
      const course = await createCourse(courseName, teacherName);
      setCourseName("");
      setTeacherName("");
      setSelectedCourseId(course.id);
      await reloadAcademic();
      setMessage("课程已创建");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleCreateClass() {
    try {
      const klass = await createClass(className);
      setClassName("");
      setSelectedClassId(klass.id);
      await reloadAcademic();
      setMessage("班级已创建");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLinkCourseClass() {
    if (!selectedCourseId || !selectedClassId) {
      setError("请先选择课程和班级");
      return;
    }
    try {
      await linkCourseClass(Number(selectedCourseId), Number(selectedClassId));
      await reloadAcademic();
      setMessage("课程班级已关联");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleCreateSession() {
    if (!selectedCourseId || !selectedClassId || !sessionTitle || !sessionNo) {
      setError("请填写课程、班级、课堂标题和课次");
      return;
    }
    try {
      await createSession({
        course_id: Number(selectedCourseId),
        class_id: Number(selectedClassId),
        title: sessionTitle,
        session_no: Number(sessionNo),
        start_time: sessionStart || undefined,
        end_time: sessionEnd || undefined,
        is_makeup: isMakeup
      });
      setSessionTitle("");
      setSessionNo("");
      setSessionStart("");
      setSessionEnd("");
      setIsMakeup(false);
      await reloadAcademic();
      setMessage("课堂已创建");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleExcelUpload(file: File | null) {
    if (!file) {
      return;
    }
    try {
      const job = await uploadStudentExcel(file);
      const suggested: Record<string, string> = {};
      Object.entries(job.standard_fields).forEach(([field, label]) => {
        const match = job.headers.find((header) => header.includes(label) || label.includes(header));
        if (match) {
          suggested[match] = field;
        }
      });
      setImportJob(job);
      setFieldMapping(suggested);
      setImportPreview(null);
      setMessage("Excel 已解析");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handlePreviewImport() {
    if (!importJob) {
      return;
    }
    try {
      setImportPreview(await previewStudentImport(importJob.job_id, fieldMapping));
      setMessage("导入预览已生成");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleConfirmImport() {
    if (!importJob || !selectedCourseId) {
      setError("请先选择课程并生成导入预览");
      return;
    }
    try {
      const result = await confirmStudentImport(importJob.job_id, Number(selectedCourseId), fieldMapping, true);
      await reloadAcademic();
      setMessage(`导入 ${result.imported} 人，跳过 ${result.skipped} 人`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleStartSession(sessionId: number) {
    try {
      await startClassroomSession(sessionId);
      await reloadAcademic();
      setSignInSummary(await fetchSignInSummary(sessionId));
      setMessage("课堂已开始");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleEndSession(sessionId: number) {
    try {
      const summary = await endClassroomSession(sessionId);
      await reloadAcademic();
      setSignInSummary(summary);
      setMessage("课堂已结束，未签到学生已记为缺勤");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadSignIns(sessionId: number) {
    try {
      setSignInSummary(await fetchSignInSummary(sessionId));
      setMessage("签到统计已刷新");
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

      {isAuthenticated && (
        <Card>
          <CardContent>
            <Stack spacing={2.5}>
              <Box>
                <Typography variant="h2">课前准备</Typography>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  创建课程、班级、课堂，并导入学生名单。
                </Typography>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                    <Stack spacing={1.5}>
                      <Typography fontWeight={700}>课程</Typography>
                      <TextField label="课程名称" value={courseName} onChange={(event) => setCourseName(event.target.value)} />
                      <TextField label="任课教师" value={teacherName} onChange={(event) => setTeacherName(event.target.value)} />
                      <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreateCourse}>
                        创建课程
                      </Button>
                      <FormControl fullWidth>
                        <InputLabel id="course-select-label">当前课程</InputLabel>
                        <Select
                          labelId="course-select-label"
                          label="当前课程"
                          value={selectedCourseId}
                          onChange={(event) => setSelectedCourseId(Number(event.target.value))}
                        >
                          {courses.map((course) => (
                            <MenuItem key={course.id} value={course.id}>
                              {course.name}（{course.student_count ?? 0} 人）
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Stack>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                    <Stack spacing={1.5}>
                      <Typography fontWeight={700}>班级</Typography>
                      <TextField label="班级名称" value={className} onChange={(event) => setClassName(event.target.value)} />
                      <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreateClass}>
                        创建班级
                      </Button>
                      <FormControl fullWidth>
                        <InputLabel id="class-select-label">当前班级</InputLabel>
                        <Select
                          labelId="class-select-label"
                          label="当前班级"
                          value={selectedClassId}
                          onChange={(event) => setSelectedClassId(Number(event.target.value))}
                        >
                          {classes.map((klass) => (
                            <MenuItem key={klass.id} value={klass.id}>
                              {klass.name}（{klass.student_count ?? 0} 人）
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <Button variant="outlined" startIcon={<LinkIcon />} onClick={handleLinkCourseClass}>
                        关联课程班级
                      </Button>
                    </Stack>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                    <Stack spacing={1.5}>
                      <Typography fontWeight={700}>课堂</Typography>
                      <TextField label="课堂标题" value={sessionTitle} onChange={(event) => setSessionTitle(event.target.value)} />
                      <TextField
                        label="课次"
                        type="number"
                        value={sessionNo}
                        onChange={(event) => setSessionNo(event.target.value === "" ? "" : Number(event.target.value))}
                      />
                      <TextField
                        label="开始时间"
                        type="datetime-local"
                        value={sessionStart}
                        onChange={(event) => setSessionStart(event.target.value)}
                        InputLabelProps={{ shrink: true }}
                      />
                      <TextField
                        label="结束时间"
                        type="datetime-local"
                        value={sessionEnd}
                        onChange={(event) => setSessionEnd(event.target.value)}
                        InputLabelProps={{ shrink: true }}
                      />
                      <FormControlLabel
                        control={<Checkbox checked={isMakeup} onChange={(event) => setIsMakeup(event.target.checked)} />}
                        label="补课课堂"
                      />
                      <Button variant="contained" startIcon={<EventIcon />} onClick={handleCreateSession}>
                        创建课堂
                      </Button>
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>

              <Divider />

              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <Stack spacing={1.5}>
                    <Typography fontWeight={700}>Excel 学生导入</Typography>
                    <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
                      上传 .xlsx
                      <input
                        type="file"
                        hidden
                        accept=".xlsx,.xls"
                        onChange={(event) => handleExcelUpload(event.target.files?.[0] ?? null)}
                      />
                    </Button>
                    {importJob && (
                      <Alert severity="info">
                        {importJob.file_name}，共 {importJob.total_rows} 行数据
                      </Alert>
                    )}
                    {importJob && (
                      <Stack spacing={1}>
                        {importJob.headers.map((header) => (
                          <FormControl key={header} fullWidth size="small">
                            <InputLabel id={`mapping-${header}`}>{header}</InputLabel>
                            <Select
                              labelId={`mapping-${header}`}
                              label={header}
                              value={fieldMapping[header] ?? ""}
                              onChange={(event) =>
                                setFieldMapping((current) => ({ ...current, [header]: event.target.value }))
                              }
                            >
                              <MenuItem value="">不导入</MenuItem>
                              {Object.entries(importJob.standard_fields).map(([field, label]) => (
                                <MenuItem key={field} value={field}>
                                  {label}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        ))}
                        <Button variant="contained" onClick={handlePreviewImport}>
                          生成预览
                        </Button>
                      </Stack>
                    )}
                  </Stack>
                </Grid>

                <Grid item xs={12} md={7}>
                  <Stack spacing={1.5}>
                    <Typography fontWeight={700}>导入预览</Typography>
                    {importPreview ? (
                      <>
                        <Alert severity={importPreview.error_count ? "warning" : "success"}>
                          有效 {importPreview.valid_rows}/{importPreview.total_rows} 行，错误 {importPreview.error_count}，警告{" "}
                          {importPreview.warning_count}
                        </Alert>
                        <Paper variant="outlined" sx={{ maxHeight: 280, overflow: "auto" }}>
                          <Table size="small" stickyHeader>
                            <TableHead>
                              <TableRow>
                                <TableCell>行号</TableCell>
                                <TableCell>学号</TableCell>
                                <TableCell>姓名</TableCell>
                                <TableCell>班级</TableCell>
                                <TableCell>状态</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {importPreview.rows.map((row) => (
                                <TableRow key={row.row_number}>
                                  <TableCell>{row.row_number}</TableCell>
                                  <TableCell>{row.data.student_id}</TableCell>
                                  <TableCell>{row.data.name}</TableCell>
                                  <TableCell>{row.data.class_name}</TableCell>
                                  <TableCell>
                                    {row.errors.length ? row.errors.join("；") : row.warnings.join("；") || "可导入"}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </Paper>
                        <Button variant="contained" onClick={handleConfirmImport} disabled={Boolean(importPreview.error_count)}>
                          确认导入有效数据
                        </Button>
                      </>
                    ) : (
                      <Typography color="text.secondary">上传文件并完成字段映射后生成预览。</Typography>
                    )}
                  </Stack>
                </Grid>
              </Grid>

              <Divider />

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography fontWeight={700} sx={{ mb: 1 }}>
                    已创建课堂
                  </Typography>
                  <Stack spacing={1}>
                    {sessions.slice(0, 5).map((session) => (
                      <Box key={session.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                        <Typography>
                          第 {session.session_no} 次：{session.title}
                        </Typography>
                        <Typography color="text.secondary">
                          {session.course_name} / {session.class_name} / {session.status}
                        </Typography>
                      </Box>
                    ))}
                    {sessions.length === 0 && <Typography color="text.secondary">暂无课堂</Typography>}
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography fontWeight={700} sx={{ mb: 1 }}>
                    学生名单
                  </Typography>
                  <Stack spacing={1}>
                    {students.slice(0, 5).map((student) => (
                      <Box key={student.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                        <Typography>
                          {student.student_id} / {student.name}
                        </Typography>
                        <Typography color="text.secondary">{student.class_name}</Typography>
                      </Box>
                    ))}
                    {students.length === 0 && <Typography color="text.secondary">暂无学生</Typography>}
                  </Stack>
                </Grid>
              </Grid>
            </Stack>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && (
        <Card>
          <CardContent>
            <Stack spacing={2.5}>
              <Box>
                <Typography variant="h2">课堂运行与签到</Typography>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  管理课堂开始、结束和学生签到统计。课堂 ID 可告知学生用于签到。
                </Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Stack spacing={1.5}>
                    {sessions.map((session) => (
                      <Paper key={session.id} variant="outlined" sx={{ p: 2 }}>
                        <Stack spacing={1}>
                          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
                            <Box>
                              <Typography fontWeight={700}>
                                #{session.id} 第 {session.session_no} 次：{session.title}
                              </Typography>
                              <Typography color="text.secondary">
                                {session.course_name} / {session.class_name} / 名单 {session.roster_count ?? 0} 人
                              </Typography>
                            </Box>
                            <Chip
                              size="small"
                              color={
                                session.status === "active"
                                  ? "success"
                                  : session.status === "ended"
                                    ? "default"
                                    : "warning"
                              }
                              label={session.status}
                              sx={{ alignSelf: { xs: "flex-start", sm: "center" } }}
                            />
                          </Stack>
                          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            <Button
                              size="small"
                              variant="contained"
                              startIcon={<PlayArrowIcon />}
                              disabled={session.status !== "pending"}
                              onClick={() => handleStartSession(session.id)}
                            >
                              开始
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              startIcon={<StopCircleIcon />}
                              disabled={session.status === "ended"}
                              onClick={() => handleEndSession(session.id)}
                            >
                              结束
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<FactCheckIcon />}
                              onClick={() => handleLoadSignIns(session.id)}
                            >
                              签到统计
                            </Button>
                          </Stack>
                        </Stack>
                      </Paper>
                    ))}
                    {sessions.length === 0 && <Typography color="text.secondary">暂无课堂，请先完成课前准备。</Typography>}
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 2, minHeight: 240 }}>
                    {signInSummary ? (
                      <Stack spacing={2}>
                        <Box>
                          <Typography fontWeight={700}>{signInSummary.session.title}</Typography>
                          <Typography color="text.secondary">
                            应到 {signInSummary.stats.total}，已签 {signInSummary.stats.signed}，迟到{" "}
                            {signInSummary.stats.late}，缺勤 {signInSummary.stats.absent}，未处理{" "}
                            {signInSummary.stats.unsigned}
                          </Typography>
                        </Box>
                        <Paper variant="outlined" sx={{ maxHeight: 320, overflow: "auto" }}>
                          <Table size="small" stickyHeader>
                            <TableHead>
                              <TableRow>
                                <TableCell>学号</TableCell>
                                <TableCell>姓名</TableCell>
                                <TableCell>状态</TableCell>
                                <TableCell>时间</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {signInSummary.records.map((record) => (
                                <TableRow key={record.student_pk}>
                                  <TableCell>{record.student_number}</TableCell>
                                  <TableCell>{record.student_name}</TableCell>
                                  <TableCell>{record.status ?? "未签到"}</TableCell>
                                  <TableCell>{record.sign_time ?? "-"}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </Paper>
                      </Stack>
                    ) : (
                      <Typography color="text.secondary">选择一堂课查看实时签到统计。</Typography>
                    )}
                  </Paper>
                </Grid>
              </Grid>
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
