import { useEffect, useRef, useState } from "react";
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
import {
  Announcement,
  AnnouncementMessage,
  classroomSocketUrl,
  fetchAnnouncements
} from "../api/announcements";
import { fetchActiveSessions, fetchPublicSession, studentSignIn, StudentSignInResult } from "../api/classroom";
import { TeachingAssistSocket } from "../api/websocket";
import { AppSnackbar } from "../components/AppSnackbar";

export function StudentPage() {
  const [activeSessions, setActiveSessions] = useState<ClassroomSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | "">("");
  const [sessionIdInput, setSessionIdInput] = useState("");
  const [currentSession, setCurrentSession] = useState<ClassroomSession | null>(null);
  const [studentId, setStudentId] = useState("");
  const [name, setName] = useState("");
  const [result, setResult] = useState<StudentSignInResult | null>(null);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const socketRef = useRef<TeachingAssistSocket | null>(null);
  const lastAnnouncementIdRef = useRef(0);

  useEffect(() => {
    loadActiveSessions();
  }, []);

  useEffect(() => {
    socketRef.current?.close();
    socketRef.current = null;
    setAnnouncements([]);
    lastAnnouncementIdRef.current = 0;
    if (!currentSession?.id) {
      return undefined;
    }

    let disposed = false;
    const sessionId = currentSession.id;
    const mergeAnnouncements = (items: Announcement[]) => {
      items.forEach((item) => {
        lastAnnouncementIdRef.current = Math.max(lastAnnouncementIdRef.current, item.id);
      });
      setAnnouncements((current) => {
        const next = new Map<number, Announcement>();
        [...items, ...current].forEach((item) => next.set(item.id, item));
        return Array.from(next.values()).sort((a, b) => b.id - a.id);
      });
    };
    const loadMessages = async (lastId?: number) => {
      try {
        const items = await fetchAnnouncements(sessionId, lastId);
        if (!disposed) {
          mergeAnnouncements(items);
        }
      } catch (err) {
        if (!disposed) {
          setError((err as Error).message);
        }
      }
    };

    loadMessages();
    const socket = new TeachingAssistSocket(
      classroomSocketUrl(sessionId),
      (event) => {
        const payload = JSON.parse(event.data) as AnnouncementMessage;
        if (payload.type === "announcement.created") {
          mergeAnnouncements([payload.announcement]);
          setMessage("收到新的课堂公告");
        }
      },
      3000,
      () => {
        const lastId = lastAnnouncementIdRef.current;
        if (lastId) {
          loadMessages(lastId);
        }
      }
    );
    socketRef.current = socket;
    socket.connect();
    return () => {
      disposed = true;
      socket.close();
    };
  }, [currentSession?.id]);

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

      <Card sx={{ maxWidth: 760 }}>
        <CardContent>
          <Stack spacing={1.5}>
            <Typography variant="h2">课堂公告</Typography>
            {announcements.map((item) => (
              <Box key={item.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                <Typography>{item.content}</Typography>
                <Typography color="text.secondary" variant="body2">
                  {item.sender_name} / {item.created_at}
                </Typography>
              </Box>
            ))}
            {announcements.length === 0 && (
              <Typography color="text.secondary">进入课堂后可查看教师发布的公告。</Typography>
            )}
          </Stack>
        </CardContent>
      </Card>

      <AppSnackbar open={Boolean(message)} message={message} severity="success" onClose={() => setMessage("")} />
    </Stack>
  );
}
