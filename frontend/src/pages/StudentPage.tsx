import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Badge,
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
import ChatBubble from "../components/ChatBubble";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import LoginIcon from "@mui/icons-material/Login";
import RefreshIcon from "@mui/icons-material/Refresh";
import SendIcon from "@mui/icons-material/Send";
import AssignmentIcon from "@mui/icons-material/Assignment";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import PsychologyIcon from "@mui/icons-material/Psychology";

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
  fetchQuestionDraft,
  fetchPublicQuestions,
  submitQuestionAnswer
} from "../api/questions";
import {
  Homework,
  HomeworkSubmitResult,
  fetchHomeworkFeedback,
  fetchPublicHomework,
  submitHomework
} from "../api/homework";
import { fetchStudentEvaluationFeedback } from "../api/evaluation";
import {
  InteractionMessage,
  InteractionMessageCreated,
  InteractionModerated,
  InteractionSettings,
  InteractionSettingsUpdated,
  fetchInteractionMessages,
  fetchInteractionSettings,
  publishStudentInteractionMessage
} from "../api/interactions";
import {
  MessageCreated,
  PrivateMessage,
  fetchStudentThread,
  markStudentMessagesRead,
  messageSocketUrl,
  sendStudentMessage
} from "../api/messages";
import { recordCachedReplay } from "../api/recovery";
import { TeachingAssistSocket } from "../api/websocket";
import { AppSnackbar } from "../components/AppSnackbar";
import { AIChatPanel } from "../components/AIChatPanel";
import { useStatusStore } from "../store/statusStore";

type ClassroomMessage =
  | AnnouncementMessage
  | QuestionPublishedMessage
  | InteractionMessageCreated
  | InteractionSettingsUpdated
  | InteractionModerated;

type CachedRequest =
  | {
      id: string;
      type: "question";
      sessionId: number;
      questionId: number;
      payload: { student_id: string; name: string; answer: unknown; action: "submit_answer" };
      createdAt: string;
    }
  | {
      id: string;
      type: "homework";
      sessionId: number;
      homeworkId: number;
      payload: { student_id: string; name: string; text_content?: string };
      createdAt: string;
    };

const CACHE_KEY = "teaching_assist_cached_requests";
const DRAFT_KEY = "teaching_assist_question_drafts";

const QUESTION_TYPE_LABELS: Record<Question["question_type"], string> = {
  single_choice: "单选题",
  multiple_choice: "多选题",
  true_false: "判断题",
  fill_blank: "填空题",
  short_answer: "简答题"
};

const SIGN_IN_STATUS_LABELS: Record<string, string> = {
  normal: "正常",
  late: "迟到",
  absent: "缺勤",
  leave: "请假"
};

type StudentSectionKey =
  | "signin"
  | "announcements"
  | "questions"
  | "interaction"
  | "homework"
  | "feedback"
  | "messages"
  | "aichat";

const STUDENT_SECTIONS: Array<{ key: StudentSectionKey; label: string; description: string }> = [
  { key: "signin", label: "课堂签到", description: "填写身份、选择课堂并签到" },
  { key: "announcements", label: "课堂公告", description: "教师发布的正式通知" },
  { key: "questions", label: "课堂问答", description: "作答题目、查看判分" },
  { key: "interaction", label: "课堂互动", description: "全班可见的自由留言" },
  { key: "homework", label: "课堂作业", description: "查看与提交作业" },
  { key: "feedback", label: "学习反馈", description: "查看个人课堂评估" },
  { key: "messages", label: "私信老师", description: "与老师一对一对话" },
  { key: "aichat", label: "AI 课堂", description: "课程相关对话、查询我的数据" },
];

function StudentSectionPlaceholder({ label }: { label: string }) {
  return (
    <Alert severity="info">
      请先在左侧「签到」中完成课堂签到，再查看「{label}」。
    </Alert>
  );
}

export function StudentPage() {
  const [activeSessions, setActiveSessions] = useState<ClassroomSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | "">("");
  const [sessionIdInput, setSessionIdInput] = useState("");
  const [currentSession, setCurrentSession] = useState<ClassroomSession | null>(null);
  const [studentId, setStudentId] = useState("");
  const [name, setName] = useState("");
  const [result, setResult] = useState<StudentSignInResult | null>(null);
  const [studentToken, setStudentToken] = useState<string | null>(null);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [announcementUnread, setAnnouncementUnread] = useState(0);
  const [interactionUnread, setInteractionUnread] = useState(0);
  const [messagesUnread, setMessagesUnread] = useState(0);
  const [interactionSettings, setInteractionSettings] = useState<InteractionSettings | null>(null);
  const [interactionMessages, setInteractionMessages] = useState<InteractionMessage[]>([]);
  const [interactionContent, setInteractionContent] = useState("");
  const [sendingInteraction, setSendingInteraction] = useState(false);
  const [privateMessages, setPrivateMessages] = useState<PrivateMessage[]>([]);
  const [privateContent, setPrivateContent] = useState("");
  const privateSocketRef = useRef<TeachingAssistSocket | null>(null);
  const lastPrivateMessageIdRef = useRef(0);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<number, string | string[]>>({});
  const [submittedQuestions, setSubmittedQuestions] = useState<Record<number, boolean>>({});
  const [homeworkList, setHomeworkList] = useState<Homework[]>([]);
  const [homeworkText, setHomeworkText] = useState<Record<number, string>>({});
  const [homeworkFiles, setHomeworkFiles] = useState<Record<number, File[]>>({});
  const [submittedHomework, setSubmittedHomework] = useState<Record<number, HomeworkSubmitResult>>({});
  const [homeworkFeedback, setHomeworkFeedback] = useState<Record<number, Record<string, unknown>>>({});
  const [evaluationFeedback, setEvaluationFeedback] = useState<Record<string, unknown> | null>(null);
  const [cachedCount, setCachedCount] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [snackError, setSnackError] = useState("");
  const [activeStudentSection, setActiveStudentSection] = useState<StudentSectionKey>("signin");
  const activeStudentSectionRef = useRef<StudentSectionKey>("signin");
  const socketRef = useRef<TeachingAssistSocket | null>(null);
  const lastAnnouncementIdRef = useRef(0);
  const lastInteractionMessageIdRef = useRef(0);

  useEffect(() => {
    activeStudentSectionRef.current = activeStudentSection;
  }, [activeStudentSection]);

  // error 自动消失：5 秒后清空，用户手动关闭则取消计时器
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (error) {
      errorTimerRef.current = setTimeout(() => setError(""), 5000);
    }
    return () => {
      if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    };
  }, [error]);

  useEffect(() => {
    loadActiveSessions();
    setCachedCount(readCachedRequests().length);
  }, []);

  useEffect(() => {
    socketRef.current?.close();
    socketRef.current = null;
    setAnnouncements([]);
    setAnnouncementUnread(0);
    setInteractionMessages([]);
    setInteractionSettings(null);
    setQuestions([]);
    setHomeworkList([]);
    setSubmittedQuestions({});
    setResult(null); // 切换课堂时清空上一课堂的签到结果，避免旧 result 误判已签到
    setStudentToken(null); // 令牌与(学生,课堂)绑定，切换课堂即失效
    lastAnnouncementIdRef.current = 0;
    lastInteractionMessageIdRef.current = 0;
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
    const mergeInteractionMessages = (items: InteractionMessage[]) => {
      items.forEach((item) => {
        lastInteractionMessageIdRef.current = Math.max(lastInteractionMessageIdRef.current, item.id);
      });
      setInteractionMessages((current) => {
        const next = new Map<number, InteractionMessage>();
        [...items, ...current].forEach((item) => next.set(item.id, item));
        return Array.from(next.values()).sort((a, b) => b.id - a.id);
      });
    };
    const loadMessages = async (lastId?: number) => {
      try {
        const [items, interactionSettingsData, interactionItems, questionItems, homeworkItems] = await Promise.all([
          fetchAnnouncements(sessionId, lastId),
          fetchInteractionSettings(sessionId),
          fetchInteractionMessages(sessionId, lastId ? lastInteractionMessageIdRef.current : undefined),
          fetchPublicQuestions(sessionId),
          fetchPublicHomework(sessionId)
        ]);
        if (!disposed) {
          mergeAnnouncements(items);
          setInteractionSettings(interactionSettingsData);
          mergeInteractionMessages(interactionItems);
          if (questionItems.length) {
            setQuestions(questionItems);
          }
          setHomeworkList(homeworkItems);
          restoreLocalDrafts(questionItems);
          void restoreServerDrafts(questionItems);
          void replayCachedRequests(sessionId);
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
          const content = payload.announcement.content ?? "";
          const preview = content.length > 40 ? `${content.slice(0, 40)}…` : content;
          setMessage(preview ? `收到新公告：${preview}` : "收到新的课堂公告");
          if (activeStudentSectionRef.current !== "announcements") {
            setAnnouncementUnread((current) => current + 1);
          }
        }
        if (payload.type === "interaction.message.created") {
          mergeInteractionMessages([payload.message]);
          if (activeStudentSectionRef.current !== "interaction") {
            setInteractionUnread((current) => current + 1);
          }
        }
        if (payload.type === "interaction.settings.updated") {
          setInteractionSettings(payload.settings);
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
        if (lastId || lastInteractionMessageIdRef.current) {
          loadMessages(lastId);
        }
        void replayCachedRequests(sessionId);
      }
    );
    socketRef.current = socket;
    socket.connect();
    return () => {
      disposed = true;
      socket.close();
    };
  }, [currentSession?.id]);

  useEffect(() => {
    if (!studentId || !name || !studentToken) {
      setPrivateMessages([]);
      lastPrivateMessageIdRef.current = 0;
      return undefined;
    }
    let disposed = false;
    // 切换身份/令牌时先清空上一身份的私信，避免跨身份串号混显
    setPrivateMessages([]);
    lastPrivateMessageIdRef.current = 0;
    const mergePrivateMessages = (items: PrivateMessage[]) => {
      items.forEach((item) => {
        lastPrivateMessageIdRef.current = Math.max(lastPrivateMessageIdRef.current, item.id);
      });
      setPrivateMessages((current) => {
        const next = new Map<number, PrivateMessage>();
        [...items, ...current].forEach((item) => next.set(item.id, item));
        return Array.from(next.values()).sort((a, b) => a.id - b.id);
      });
    };
    const loadThread = async () => {
      try {
        const items = await fetchStudentThread(studentId, name, studentToken);
        if (!disposed) {
          mergePrivateMessages(items);
          // 打开会话即显式标记已读（替代原先 GET 内写库），并刷新未读计数
          if (studentToken) {
            void markStudentMessagesRead(studentToken).catch(() => undefined);
          }
        }
      } catch (err) {
        if (!disposed) {
          setError((err as Error).message);
        }
      }
    };
    loadThread();
    const socket = new TeachingAssistSocket(
      messageSocketUrl(studentToken ?? undefined),
      (event) => {
        const payload = JSON.parse(event.data) as MessageCreated;
        if (payload.type === "message.created" && payload.message.receiver_role === "student") {
          mergePrivateMessages([payload.message]);
          setMessage("老师回复了你的私信");
          if (activeStudentSectionRef.current !== "messages") {
            setMessagesUnread((current) => current + 1);
          }
        }
      },
      3000
    );
    privateSocketRef.current = socket;
    socket.connect();
    return () => {
      disposed = true;
      socket.close();
      privateSocketRef.current = null;
    };
  }, [studentId, name, studentToken]);

  async function handleSendPrivateMessage() {
    if (!studentId || !name) {
      setError("请先填写学号和姓名");
      return;
    }
    if (!privateContent.trim()) {
      setError("私信内容不能为空");
      return;
    }
    try {
      await sendStudentMessage(studentId, name, privateContent, studentToken);
      setPrivateContent("");
      setMessage("私信已发送");
      const items = await fetchStudentThread(studentId, name, studentToken);
      setPrivateMessages(items);
      lastPrivateMessageIdRef.current = items.reduce((max, item) => Math.max(max, item.id), 0);
    } catch (err) {
      setError((err as Error).message);
    }
  }

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

  function readCachedRequests(): CachedRequest[] {
    try {
      return JSON.parse(localStorage.getItem(CACHE_KEY) ?? "[]") as CachedRequest[];
    } catch {
      return [];
    }
  }

  function writeCachedRequests(items: CachedRequest[]) {
    localStorage.setItem(CACHE_KEY, JSON.stringify(items));
    setCachedCount(items.length);
  }

  function cacheRequest(item: CachedRequest) {
    const items = readCachedRequests();
    writeCachedRequests([...items, item]);
  }

  function readDrafts() {
    try {
      return JSON.parse(localStorage.getItem(DRAFT_KEY) ?? "{}") as Record<string, unknown>;
    } catch {
      return {};
    }
  }

  function saveLocalDraft(questionId: number, answer: unknown) {
    const drafts = readDrafts();
    drafts[String(questionId)] = answer;
    localStorage.setItem(DRAFT_KEY, JSON.stringify(drafts));
  }

  function restoreLocalDrafts(questionItems: Question[]) {
    const drafts = readDrafts();
    setAnswers((current) => {
      const next = { ...current };
      questionItems.forEach((question) => {
        const value = drafts[String(question.id)];
        if (value !== undefined && next[question.id] === undefined) {
          next[question.id] = value as string | string[];
        }
      });
      return next;
    });
  }

  async function restoreServerDrafts(questionItems: Question[]) {
    if (!studentId || !name) {
      return;
    }
    const entries = await Promise.all(
      questionItems.map(async (question) => {
        try {
          const draft = await fetchQuestionDraft(question.id, studentId, name, studentToken);
          return [question.id, draft.answer ?? draft.answer_text] as const;
        } catch {
          return [question.id, undefined] as const;
        }
      })
    );
    setAnswers((current) => {
      const next = { ...current };
      entries.forEach(([questionId, value]) => {
        if (value !== undefined && next[questionId] === undefined) {
          next[questionId] = value as string | string[];
        }
      });
      return next;
    });
  }

  async function replayCachedRequests(sessionId: number) {
    const items = readCachedRequests();
    const remaining: CachedRequest[] = [];
    let replayed = 0;
    for (const item of items) {
      if (item.sessionId !== sessionId) {
        remaining.push(item);
        continue;
      }
      try {
        if (item.type === "question") {
          await submitQuestionAnswer(item.questionId, item.payload);
          setSubmittedQuestions((current) => ({ ...current, [item.questionId]: true }));
        } else {
          const result = await submitHomework(item.homeworkId, item.payload);
          setSubmittedHomework((current) => ({ ...current, [item.homeworkId]: result }));
        }
        await recordCachedReplay(sessionId, { cached_id: item.id, type: item.type, created_at: item.createdAt });
        replayed += 1;
      } catch {
        remaining.push(item);
      }
    }
    writeCachedRequests(remaining);
    if (replayed > 0) {
      setMessage(`已重发 ${replayed} 条离线缓存请求`);
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
      setStudentToken(signInResult.token ?? null);
      setMessage(signInResult.duplicate ? "你已经完成过签到" : "签到成功");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleSendInteractionMessage() {
    const sessionId = currentSession?.id || Number(sessionIdInput);
    if (!sessionId || !studentId || !name) {
      setError("请先完成签到后再参与课堂互动");
      return;
    }
    if (!result || !["normal", "late"].includes(result.status)) {
      setError("完成正常或迟到签到后才能参与课堂互动");
      return;
    }
    if (sendingInteraction) {
      return;
    }
    setSendingInteraction(true);
    try {
      await publishStudentInteractionMessage(sessionId, studentId, name, interactionContent);
      setInteractionContent("");
      setMessage("互动留言已发送");
    } catch (err) {
      const msg = (err as Error).message;
      if (msg.startsWith("内容未通过审核")) {
        // AI 拦截：用浮动气泡提醒，并清空输入框，避免学生误以为已发出
        setSnackError(msg);
        setInteractionContent("");
      } else {
        setError(msg);
      }
    } finally {
      setSendingInteraction(false);
    }
  }

  function setQuestionAnswer(question: Question, value: string, checked?: boolean) {
    setAnswers((current) => {
      if (question.question_type === "multiple_choice") {
        const existing = Array.isArray(current[question.id]) ? (current[question.id] as string[]) : [];
        const next = checked ? [...existing, value] : existing.filter((item) => item !== value);
        saveLocalDraft(question.id, next);
        return { ...current, [question.id]: next };
      }
      saveLocalDraft(question.id, value);
      return { ...current, [question.id]: value };
    });
  }

  async function handleSaveDraft(question: Question) {
    if (!studentId || !name) {
      setError("请先填写学号和姓名");
      return;
    }
    try {
      await submitQuestionAnswer(question.id, {
        student_id: studentId,
        name,
        answer: answers[question.id] ?? "",
        action: "save_draft"
      });
      saveLocalDraft(question.id, answers[question.id] ?? "");
      setMessage("答题草稿已保存");
    } catch (err) {
      saveLocalDraft(question.id, answers[question.id] ?? "");
      setMessage("网络暂不可用，草稿已保存在本机");
    }
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
      cacheRequest({
        id: `${Date.now()}-${question.id}`,
        type: "question",
        sessionId: question.session_id,
        questionId: question.id,
        payload: {
          student_id: studentId,
          name,
          answer: answers[question.id] ?? "",
          action: "submit_answer"
        },
        createdAt: new Date().toISOString()
      });
      setMessage("网络暂不可用，答案已缓存，重连后会自动重发");
    }
  }

  async function handleSubmitHomework(homework: Homework) {
    if (!studentId || !name) {
      setError("请先填写学号和姓名");
      return;
    }
    try {
      const result = await submitHomework(homework.id, {
        student_id: studentId,
        name,
        text_content: homeworkText[homework.id] ?? "",
        files: homeworkFiles[homework.id] ?? []
      });
      setSubmittedHomework((current) => ({ ...current, [homework.id]: result }));
      setMessage(`作业已提交，当前版本 ${result.submit_version}`);
    } catch (err) {
      if ((homeworkFiles[homework.id] ?? []).length > 0) {
        setError("网络异常，带附件的作业无法离线缓存，请恢复网络后重新提交");
        return;
      }
      cacheRequest({
        id: `${Date.now()}-${homework.id}`,
        type: "homework",
        sessionId: homework.session_id,
        homeworkId: homework.id,
        payload: {
          student_id: studentId,
          name,
          text_content: homeworkText[homework.id] ?? ""
        },
        createdAt: new Date().toISOString()
      });
      setMessage("网络暂不可用，作业文本已缓存，重连后会自动重发");
    }
  }

  async function handleLoadHomeworkFeedback(homework: Homework) {
    if (!studentId || !name) {
      setError("请先填写学号和姓名");
      return;
    }
    try {
      const feedback = await fetchHomeworkFeedback(homework.id, studentId, name, studentToken);
      setHomeworkFeedback((current) => ({ ...current, [homework.id]: feedback }));
      setMessage(feedback.published ? "作业反馈已获取" : "教师尚未发布该作业成绩");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadEvaluationFeedback() {
    const sessionId = currentSession?.id || Number(sessionIdInput);
    if (!sessionId || !studentId || !name) {
      setError("请先选择课堂并填写学号、姓名");
      return;
    }
    try {
      const feedback = await fetchStudentEvaluationFeedback(sessionId, studentId, name, studentToken);
      setEvaluationFeedback(feedback);
      setMessage(feedback.evaluation ? "学习反馈已获取" : "教师尚未生成课堂评估");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function updateHomeworkFiles(homeworkId: number, fileList: FileList | null) {
    setHomeworkFiles((current) => ({
      ...current,
      [homeworkId]: fileList ? Array.from(fileList) : []
    }));
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

  // 将学生身份信息同步到全局状态，供 AppLayout 标题栏展示
  useEffect(() => {
    useStatusStore.getState().setStudentInfo(studentId, name);
  }, [studentId, name]);

  useEffect(() => {
    useStatusStore.getState().setStudentLoggedIn(Boolean(result));
  }, [result]);

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "260px minmax(0, 1fr)" },
        gap: 2,
        alignItems: "start",
      }}
    >
      <Paper
        variant="outlined"
        sx={{
          position: { xs: "static", md: "sticky" },
          top: { md: 16 },
          p: 1,
          maxHeight: { md: "calc(100vh - 120px)" },
          overflow: "auto",
        }}
      >
        <Stack spacing={0.75}>
          {STUDENT_SECTIONS.map((section) => {
            const unread =
              section.key === "announcements" ? announcementUnread :
              section.key === "interaction" ? interactionUnread :
              section.key === "messages" ? messagesUnread : 0;
            const labelNode = (
              <Box>
                <Typography component="span" sx={{ display: "block", fontWeight: 700, lineHeight: 1.3 }}>
                  {section.label}
                </Typography>
                <Typography component="span" sx={{ display: "block", fontSize: "0.75rem", opacity: 0.78, lineHeight: 1.4 }}>
                  {section.description}
                </Typography>
              </Box>
            );
            return (
              <Button
                key={section.key}
                fullWidth
                variant={activeStudentSection === section.key ? "contained" : "text"}
                onClick={() => {
                  setActiveStudentSection(section.key);
                  if (section.key === "announcements") setAnnouncementUnread(0);
                  if (section.key === "interaction") setInteractionUnread(0);
                  if (section.key === "messages") setMessagesUnread(0);
                }}
                sx={{
                  justifyContent: "flex-start",
                  alignItems: "flex-start",
                  textAlign: "left",
                  py: 1,
                  px: 1.25,
                  minHeight: 58,
                }}
              >
                {unread > 0 ? (
                  <Badge badgeContent={unread} color="error" max={99} sx={{ width: "100%" }}>
                    {labelNode}
                  </Badge>
                ) : (
                  labelNode
                )}
              </Button>
            );
          })}
        </Stack>
      </Paper>

      <Stack spacing={3} sx={{ minWidth: 0 }}>
        {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}

        {activeStudentSection === "signin" && (
          <Box>
            <Typography variant="h1" sx={{ mb: 2 }}>课堂签到</Typography>
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
                      {cachedCount > 0 && <Chip size="small" color="warning" label={`待重发 ${cachedCount}`} sx={{ ml: 1 }} />}
                    </Alert>
                  )}

                  <TextField label="学号" value={studentId} onChange={(event) => setStudentId(event.target.value)} fullWidth />
                  <TextField label="姓名" value={name} onChange={(event) => setName(event.target.value)} fullWidth />
                  <Button variant="contained" startIcon={<LoginIcon />} onClick={handleSignIn}>
                    提交签到
                  </Button>

                  {result && (
                    <Stack spacing={1}>
                      <Alert severity={result.status === "late" ? "warning" : "success"}>
                        {result.student_number} / {result.student_name} / {SIGN_IN_STATUS_LABELS[result.status] ?? result.status}
                        {result.sign_time ? ` / ${result.sign_time}` : ""}
                      </Alert>
                      {result.device_warning && (
                        <Alert severity={result.device_warning.level === "critical" ? "error" : "warning"}>
                          ⚠️ 设备共用警告：{result.device_warning.message}
                        </Alert>
                      )}
                    </Stack>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Box>
        )}

        {activeStudentSection === "announcements" && (
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
          )}

        {activeStudentSection === "questions" && (
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
                        <Button variant="outlined" onClick={() => handleSaveDraft(question)} disabled={Boolean(submittedQuestions[question.id])}>
                          保存草稿
                        </Button>
                      </Stack>
                    </Paper>
                  ))}
                  {questions.length === 0 && <Typography color="text.secondary">进入课堂后可查看教师发布的问题。</Typography>}
                </Stack>
              </CardContent>
            </Card>
          )}

        {activeStudentSection === "interaction" && (
            <Card sx={{ maxWidth: 760 }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Box>
                    <Typography variant="h2">课堂互动</Typography>
                    <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                      完成签到后可参与课堂留言，全班可见。
                    </Typography>
                  </Box>
                  {interactionMessages.map((item) => (
                    <ChatBubble
                      key={item.id}
                      role={item.sender_role === "teacher" ? "teacher" : "student"}
                      name={item.sender_name}
                      time={item.created_at}
                      content={item.content}
                      selfName={item.sender_name}
                    />
                  ))}
                  {interactionMessages.length === 0 && (
                    <Typography color="text.secondary">暂无课堂互动留言。</Typography>
                  )}
                  {!result && <Alert severity="info">完成签到后可参与课堂互动。</Alert>}
                  {result && !Boolean(interactionSettings?.student_messages_enabled ?? true) && (
                    <Alert severity="warning">教师已暂停课堂互动发言，你仍可查看已有留言。</Alert>
                  )}
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                    <TextField
                      label="互动留言"
                      value={interactionContent}
                      onChange={(event) => setInteractionContent(event.target.value)}
                      disabled={!result || !Boolean(interactionSettings?.student_messages_enabled ?? true)}
                      helperText={`${interactionContent.length}/300`}
                      inputProps={{ maxLength: 300 }}
                      fullWidth
                    />
                    <Button
                      variant="contained"
                      startIcon={<SendIcon />}
                      onClick={handleSendInteractionMessage}
                      disabled={!result || !Boolean(interactionSettings?.student_messages_enabled ?? true) || sendingInteraction}
                      sx={{ minWidth: 120 }}
                    >
                      {sendingInteraction ? "审核中…" : "发送"}
                    </Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          )}

        {activeStudentSection === "homework" && (
            <Card sx={{ maxWidth: 760 }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <AssignmentIcon color="primary" />
                    <Typography variant="h2">课堂作业</Typography>
                  </Stack>
                  {homeworkList.map((homework) => {
                    const submitted = submittedHomework[homework.id];
                    const selectedFiles = homeworkFiles[homework.id] ?? [];
                    return (
                      <Paper key={homework.id} variant="outlined" sx={{ p: 2 }}>
                        <Stack spacing={1.5}>
                          <Box>
                            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                              <Typography fontWeight={700}>{homework.title}</Typography>
                              <Chip size="small" label={homework.status} />
                              {submitted && (
                                <Chip
                                  size="small"
                                  color={submitted.status === "late" ? "warning" : "success"}
                                  label={`已提交 v${submitted.submit_version}`}
                                />
                              )}
                            </Stack>
                            <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
                              截止时间：{homework.deadline}
                              {homework.allow_late ? "，允许迟交" : ""}
                            </Typography>
                            {homework.description && <Typography sx={{ mt: 0.75, whiteSpace: "pre-wrap" }}>{homework.description}</Typography>}
                            {homework.grading_criteria && (
                              <Typography color="text.secondary" variant="body2" sx={{ mt: 0.75, whiteSpace: "pre-wrap" }}>
                                评分标准：{homework.grading_criteria}
                              </Typography>
                            )}
                            {homework.attachments?.length > 0 && (
                              <Stack spacing={0.25} sx={{ mt: 0.75 }}>
                                {homework.attachments.map((file) => (
                                  <Typography key={file.id} color="text.secondary" variant="body2">
                                    教师附件：{file.original_name} ({Math.ceil(file.file_size / 1024)} KB)
                                  </Typography>
                                ))}
                              </Stack>
                            )}
                          </Box>
                          <TextField
                            label="提交内容"
                            value={homeworkText[homework.id] ?? ""}
                            onChange={(event) =>
                              setHomeworkText((current) => ({ ...current, [homework.id]: event.target.value }))
                            }
                            inputProps={{ maxLength: 5000 }}
                            multiline
                            minRows={3}
                            fullWidth
                          />
                          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ xs: "stretch", sm: "center" }}>
                            <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
                              选择附件
                              <input
                                type="file"
                                multiple
                                hidden
                                onChange={(event) => updateHomeworkFiles(homework.id, event.target.files)}
                              />
                            </Button>
                            <Typography color="text.secondary" variant="body2">
                              {selectedFiles.length > 0
                                ? selectedFiles.map((file) => file.name).join("，")
                                : "支持 doc、pdf、zip、txt、图片等常见格式"}
                            </Typography>
                          </Stack>
                          <Button variant="contained" startIcon={<SendIcon />} onClick={() => handleSubmitHomework(homework)}>
                            {submitted ? "再次提交" : "提交作业"}
                          </Button>
                          <Button variant="outlined" onClick={() => handleLoadHomeworkFeedback(homework)}>
                            查看反馈
                          </Button>
                          {homeworkFeedback[homework.id] && (
                            <Alert severity={homeworkFeedback[homework.id].published ? "success" : "info"}>
                              {homeworkFeedback[homework.id].published
                                ? `得分 ${String((homeworkFeedback[homework.id].submission as Record<string, unknown>)?.final_score ?? "-")}：${String((homeworkFeedback[homework.id].submission as Record<string, unknown>)?.final_feedback ?? "")}`
                                : "教师尚未发布成绩"}
                            </Alert>
                          )}
                        </Stack>
                      </Paper>
                    );
                  })}
                  {homeworkList.length === 0 && <Typography color="text.secondary">进入课堂后可查看教师发布的作业。</Typography>}
                </Stack>
              </CardContent>
            </Card>
          )}

        {activeStudentSection === "feedback" && (
            <Card sx={{ maxWidth: 760 }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Typography variant="h2">学习反馈</Typography>
                  <Button variant="outlined" onClick={handleLoadEvaluationFeedback}>
                    查看课堂评估
                  </Button>
                  {evaluationFeedback?.evaluation ? (
                    <Alert severity="info">
                      总分 {String((evaluationFeedback.evaluation as Record<string, unknown>).total_score)}，
                      等级 {String((evaluationFeedback.evaluation as Record<string, unknown>).level)}：
                      {String((evaluationFeedback.evaluation as Record<string, unknown>).advice ?? "")}
                    </Alert>
                  ) : (
                    <Typography color="text.secondary">教师生成评估后可查看个人课堂反馈。</Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          )}

        {activeStudentSection === "messages" &&
          (result ? (
            <Card sx={{ maxWidth: 760 }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Box>
                    <Typography variant="h2">私信老师</Typography>
                    <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                      与老师的 1:1 私聊，仅你和老师可见。完成签到后即可收发。
                    </Typography>
                  </Box>
                  {privateMessages.map((item) => (
                    <ChatBubble
                      key={item.id}
                      role={item.sender_role === "student" ? "student" : "teacher"}
                      name={item.sender_role === "student" ? (item.sender_name || "我") : item.sender_name}
                      time={item.created_at}
                      content={item.content}
                      selfName={item.sender_role === "teacher" ? "老师" : undefined}
                    />
                  ))}
                  {privateMessages.length === 0 && (
                    <Typography color="text.secondary">还没有私信，给老师发一条吧。</Typography>
                  )}
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                    <TextField
                      label="私信内容"
                      value={privateContent}
                      onChange={(event) => setPrivateContent(event.target.value)}
                      helperText={`${privateContent.length}/500`}
                      inputProps={{ maxLength: 500 }}
                      fullWidth
                    />
                    <Button
                      variant="contained"
                      startIcon={<SendIcon />}
                      onClick={handleSendPrivateMessage}
                      disabled={!studentId || !name}
                      sx={{ minWidth: 120 }}
                    >
                      发送
                    </Button>
                  </Stack>
                  {(!studentId || !name) && (
                    <Alert severity="info">请先在「签到」中完成课堂签到，即可与老师私信。</Alert>
                  )}
                </Stack>
              </CardContent>
            </Card>
          ) : (
            <StudentSectionPlaceholder label="私信老师" />
          ))}

        {activeStudentSection === "aichat" &&
          (!result || !currentSession ? (
            <StudentSectionPlaceholder label="AI 课堂" />
          ) : (
            <Card sx={{ maxWidth: 820 }}>
              <CardContent>
                <Stack spacing={2}>
                  <Box>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <PsychologyIcon color="primary" />
                      <Typography variant="h2">AI 课堂</Typography>
                    </Stack>
                    <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                      与 AI 助手的课程相关对话。可问课程知识，或查询你自己的学习数据（签到、作业、答题、评估）。对话内容不保存。
                    </Typography>
                  </Box>
                  <Box sx={{ height: 620 }}>
                    <AIChatPanel
                      key={currentSession.id}
                      role="student"
                      sessionId={currentSession.id}
                      courseName={currentSession.course_name}
                      studentId={studentId}
                      studentName={name}
                    />
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          ))}

        <AppSnackbar open={Boolean(message)} message={message} severity="success" onClose={() => setMessage("")} />
        <AppSnackbar open={Boolean(snackError)} message={snackError} severity="error" onClose={() => setSnackError("")} />
      </Stack>
    </Box>
  );
}
