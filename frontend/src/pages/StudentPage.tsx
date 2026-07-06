import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import LoginIcon from "@mui/icons-material/Login";
import RefreshIcon from "@mui/icons-material/Refresh";

import { ClassroomSession } from "../api/academic";
import { fetchActiveSessions, fetchPublicSession, studentSignIn, StudentSignInResult } from "../api/classroom";
import { AppSnackbar } from "../components/AppSnackbar";

export function StudentPage() {
  const [activeSessions, setActiveSessions] = useState<ClassroomSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | "">("");
  const [sessionIdInput, setSessionIdInput] = useState("");
  const [currentSession, setCurrentSession] = useState<ClassroomSession | null>(null);
  const [studentId, setStudentId] = useState("");
  const [name, setName] = useState("");
  const [result, setResult] = useState<StudentSignInResult | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    loadActiveSessions();
  }, []);

  async function loadActiveSessions() {
    try {
      const sessions = await fetchActiveSessions();
      setActiveSessions(sessions);
      if (sessions.length && !selectedSessionId) {
        setSelectedSessionId(sessions[0].id);
        setSessionIdInput(String(sessions[0].id));
        setCurrentSession(sessions[0]);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadSession(sessionId: number) {
    try {
      const session = await fetchPublicSession(sessionId);
      setCurrentSession(session);
      setSelectedSessionId(session.id);
      setSessionIdInput(String(session.id));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleSignIn() {
    const sessionId = currentSession?.id || Number(sessionIdInput);
    if (!sessionId || !studentId || !name) {
      setError("请填写课堂 ID、学号和姓名");
      return;
    }
    try {
      const signInResult = await studentSignIn(sessionId, studentId, name);
      setResult(signInResult);
      setMessage(signInResult.duplicate ? "你已经完成过签到" : "签到成功");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h1">学生签到</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.75 }}>
          输入课堂 ID、学号和姓名完成本次课堂签到。
        </Typography>
      </Box>

      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}

      <Card sx={{ maxWidth: 640 }}>
        <CardContent>
          <Stack spacing={2}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <FormControl fullWidth>
                <InputLabel id="active-session-label">活动课堂</InputLabel>
                <Select
                  labelId="active-session-label"
                  label="活动课堂"
                  value={selectedSessionId}
                  onChange={(event) => loadSession(Number(event.target.value))}
                >
                  {activeSessions.map((session) => (
                    <MenuItem key={session.id} value={session.id}>
                      #{session.id} {session.course_name} / {session.class_name} / {session.title}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadActiveSessions}>
                刷新
              </Button>
            </Stack>

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <TextField
                label="课堂 ID"
                value={sessionIdInput}
                onChange={(event) => setSessionIdInput(event.target.value)}
                fullWidth
              />
              <Button variant="outlined" onClick={() => loadSession(Number(sessionIdInput))}>
                查询
              </Button>
            </Stack>

            {currentSession && (
              <Alert severity={currentSession.status === "active" ? "success" : "warning"}>
                {currentSession.course_name} / {currentSession.class_name} / {currentSession.title}：
                <Chip size="small" label={currentSession.status} sx={{ ml: 1 }} />
              </Alert>
            )}

            <TextField label="学号" value={studentId} onChange={(event) => setStudentId(event.target.value)} fullWidth />
            <TextField label="姓名" value={name} onChange={(event) => setName(event.target.value)} fullWidth />
            <Button variant="contained" startIcon={<LoginIcon />} onClick={handleSignIn}>
              提交签到
            </Button>

            {result && (
              <Alert severity={result.status === "late" ? "warning" : "success"}>
                {result.student_number} / {result.student_name} / {result.status}
                {result.sign_time ? ` / ${result.sign_time}` : ""}
              </Alert>
            )}
          </Stack>
        </CardContent>
      </Card>

      <AppSnackbar open={Boolean(message)} message={message} severity="success" onClose={() => setMessage("")} />
    </Stack>
  );
}
