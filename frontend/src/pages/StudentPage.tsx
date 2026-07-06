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
  Paper,
  Select,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import LoginIcon from "@mui/icons-material/Login";
import RefreshIcon from "@mui/icons-material/Refresh";
import SendIcon from "@mui/icons-material/Send";

import { ClassroomSession } from "../api/academic";
import {
  Announcement,
  AnnouncementMessage,
  classroomSocketUrl,
  fetchAnnouncements
} from "../api/announcements";
import { fetchActiveSessions, fetchPublicSession, studentSignIn, StudentSignInResult } from "../api/classroom";
import {
  Question,
  QuestionPublishedMessage,
  fetchPublicQuestions,
  submitQuestionAnswer
} from "../api/questions";
import { TeachingAssistSocket } from "../api/websocket";
import { AppSnackbar } from "../components/AppSnackbar";

type ClassroomMessage = AnnouncementMessage | QuestionPublishedMessage;

const QUESTION_TYPE_LABELS: Record<Question["question_type"], string> = {
  single_choice: "单选题",
  multiple_choice: "多选题",
  true_false: "判断题",
  fill_blank: "填空题",
  short_answer: "简答题"
};

export function StudentPage() {
  const [activeSessions, setActiveSessions] = useState<ClassroomSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | "">("");
  const [sessionIdInput, setSessionIdInput] = useState("");
  const [currentSession, setCurrentSession] = useState<ClassroomSession | null>(null);
  const [studentId, setStudentId] = useState("");
  const [name, setName] = useState("");
  const [result, setResult] = useState<StudentSignInResult | null>(null);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<number, string | string[]>>({});
  const [submittedQuestions, setSubmittedQuestions] = useState<Record<number, boolean>>({});
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
    setQuestions([]);
    setSubmittedQuestions({});
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
        const [items, questionItems] = await Promise.all([fetchAnnouncements(sessionId, lastId), fetchPublicQuestions(sessionId)]);
        if (!disposed) {
          mergeAnnouncements(items);
          if (questionItems.length) {
            setQuestions(questionItems);
          }
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
        const payload = JSON.parse(event.data) as ClassroomMessage;
        if (payload.type === "announcement.created") {
          mergeAnnouncements([payload.announcement]);
          setMessage("收到新的课堂公告");
        }
        if (payload.type === "question.published") {
          setQuestions((current) => {
            const next = new Map<number, Question>();
            [payload.question, ...current].forEach((item) => next.set(item.id, item));
            return Array.from(next.values()).sort((a, b) => b.id - a.id);
          });
          setMessage("收到新的课堂问题");
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

  function setQuestionAnswer(question: Question, value: string, checked?: boolean) {
    setAnswers((current) => {
      if (question.question_type === "multiple_choice") {
        const existing = Array.isArray(current[question.id]) ? (current[question.id] as string[]) : [];
        const next = checked ? [...existing, value] : existing.filter((item) => item !== value);
        return { ...current, [question.id]: next };
      }
      return { ...current, [question.id]: value };
    });
  }

  async function handleSubmitAnswer(question: Question) {
    if (!studentId || !name) {
      setError("请先填写学号和姓名");
      return;
    }
    try {
      await submitQuestionAnswer(question.id, {
        student_id: studentId,
        name,
        answer: answers[question.id] ?? "",
        action: "submit_answer"
      });
      setSubmittedQuestions((current) => ({ ...current, [question.id]: true }));
      setMessage("答案已提交");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function renderAnswerInput(question: Question) {
    const answer = answers[question.id];
    if (question.question_type === "single_choice" || question.question_type === "true_false") {
      return (
        <FormControl fullWidth>
          <InputLabel id={`question-answer-${question.id}`}>选择答案</InputLabel>
          <Select
            labelId={`question-answer-${question.id}`}
            label="选择答案"
            value={typeof answer === "string" ? answer : ""}
            onChange={(event) => setQuestionAnswer(question, event.target.value)}
          >
            {question.options.map((option) => (
              <MenuItem key={option.option_key} value={option.option_key}>
                {option.option_key}. {option.content}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }
    if (question.question_type === "multiple_choice") {
      const selected = Array.isArray(answer) ? answer : [];
      return (
        <Stack spacing={0.5}>
          {question.options.map((option) => (
            <FormControlLabel
              key={option.option_key}
              control={
                <Checkbox
                  checked={selected.includes(option.option_key)}
                  onChange={(event) => setQuestionAnswer(question, option.option_key, event.target.checked)}
                />
              }
              label={`${option.option_key}. ${option.content}`}
            />
          ))}
        </Stack>
      );
    }
    return (
      <TextField
        label="我的答案"
        value={typeof answer === "string" ? answer : ""}
        onChange={(event) => setQuestionAnswer(question, event.target.value)}
        multiline={question.question_type === "short_answer"}
        minRows={question.question_type === "short_answer" ? 3 : 1}
        fullWidth
      />
    );
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

      <Card sx={{ maxWidth: 760 }}>
        <CardContent>
          <Stack spacing={1.5}>
            <Typography variant="h2">课堂问答</Typography>
            {questions.map((question) => (
              <Paper key={question.id} variant="outlined" sx={{ p: 2 }}>
                <Stack spacing={1.5}>
                  <Box>
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                      <Typography fontWeight={700}>{question.title}</Typography>
                      <Chip size="small" label={QUESTION_TYPE_LABELS[question.question_type]} />
                      {submittedQuestions[question.id] && <Chip size="small" color="success" label="已提交" />}
                    </Stack>
                    <Typography sx={{ mt: 0.75 }}>{question.content}</Typography>
                    {question.deadline && (
                      <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
                        截止时间：{question.deadline}
                      </Typography>
                    )}
                  </Box>
                  {renderAnswerInput(question)}
                  <Button
                    variant="contained"
                    startIcon={<SendIcon />}
                    onClick={() => handleSubmitAnswer(question)}
                    disabled={Boolean(submittedQuestions[question.id])}
                  >
                    提交答案
                  </Button>
                </Stack>
              </Paper>
            ))}
            {questions.length === 0 && <Typography color="text.secondary">进入课堂后可查看教师发布的问题。</Typography>}
          </Stack>
        </CardContent>
      </Card>

      <AppSnackbar open={Boolean(message)} message={message} severity="success" onClose={() => setMessage("")} />
    </Stack>
  );
}
