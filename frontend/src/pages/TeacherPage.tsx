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
import QuizIcon from "@mui/icons-material/Quiz";
import SendIcon from "@mui/icons-material/Send";
import AssignmentIcon from "@mui/icons-material/Assignment";
import PsychologyIcon from "@mui/icons-material/Psychology";
import AssessmentIcon from "@mui/icons-material/Assessment";
import DownloadIcon from "@mui/icons-material/Download";
import RestoreIcon from "@mui/icons-material/Restore";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";

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
  downloadImportErrors,
  fetchClasses,
  fetchCourses,
  fetchSessions,
  fetchStudents,
  linkCourseClass,
  previewStudentImport,
  setStudentActive,
  suggestStudentImportMapping,
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
  Announcement,
  fetchAnnouncements,
  publishAnnouncement
} from "../api/announcements";
import {
  SignInSummary,
  DeviceSharingAlert,
  downloadSignIns,
  endClassroomSession,
  fetchDeviceAlerts,
  fetchSignInLogs,
  fetchSignInSummary,
  reviewDeviceAlert,
  startClassroomSession,
  updateSignInStatus
} from "../api/classroom";
import {
  BonusSummary,
  Question,
  QuestionOption,
  QuestionStats,
  QuestionType,
  downloadQuestionAnswers,
  fetchAnonymousQuestionStats,
  fetchQuestionBonusSettings,
  fetchQuestionBonusSummary,
  fetchQuestionStats,
  fetchQuestions,
  publishQuestion,
  updateQuestionBonusSettings
} from "../api/questions";
import {
  Homework,
  HomeworkSubmissionSummary,
  addHomeworkAttachments,
  createHomework,
  downloadHomeworkSubmissions,
  fetchHomework,
  fetchHomeworkSubmissionSummary,
  publishHomeworkGrades,
  reviewHomeworkSubmission,
  startHomeworkAiReview
} from "../api/homework";
import {
  AiOverview,
  AiProvider,
  AiSafetyCheckResult,
  activateAiProvider,
  checkAiConnectivity,
  checkAiSafety,
  fetchAiFailureTasks,
  fetchAiOverview,
  updateAiProvider,
  updateAiSafety
} from "../api/ai";
import {
  EvaluationReport,
  calculateEvaluation,
  downloadEvaluationReport,
  fetchEvaluationReport,
  updateEvaluationWeights
} from "../api/evaluation";
import {
  InteractionMessage,
  InteractionSettings,
  fetchInteractionMessages,
  fetchInteractionSettings,
  publishTeacherInteractionMessage,
  updateInteractionSettings
} from "../api/interactions";
import {
  applyRecoveryAction,
  fetchRecoveryEvents,
  recordInterruption
} from "../api/recovery";
import { AppSnackbar } from "../components/AppSnackbar";
import { useAuthStore } from "../store/authStore";

const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  single_choice: "单选题",
  multiple_choice: "多选题",
  true_false: "判断题",
  fill_blank: "填空题",
  short_answer: "简答题"
};

const DEFAULT_OPTIONS: QuestionOption[] = [
  { option_key: "A", content: "", is_correct: false },
  { option_key: "B", content: "", is_correct: false },
  { option_key: "C", content: "", is_correct: false },
  { option_key: "D", content: "", is_correct: false }
];

const SIGN_IN_STATUS_LABELS: Record<string, string> = {
  normal: "正常",
  late: "迟到",
  absent: "缺勤",
  leave: "请假"
};

const EVALUATION_WEIGHT_FIELDS = [
  { key: "attendance_weight", label: "签到权重" },
  { key: "question_weight", label: "问答权重" },
  { key: "homework_weight", label: "作业权重" },
  { key: "message_weight", label: "课堂互动权重" },
  { key: "activity_weight", label: "课堂活动权重" }
] as const;

type EvaluationWeightKey = (typeof EVALUATION_WEIGHT_FIELDS)[number]["key"];
type EvaluationWeights = Record<EvaluationWeightKey, number | string>;
type TeacherSectionKey =
  | "system"
  | "ai"
  | "preparation"
  | "classroom"
  | "questions"
  | "homework"
  | "evaluation"
  | "announcements"
  | "interaction";

const DEFAULT_EVALUATION_WEIGHTS: EvaluationWeights = {
  attendance_weight: 20,
  question_weight: 35,
  homework_weight: 25,
  message_weight: 10,
  activity_weight: 10
};

function pickEvaluationWeights(weights: Record<string, number | string>): EvaluationWeights {
  return Object.fromEntries(
    EVALUATION_WEIGHT_FIELDS.map((field) => [field.key, weights[field.key] ?? DEFAULT_EVALUATION_WEIGHTS[field.key]])
  ) as EvaluationWeights;
}

const TEACHER_SECTIONS: Array<{ key: TeacherSectionKey; label: string; description: string }> = [
  { key: "system", label: "系统与备份", description: "服务状态、启动检查、访问地址" },
  { key: "ai", label: "AI 管理", description: "Provider、自检、内容安全" },
  { key: "preparation", label: "课前准备", description: "课程、班级、课堂、导入" },
  { key: "classroom", label: "课堂签到", description: "开课、签到、请假、设备预警" },
  { key: "questions", label: "课堂问答", description: "发布题目、统计、加分" },
  { key: "homework", label: "课堂作业", description: "发布、提交、批阅、成绩" },
  { key: "evaluation", label: "学习评估", description: "权重、评估、恢复记录" },
  { key: "announcements", label: "课堂公告", description: "教师正式通知" },
  { key: "interaction", label: "课堂互动", description: "自由留言、发言开关" }
];

export function TeacherPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [startup, setStartup] = useState<StartupStatus | null>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [accessInfo, setAccessInfo] = useState<AccessInfo | null>(null);
  const [aiOverview, setAiOverview] = useState<AiOverview | null>(null);
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
  const [fieldMapping, setFieldMapping] = useState<Record<number, string>>({});
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [duplicateStrategy, setDuplicateStrategy] = useState<"merge" | "overwrite" | "skip">("merge");
  const [showInactiveStudents, setShowInactiveStudents] = useState(false);
  const [signInSummary, setSignInSummary] = useState<SignInSummary | null>(null);
  const [signInLogs, setSignInLogs] = useState<Array<Record<string, unknown>>>([]);
  const [signInReason, setSignInReason] = useState("教师手动调整");
  const [deviceAlerts, setDeviceAlerts] = useState<DeviceSharingAlert[]>([]);
  const [announcementSessionId, setAnnouncementSessionId] = useState<number | "">("");
  const [announcementContent, setAnnouncementContent] = useState("");
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [interactionSessionId, setInteractionSessionId] = useState<number | "">("");
  const [interactionSettings, setInteractionSettings] = useState<InteractionSettings | null>(null);
  const [interactionMessages, setInteractionMessages] = useState<InteractionMessage[]>([]);
  const [interactionContent, setInteractionContent] = useState("");
  const [questionSessionId, setQuestionSessionId] = useState<number | "">("");
  const [questionTitle, setQuestionTitle] = useState("");
  const [questionContent, setQuestionContent] = useState("");
  const [questionType, setQuestionType] = useState<QuestionType>("single_choice");
  const [questionOptions, setQuestionOptions] = useState<QuestionOption[]>(DEFAULT_OPTIONS);
  const [questionAnswer, setQuestionAnswer] = useState("");
  const [questionKeywords, setQuestionKeywords] = useState("");
  const [questionDeadline, setQuestionDeadline] = useState("");
  const [questionScore, setQuestionScore] = useState<number | "">(1);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [questionStats, setQuestionStats] = useState<QuestionStats | null>(null);
  const [anonymousStats, setAnonymousStats] = useState<Record<string, unknown> | null>(null);
  const [bonusSummary, setBonusSummary] = useState<BonusSummary | null>(null);
  const [bonusSettings, setBonusSettings] = useState<Record<string, number | string>>({});
  const [homeworkSessionId, setHomeworkSessionId] = useState<number | "">("");
  const [homeworkTitle, setHomeworkTitle] = useState("");
  const [homeworkDescription, setHomeworkDescription] = useState("");
  const [homeworkDeadline, setHomeworkDeadline] = useState("");
  const [homeworkCriteria, setHomeworkCriteria] = useState("");
  const [homeworkAllowLate, setHomeworkAllowLate] = useState(false);
  const [homeworkList, setHomeworkList] = useState<Homework[]>([]);
  const [homeworkSummary, setHomeworkSummary] = useState<HomeworkSubmissionSummary | null>(null);
  const [homeworkAttachmentFiles, setHomeworkAttachmentFiles] = useState<Record<number, File[]>>({});
  const [reviewScores, setReviewScores] = useState<Record<number, string>>({});
  const [reviewFeedback, setReviewFeedback] = useState<Record<number, string>>({});
  const [evaluationSessionId, setEvaluationSessionId] = useState<number | "">("");
  const [evaluationReport, setEvaluationReport] = useState<EvaluationReport | null>(null);
  const [evaluationWeights, setEvaluationWeights] = useState<EvaluationWeights>(DEFAULT_EVALUATION_WEIGHTS);
  const [recoverySessionId, setRecoverySessionId] = useState<number | "">("");
  const [recoveryStartedAt, setRecoveryStartedAt] = useState("");
  const [recoveryEndedAt, setRecoveryEndedAt] = useState("");
  const [recoveryEvents, setRecoveryEvents] = useState<Array<Record<string, unknown>>>([]);
  const [aiProviderId, setAiProviderId] = useState<number | "">("");
  const [aiProviderName, setAiProviderName] = useState("");
  const [aiDisplayName, setAiDisplayName] = useState("");
  const [aiBaseUrl, setAiBaseUrl] = useState("");
  const [aiModelName, setAiModelName] = useState("");
  const [aiApiKey, setAiApiKey] = useState("");
  const [aiHttpProxy, setAiHttpProxy] = useState("");
  const [aiEnabled, setAiEnabled] = useState(false);
  const [aiSafetyMaxLength, setAiSafetyMaxLength] = useState<number | "">(2000);
  const [aiSafetyKeywords, setAiSafetyKeywords] = useState("");
  const [aiKeywordAction, setAiKeywordAction] = useState<"replace" | "block">("replace");
  const [aiDisplayStrategy, setAiDisplayStrategy] = useState<"review_first" | "direct_with_report">("review_first");
  const [aiSafetySample, setAiSafetySample] = useState("");
  const [aiSafetyResult, setAiSafetyResult] = useState<AiSafetyCheckResult | null>(null);
  const [aiFailureTaskCount, setAiFailureTaskCount] = useState(0);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [selectedIp, setSelectedIp] = useState("");
  const [selectedPort, setSelectedPort] = useState<number | "">("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [activeTeacherSection, setActiveTeacherSection] = useState<TeacherSectionKey>("system");
  const { isAuthenticated, setTeacherSession, logout: clearSession } = useAuthStore();

  /** Session status: raw English → Chinese label */
  const sessionStatusLabel = (s: string) =>
    s === "ended" ? "已结束" : s === "active" ? "进行中" : "未开始";

  useEffect(() => {
    Promise.all([fetchHealth(), fetchStartupStatus(), fetchAuthStatus()])
      .then(([healthData, startupData, authData]) => {
        setHealth(healthData);
        setStartup(startupData);
        setAuthStatus(authData);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  // Auto-logout when backend reports token expired (401)
  useEffect(() => {
    const onAuthExpired = () => {
      clearSession();
      setMessage("");
      setError("登录已过期，请重新登录");
    };
    window.addEventListener("auth:expired", onAuthExpired);
    return () => window.removeEventListener("auth:expired", onAuthExpired);
  }, [clearSession]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    Promise.all([
      fetchAccessInfo(),
      fetchAiOverview(),
      fetchAiFailureTasks(),
      fetchBackups(),
      fetchCourses(),
      fetchClasses(),
      fetchSessions(),
      fetchStudents(undefined, undefined, showInactiveStudents)
    ])
      .then(([accessData, aiData, aiTasks, backupData, courseData, classData, sessionData, studentData]) => {
        setAccessInfo(accessData);
        setSelectedIp(accessData.selected_ip);
        setSelectedPort(accessData.port);
        applyAiOverview(aiData);
        setAiFailureTaskCount(aiTasks.length);
        setBackups(backupData);
        setCourses(courseData);
        setClasses(classData);
        setSessions(sessionData);
        setStudents(studentData);
      })
      .catch((err: Error) => setError(err.message));
  }, [isAuthenticated, showInactiveStudents]);

  async function reloadAcademic() {
    const [courseData, classData, sessionData, studentData] = await Promise.all([
      fetchCourses(),
      fetchClasses(),
      fetchSessions(),
      fetchStudents(undefined, undefined, showInactiveStudents)
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

  function applyAiOverview(data: AiOverview) {
    setAiOverview(data);
    const provider = data.active_provider ?? data.providers[0];
    if (provider) {
      fillAiProviderForm(provider);
    }
    setAiSafetyMaxLength(data.safety.max_length);
    setAiSafetyKeywords(data.safety.blocked_keywords.join("\n"));
    setAiKeywordAction(data.safety.keyword_action);
    setAiDisplayStrategy(data.safety.display_strategy);
  }

  function fillAiProviderForm(provider: AiProvider) {
    setAiProviderId(provider.id);
    setAiProviderName(provider.provider_name);
    setAiDisplayName(provider.display_name);
    setAiBaseUrl(provider.base_url);
    setAiModelName(provider.model_name);
    setAiApiKey("");
    setAiHttpProxy(provider.http_proxy ?? "");
    setAiEnabled(provider.enabled);
  }

  async function reloadAiOverview() {
    const [overview, tasks] = await Promise.all([fetchAiOverview(), fetchAiFailureTasks()]);
    applyAiOverview(overview);
    setAiFailureTaskCount(tasks.length);
  }

  async function handleSaveAiProvider() {
    if (!aiProviderId) {
      setError("请选择要配置的 AI Provider");
      return;
    }
    try {
      await updateAiProvider(Number(aiProviderId), {
        provider_name: aiProviderName,
        display_name: aiDisplayName,
        base_url: aiBaseUrl,
        model_name: aiModelName,
        api_key: aiApiKey || undefined,
        http_proxy: aiHttpProxy || undefined,
        enabled: aiEnabled
      });
      await reloadAiOverview();
      setMessage("AI Provider 配置已保存");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleActivateAiProvider() {
    if (!aiProviderId) {
      setError("请选择要切换的 AI Provider");
      return;
    }
    try {
      await activateAiProvider(Number(aiProviderId));
      await reloadAiOverview();
      setMessage("AI Provider 已切换");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleCheckAiConnectivity() {
    try {
      const result = await checkAiConnectivity(aiProviderId ? Number(aiProviderId) : undefined);
      await reloadAiOverview();
      setMessage(result.message);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleSaveAiSafety() {
    try {
      await updateAiSafety({
        max_length: aiSafetyMaxLength === "" ? 2000 : Number(aiSafetyMaxLength),
        blocked_keywords: aiSafetyKeywords
          .split(/[,，;；\n]/)
          .map((item) => item.trim())
          .filter(Boolean),
        keyword_action: aiKeywordAction,
        display_strategy: aiDisplayStrategy
      });
      await reloadAiOverview();
      setMessage("AI 内容安全策略已保存");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleCheckAiSafety() {
    try {
      setAiSafetyResult(await checkAiSafety(aiSafetySample));
      setMessage("内容安全检查已完成");
    } catch (err) {
      setError((err as Error).message);
    }
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
    setUploading(true);
    setUploadError("");
    try {
      const job = await uploadStudentExcel(file);
      const suggested: Record<number, string> = {};
      job.headers.forEach((header, idx) => {
        const match = Object.entries(job.standard_fields).find(([, label]) =>
          header.includes(label) || label.includes(header)
        );
        if (match) {
          suggested[idx] = match[0];
        }
      });
      setImportJob(job);
      setFieldMapping(suggested);
      setImportPreview(null);
      setMessage("Excel 已解析");
    } catch (err) {
      const msg = (err as Error).message || "上传失败，请检查文件格式和网络连接";
      setError(msg);
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  }

  async function handlePreviewImport() {
    if (!importJob) {
      return;
    }
    setPreviewing(true);
    try {
      // Convert index-based mapping to {header: field} for backend
      const headerMapping: Record<string, string> = {};
      importJob.headers.forEach((header, idx) => {
        if (fieldMapping[idx]) {
          headerMapping[header] = fieldMapping[idx];
        }
      });
      setImportPreview(await previewStudentImport(importJob.job_id, headerMapping));
      setMessage("导入预览已生成");
      setConfirmError("");
    } catch (err: any) {
      setConfirmError(err.message || "预览生成失败");
    }
    setPreviewing(false);
  }

  async function handleSuggestImportMapping() {
    if (!importJob) {
      return;
    }
    try {
      const suggestion = await suggestStudentImportMapping(importJob.job_id);
      // Convert backend {header: field} format to index-based mapping
      const indexMapping: Record<number, string> = {};
      importJob.headers.forEach((header, idx) => {
        if (suggestion.mapping[header]) {
          indexMapping[idx] = suggestion.mapping[header];
        }
      });
      setFieldMapping(indexMapping);
      setMessage(suggestion.message);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleConfirmImport() {
    if (!importJob) {
      setConfirmError("请先上传 Excel 文件");
      return;
    }
    if (!selectedCourseId) {
      setConfirmError("请先在上方选择一个课程，再确认导入");
      return;
    }
    if (!importPreview) {
      setConfirmError("请先生成导入预览");
      return;
    }
    setConfirmError("");
    setConfirming(true);
    try {
      // Convert index-based mapping back to {header: field} for backend
      const headerMapping: Record<string, string> = {};
      importJob.headers.forEach((header, idx) => {
        if (fieldMapping[idx]) {
          headerMapping[header] = fieldMapping[idx];
        }
      });
      const result = await confirmStudentImport(
        importJob.job_id,
        Number(selectedCourseId),
        headerMapping,
        true,
        duplicateStrategy
      );
      await reloadAcademic();
      setMessage(`导入成功：新增 ${result.imported} 人，更新 ${result.updated} 人，跳过 ${result.skipped} 人`);
      setConfirming(false);
    } catch (err: any) {
      setConfirmError(err.message || "导入失败，请重试");
      setConfirming(false);
    }
  }

  async function handleDownloadImportErrors() {
    if (!importJob) {
      return;
    }
    try {
      await downloadImportErrors(importJob.job_id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleToggleStudentActive(student: Student) {
    try {
      await setStudentActive(student.id, !student.is_active);
      await reloadAcademic();
      setMessage(student.is_active ? "学生已停用" : "学生已启用");
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
      const [summary, logs, alerts] = await Promise.all([
        fetchSignInSummary(sessionId),
        fetchSignInLogs(sessionId),
        fetchDeviceAlerts(sessionId).catch(() => [] as DeviceSharingAlert[]),
      ]);
      setSignInSummary(summary);
      setSignInLogs(logs);
      setDeviceAlerts(alerts);
      setMessage(alerts.length > 0 ? `签到统计已刷新，发现 ${alerts.length} 条设备共用警告` : "签到统计已刷新");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleReviewAlert(alertId: number) {
    try {
      await reviewDeviceAlert(alertId);
      setDeviceAlerts((current) => current.map((a) => (a.id === alertId ? { ...a, reviewed: 1 } : a)));
      setMessage("警告已标记为已审核");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleUpdateSignIn(studentPk: number, status: "normal" | "late" | "absent" | "leave") {
    if (!signInSummary) {
      return;
    }
    try {
      setSignInSummary(await updateSignInStatus(signInSummary.session.id, studentPk, status, signInReason || undefined));
      setSignInLogs(await fetchSignInLogs(signInSummary.session.id));
      setMessage(status === "absent" ? "签到状态已改为缺勤" : status === "leave" ? "签到状态已改为请假" : "补签/状态修改已保存");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleDownloadSignIns() {
    if (!signInSummary) {
      return;
    }
    try {
      await downloadSignIns(signInSummary.session.id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadAnnouncements(sessionId: number) {
    try {
      setAnnouncementSessionId(sessionId);
      setAnnouncements(await fetchAnnouncements(sessionId));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handlePublishAnnouncement() {
    if (!announcementSessionId) {
      setError("请先选择课堂");
      return;
    }
    try {
      await publishAnnouncement(Number(announcementSessionId), announcementContent);
      setAnnouncementContent("");
      setAnnouncements(await fetchAnnouncements(Number(announcementSessionId)));
      setMessage("公告已发布");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadInteraction(sessionId: number) {
    try {
      setInteractionSessionId(sessionId);
      const [settings, messages] = await Promise.all([
        fetchInteractionSettings(sessionId),
        fetchInteractionMessages(sessionId)
      ]);
      setInteractionSettings(settings);
      setInteractionMessages(messages);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleToggleInteraction(enabled: boolean) {
    if (!interactionSessionId) {
      return;
    }
    try {
      setInteractionSettings(await updateInteractionSettings(Number(interactionSessionId), enabled));
      setMessage(enabled ? "已允许学生互动发言" : "已暂停学生互动发言");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handlePublishTeacherInteraction() {
    if (!interactionSessionId) {
      setError("请先选择互动课堂");
      return;
    }
    try {
      await publishTeacherInteractionMessage(Number(interactionSessionId), interactionContent);
      setInteractionContent("");
      setInteractionMessages(await fetchInteractionMessages(Number(interactionSessionId)));
      setMessage("课堂互动消息已发送");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadQuestions(sessionId: number) {
    try {
      setQuestionSessionId(sessionId);
      const [questionItems, settings, bonus] = await Promise.all([
        fetchQuestions(sessionId),
        fetchQuestionBonusSettings(),
        fetchQuestionBonusSummary(sessionId)
      ]);
      setQuestions(questionItems);
      setBonusSettings(settings);
      setBonusSummary(bonus);
      setQuestionStats(null);
      setAnonymousStats(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function updateQuestionOption(index: number, patch: Partial<QuestionOption>) {
    setQuestionOptions((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)));
  }

  function normalizedQuestionPayload() {
    const base = {
      title: questionTitle,
      content: questionContent,
      question_type: questionType,
      score: questionScore === "" ? 1 : Number(questionScore),
      deadline: questionDeadline || undefined
    };
    if (questionType === "fill_blank") {
      return {
        ...base,
        correct_answer: questionAnswer
          .split(/[,，;；\n]/)
          .map((item) => item.trim())
          .filter(Boolean),
        keywords: questionKeywords
          .split(/[,，;；\n]/)
          .map((item) => item.trim())
          .filter(Boolean)
      };
    }
    if (questionType === "short_answer") {
      return { ...base, correct_answer: questionAnswer };
    }
    if (questionType === "true_false") {
      return {
        ...base,
        options: [
          { option_key: "T", content: "正确", is_correct: questionAnswer === "T" },
          { option_key: "F", content: "错误", is_correct: questionAnswer === "F" }
        ],
        correct_answer: questionAnswer ? [questionAnswer] : []
      };
    }
    const options = questionOptions
      .filter((option) => option.content.trim())
      .map((option, index) => ({ ...option, display_order: index }));
    return {
      ...base,
      options,
      correct_answer: options.filter((option) => option.is_correct).map((option) => option.option_key)
    };
  }

  async function handlePublishQuestion() {
    if (!questionSessionId) {
      setError("请先选择课堂");
      return;
    }
    try {
      await publishQuestion(Number(questionSessionId), normalizedQuestionPayload());
      setQuestionTitle("");
      setQuestionContent("");
      setQuestionAnswer("");
      setQuestionKeywords("");
      setQuestionDeadline("");
      setQuestionOptions(DEFAULT_OPTIONS);
      setQuestions(await fetchQuestions(Number(questionSessionId)));
      setMessage("问题已发布");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadQuestionStats(questionId: number) {
    try {
      const [stats, anonymous] = await Promise.all([
        fetchQuestionStats(questionId),
        fetchAnonymousQuestionStats(questionId)
      ]);
      setQuestionStats(stats);
      setAnonymousStats(anonymous);
      setMessage("问答统计已刷新");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleSaveBonusSettings() {
    const payload = Object.fromEntries(
      Object.entries(bonusSettings).map(([key, value]) => [key, Number(value) || 0])
    );
    try {
      setBonusSettings(await updateQuestionBonusSettings(payload));
      if (questionSessionId) {
        setBonusSummary(await fetchQuestionBonusSummary(Number(questionSessionId)));
      }
      setMessage("问答加分规则已保存");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleDownloadQuestionAnswers() {
    if (!questionSessionId) {
      return;
    }
    try {
      await downloadQuestionAnswers(Number(questionSessionId));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadHomework(sessionId: number) {
    try {
      setHomeworkSessionId(sessionId);
      setHomeworkList(await fetchHomework(sessionId));
      setHomeworkSummary(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleCreateHomework() {
    if (!homeworkSessionId || !homeworkTitle || !homeworkDeadline) {
      setError("请先选择课堂，并填写作业标题和截止时间");
      return;
    }
    try {
      await createHomework(Number(homeworkSessionId), {
        title: homeworkTitle,
        description: homeworkDescription || undefined,
        deadline: homeworkDeadline,
        grading_criteria: homeworkCriteria || undefined,
        allow_late: homeworkAllowLate
      });
      setHomeworkTitle("");
      setHomeworkDescription("");
      setHomeworkDeadline("");
      setHomeworkCriteria("");
      setHomeworkAllowLate(false);
      setHomeworkList(await fetchHomework(Number(homeworkSessionId)));
      setMessage("作业已发布");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadHomeworkSummary(homeworkId: number) {
    try {
      setHomeworkSummary(await fetchHomeworkSubmissionSummary(homeworkId));
      setMessage("作业提交列表已刷新");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleAddHomeworkAttachments(homeworkId: number) {
    const files = homeworkAttachmentFiles[homeworkId] ?? [];
    if (!files.length) {
      setError("请先选择教师附件");
      return;
    }
    try {
      await addHomeworkAttachments(homeworkId, files);
      setHomeworkAttachmentFiles((current) => ({ ...current, [homeworkId]: [] }));
      if (homeworkSessionId) {
        setHomeworkList(await fetchHomework(Number(homeworkSessionId)));
      }
      setMessage("作业附件已上传");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleStartHomeworkAiReview(homeworkId: number) {
    try {
      const job = await startHomeworkAiReview(homeworkId);
      setHomeworkSummary(await fetchHomeworkSubmissionSummary(homeworkId));
      setMessage(String(job.message ?? "AI 批阅任务已处理"));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleReviewSubmission(submissionId: number, homeworkId: number) {
    const score = Number(reviewScores[submissionId]);
    if (!Number.isFinite(score)) {
      setError("请输入教师复核分数");
      return;
    }
    try {
      await reviewHomeworkSubmission(submissionId, score, reviewFeedback[submissionId] || undefined);
      setHomeworkSummary(await fetchHomeworkSubmissionSummary(homeworkId));
      setMessage("教师复核已保存");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handlePublishHomeworkGrades(homeworkId: number) {
    try {
      const result = await publishHomeworkGrades(homeworkId);
      setHomeworkSummary(await fetchHomeworkSubmissionSummary(homeworkId));
      setMessage(`已发布 ${result.published ?? 0} 份作业成绩`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleDownloadHomework(homeworkId: number) {
    try {
      await downloadHomeworkSubmissions(homeworkId);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleCalculateEvaluation(versionType: "temporary" | "final") {
    if (!evaluationSessionId) {
      setError("请先选择评估课堂");
      return;
    }
    try {
      const report = await calculateEvaluation(Number(evaluationSessionId), versionType);
      setEvaluationReport(report);
      setEvaluationWeights(pickEvaluationWeights(report.weights));
      setMessage(versionType === "final" ? "最终评估已生成" : "临时评估已生成");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadEvaluation(sessionId: number) {
    try {
      setEvaluationSessionId(sessionId);
      const report = await fetchEvaluationReport(sessionId);
      setEvaluationReport(report);
      if (Object.keys(report.weights).length) {
        setEvaluationWeights(pickEvaluationWeights(report.weights));
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleSaveEvaluationWeights() {
    const payload = Object.fromEntries(
      Object.entries(evaluationWeights).map(([key, value]) => [key, Number(value) || 0])
    );
    try {
      setEvaluationWeights(pickEvaluationWeights(await updateEvaluationWeights(payload)));
      setMessage("评估权重已保存");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleDownloadEvaluation() {
    if (!evaluationSessionId) {
      return;
    }
    try {
      await downloadEvaluationReport(Number(evaluationSessionId));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLoadRecoveryEvents(sessionId: number) {
    try {
      setRecoverySessionId(sessionId);
      setRecoveryEvents(await fetchRecoveryEvents(sessionId));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleRecordInterruption() {
    if (!recoverySessionId || !recoveryStartedAt || !recoveryEndedAt) {
      setError("请先选择课堂并填写中断起止时间");
      return;
    }
    try {
      await recordInterruption(Number(recoverySessionId), recoveryStartedAt, recoveryEndedAt);
      setRecoveryEvents(await fetchRecoveryEvents(Number(recoverySessionId)));
      setMessage("中断事件已记录");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleApplyRecovery(eventId: number, action: "extend_questions" | "reopen_sign_in") {
    if (!recoverySessionId) {
      return;
    }
    try {
      await applyRecoveryAction(Number(recoverySessionId), eventId, action);
      setRecoveryEvents(await fetchRecoveryEvents(Number(recoverySessionId)));
      setMessage(action === "extend_questions" ? "答题截止时间已延长" : "签到窗口已重新开放");
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

      {isAuthenticated && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "260px minmax(0, 1fr)" },
            gap: 2,
            alignItems: "start"
          }}
        >
          <Paper
            variant="outlined"
            sx={{
              position: { xs: "static", md: "sticky" },
              top: { md: 16 },
              p: 1,
              maxHeight: { md: "calc(100vh - 120px)" },
              overflow: "auto"
            }}
          >
            <Stack spacing={0.75}>
              {TEACHER_SECTIONS.map((section) => (
                <Button
                  key={section.key}
                  fullWidth
                  variant={activeTeacherSection === section.key ? "contained" : "text"}
                  onClick={() => setActiveTeacherSection(section.key)}
                  sx={{
                    justifyContent: "flex-start",
                    alignItems: "flex-start",
                    textAlign: "left",
                    py: 1,
                    px: 1.25,
                    minHeight: 58
                  }}
                >
                  <Box>
                    <Typography component="span" sx={{ display: "block", fontWeight: 700, lineHeight: 1.3 }}>
                      {section.label}
                    </Typography>
                    <Typography component="span" sx={{ display: "block", fontSize: "0.75rem", opacity: 0.78, lineHeight: 1.4 }}>
                      {section.description}
                    </Typography>
                  </Box>
                </Button>
              ))}
            </Stack>
          </Paper>

          <Stack spacing={3} sx={{ minWidth: 0 }}>

      {health && activeTeacherSection === "system" && (
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

      {startup && isAuthenticated && activeTeacherSection === "system" && (
        <Card>
          <CardContent>
            <Typography variant="h2">启动检查</Typography>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={1}>
              <Typography>数据库位置：{startup.database_path}</Typography>
              <Typography>U 盘路径识别：{startup.removable_root ?? "未配置"}</Typography>
              <Typography>本次迁移：{startup.migrations.length ? startup.migrations.join(", ") : "无"}</Typography>
              <Typography>初始化目录：{startup.directories.join("；")}</Typography>
              {startup.ai && (
                <Alert severity={startup.ai.status === "available" ? "success" : "info"}>
                  AI 启动自检：{startup.ai.message ?? startup.ai.status}
                </Alert>
              )}
            </Stack>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && activeTeacherSection === "ai" && aiOverview && (
        <Card>
          <CardContent>
            <Stack spacing={2.5}>
              <Box>
                <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap>
                  <PsychologyIcon color="primary" />
                  <Typography variant="h2">AI 管理与安全</Typography>
                  <Chip
                    size="small"
                    color={aiOverview.status === "available" ? "success" : "warning"}
                    label={aiOverview.status === "available" ? "AI 可用" : "基础模式"}
                  />
                </Stack>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  当前 Provider：{aiOverview.active_provider?.display_name ?? "未配置"}，待人工处理任务 {aiFailureTaskCount} 个。
                </Typography>
              </Box>

              {aiOverview.basic_mode && (
                <Alert severity="info">
                  AI 不可用时签到、答题提交、作业提交和统计继续可用；受影响功能：{aiOverview.affected_features.join("、")}。
                </Alert>
              )}

              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                    <Stack spacing={1.5}>
                      <Typography fontWeight={700}>Provider 配置</Typography>
                      <FormControl fullWidth>
                        <InputLabel id="ai-provider-label">Provider</InputLabel>
                        <Select
                          labelId="ai-provider-label"
                          label="Provider"
                          value={aiProviderId}
                          onChange={(event) => {
                            const provider = aiOverview.providers.find((item) => item.id === Number(event.target.value));
                            if (provider) {
                              fillAiProviderForm(provider);
                            }
                          }}
                        >
                          {aiOverview.providers.map((provider) => (
                            <MenuItem key={provider.id} value={provider.id}>
                              {provider.display_name} / {provider.last_status}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <TextField label="Provider 标识" value={aiProviderName} onChange={(event) => setAiProviderName(event.target.value)} />
                      <TextField label="显示名称" value={aiDisplayName} onChange={(event) => setAiDisplayName(event.target.value)} />
                      <TextField label="Base URL" value={aiBaseUrl} onChange={(event) => setAiBaseUrl(event.target.value)} />
                      <TextField label="模型名称" value={aiModelName} onChange={(event) => setAiModelName(event.target.value)} />
                      <TextField
                        label={aiOverview.providers.find((item) => item.id === aiProviderId)?.api_key_set ? "API Key（留空则保留原值）" : "API Key"}
                        type="password"
                        value={aiApiKey}
                        onChange={(event) => setAiApiKey(event.target.value)}
                      />
                      <TextField label="HTTP Proxy" value={aiHttpProxy} onChange={(event) => setAiHttpProxy(event.target.value)} />
                      <FormControlLabel
                        control={<Checkbox checked={aiEnabled} onChange={(event) => setAiEnabled(event.target.checked)} />}
                        label="启用此 Provider"
                      />
                      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                        <Button variant="contained" onClick={handleSaveAiProvider}>
                          保存配置
                        </Button>
                        <Button variant="outlined" onClick={handleActivateAiProvider}>
                          切换
                        </Button>
                        <Button variant="outlined" onClick={handleCheckAiConnectivity}>
                          自检
                        </Button>
                      </Stack>
                    </Stack>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={7}>
                  <Stack spacing={2}>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Stack spacing={1.5}>
                        <Typography fontWeight={700}>内容安全</Typography>
                        <Grid container spacing={1.5}>
                          <Grid item xs={12} sm={4}>
                            <TextField
                              label="最大长度"
                              type="number"
                              value={aiSafetyMaxLength}
                              onChange={(event) => setAiSafetyMaxLength(Number(event.target.value))}
                              fullWidth
                            />
                          </Grid>
                          <Grid item xs={12} sm={4}>
                            <FormControl fullWidth>
                              <InputLabel id="ai-keyword-action-label">敏感词处理</InputLabel>
                              <Select
                                labelId="ai-keyword-action-label"
                                label="敏感词处理"
                                value={aiKeywordAction}
                                onChange={(event) => setAiKeywordAction(event.target.value as "replace" | "block")}
                              >
                                <MenuItem value="replace">替换为 ***</MenuItem>
                                <MenuItem value="block">拦截展示</MenuItem>
                              </Select>
                            </FormControl>
                          </Grid>
                          <Grid item xs={12} sm={4}>
                            <FormControl fullWidth>
                              <InputLabel id="ai-display-strategy-label">展示策略</InputLabel>
                              <Select
                                labelId="ai-display-strategy-label"
                                label="展示策略"
                                value={aiDisplayStrategy}
                                onChange={(event) => setAiDisplayStrategy(event.target.value as "review_first" | "direct_with_report")}
                              >
                                <MenuItem value="review_first">教师审核后展示</MenuItem>
                                <MenuItem value="direct_with_report">直接展示并可举报</MenuItem>
                              </Select>
                            </FormControl>
                          </Grid>
                        </Grid>
                        <TextField
                          label="敏感关键词"
                          value={aiSafetyKeywords}
                          onChange={(event) => setAiSafetyKeywords(event.target.value)}
                          multiline
                          minRows={2}
                          fullWidth
                        />
                        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                          <Button variant="contained" onClick={handleSaveAiSafety}>
                            保存策略
                          </Button>
                          <TextField
                            label="测试文本"
                            value={aiSafetySample}
                            onChange={(event) => setAiSafetySample(event.target.value)}
                            size="small"
                            fullWidth
                          />
                          <Button variant="outlined" onClick={handleCheckAiSafety}>
                            检查
                          </Button>
                        </Stack>
                        {aiSafetyResult && (
                          <Alert severity={aiSafetyResult.blocked ? "warning" : "success"}>
                            {aiSafetyResult.message}；动作 {aiSafetyResult.action}；命中{" "}
                            {aiSafetyResult.matched_keywords.length ? aiSafetyResult.matched_keywords.join("、") : "无"}。
                            {aiSafetyResult.text ? ` 结果：${aiSafetyResult.text}` : ""}
                          </Alert>
                        )}
                      </Stack>
                    </Paper>

                    <Paper variant="outlined" sx={{ p: 2, overflow: "auto" }}>
                      <Typography fontWeight={700} sx={{ mb: 1 }}>
                        降级策略
                      </Typography>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>场景</TableCell>
                            <TableCell>正常模式</TableCell>
                            <TableCell>降级模式</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {aiOverview.degradation_strategies.map((strategy) => (
                            <TableRow key={strategy.scenario}>
                              <TableCell>{strategy.scenario}</TableCell>
                              <TableCell>{strategy.normal_mode}</TableCell>
                              <TableCell>{strategy.degraded_mode}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </Paper>
                  </Stack>
                </Grid>
              </Grid>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography fontWeight={700} sx={{ mb: 1 }}>
                  自检记录
                </Typography>
                <Stack spacing={0.75}>
                  {aiOverview.recent_checks.map((item) => (
                    <Typography key={item.id} color="text.secondary">
                      {item.checked_at} / {item.provider_display_name ?? "Provider"} / {item.status} / {item.message}
                    </Typography>
                  ))}
                  {aiOverview.recent_checks.length === 0 && <Typography color="text.secondary">暂无自检记录</Typography>}
                </Stack>
              </Paper>
            </Stack>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && activeTeacherSection === "preparation" && (
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
                    <Button component="label" variant="outlined" startIcon={uploading ? <CircularProgress size={18} color="inherit" /> : <UploadFileIcon />} disabled={uploading}>
                      {uploading ? "正在解析..." : "上传 .xlsx"}
                      <input
                        type="file"
                        hidden
                        accept=".xlsx,.xls"
                        onChange={(event) => handleExcelUpload(event.target.files?.[0] ?? null)}
                      />
                    </Button>
                    {uploadError && (
                      <Alert severity="error" sx={{ mt: 1 }}>{uploadError}</Alert>
                    )}
                    {importJob && (
                      <Alert severity="info">
                        {importJob.file_name}，共 {importJob.total_rows} 行数据
                      </Alert>
                    )}
                    {importJob && (
                      <Stack spacing={1}>
                        {importJob.headers.map((header, idx) => (
                          <FormControl key={`hdr-${idx}`} fullWidth size="small">
                            <InputLabel id={`mapping-${idx}`}>{header}</InputLabel>
                            <Select
                              labelId={`mapping-${idx}`}
                              label={header}
                              value={fieldMapping[idx] ?? ""}
                              onChange={(event) =>
                                setFieldMapping((current) => ({ ...current, [idx]: event.target.value }))
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
                        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                          <Button variant="outlined" startIcon={<PsychologyIcon />} onClick={handleSuggestImportMapping}>
                            AI 映射
                          </Button>
                          <Button variant="contained" onClick={handlePreviewImport} disabled={previewing} startIcon={previewing ? <CircularProgress size={16} color="inherit" /> : undefined}>
                            {previewing ? "生成中..." : "生成预览"}
                          </Button>
                        </Stack>
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
                        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems="flex-start">
                          <FormControl size="small" sx={{ minWidth: 160 }}>
                            <InputLabel id="duplicate-strategy-label">重复学号</InputLabel>
                            <Select
                              labelId="duplicate-strategy-label"
                              label="重复学号"
                              value={duplicateStrategy}
                              onChange={(event) => setDuplicateStrategy(event.target.value as "merge" | "overwrite" | "skip")}
                            >
                              <MenuItem value="merge">增量合并</MenuItem>
                              <MenuItem value="overwrite">覆盖更新</MenuItem>
                              <MenuItem value="skip">跳过重复</MenuItem>
                            </Select>
                          </FormControl>
                          <Button
                            variant="contained"
                            onClick={handleConfirmImport}
                            disabled={confirming || Boolean(importPreview?.error_count)}
                            startIcon={confirming ? <CircularProgress size={16} color="inherit" /> : undefined}
                          >
                            {confirming ? "正在导入..." : "确认导入有效数据"}
                          </Button>
                          {importPreview && importPreview.error_count > 0 && (
                            <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadImportErrors}>
                              错误报告
                            </Button>
                          )}
                        </Stack>
                        {confirmError && (
                          <Alert severity="error" sx={{ mt: 1 }}>
                            {confirmError}
                          </Alert>
                        )}
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
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                          <Typography fontWeight={500}>
                            第 {session.session_no} 次：{session.title}
                          </Typography>
                          <Chip
                            label={sessionStatusLabel(session.status)}
                            size="small"
                            color={session.status === "active" ? "success" : session.status === "ended" ? "default" : "warning"}
                            variant="outlined"
                          />
                        </Box>
                        <Typography color="text.secondary" variant="body2">
                          {session.course_name} / {session.class_name}
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
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={showInactiveStudents}
                        onChange={(event) => setShowInactiveStudents(event.target.checked)}
                      />
                    }
                    label="显示停用学生"
                  />
                  <Stack spacing={1}>
                    {students.slice(0, 8).map((student) => (
                      <Box key={student.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                        <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="center">
                          <Box>
                            <Typography>
                              {student.student_id} / {student.name}
                              {!student.is_active && <Chip size="small" color="default" label="已停用" sx={{ ml: 1 }} />}
                            </Typography>
                            <Typography color="text.secondary">{student.class_name}</Typography>
                          </Box>
                          <Button size="small" variant="outlined" onClick={() => handleToggleStudentActive(student)}>
                            {student.is_active ? "停用" : "启用"}
                          </Button>
                        </Stack>
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

      {isAuthenticated && activeTeacherSection === "evaluation" && (
        <Card>
          <CardContent>
            <Stack spacing={2.5}>
              <Box>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <AssessmentIcon color="primary" />
                  <Typography variant="h2">学习评估与恢复</Typography>
                </Stack>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  汇总签到、问答和作业形成课堂评估；记录课堂中断并应用延时或重新开放签到。
                </Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                    <Stack spacing={1.5}>
                      <Typography fontWeight={700}>学习效果评估</Typography>
                      <FormControl fullWidth>
                        <InputLabel id="evaluation-session-label">评估课堂</InputLabel>
                        <Select
                          labelId="evaluation-session-label"
                          label="评估课堂"
                          value={evaluationSessionId}
                          onChange={(event) => handleLoadEvaluation(Number(event.target.value))}
                        >
                          {sessions.map((session) => (
                            <MenuItem key={session.id} value={session.id}>
                              #{session.id} {session.course_name} / {session.title}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <Grid container spacing={1}>
                        {EVALUATION_WEIGHT_FIELDS.map((field) => (
                          <Grid item xs={6} sm={4} key={field.key}>
                            <TextField
                              size="small"
                              label={field.label}
                              type="number"
                              value={evaluationWeights[field.key]}
                              onChange={(event) =>
                                setEvaluationWeights((current) => ({ ...current, [field.key]: event.target.value }))
                              }
                              fullWidth
                            />
                          </Grid>
                        ))}
                      </Grid>
                      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                        <Button variant="outlined" onClick={handleSaveEvaluationWeights}>
                          保存权重
                        </Button>
                        <Button variant="contained" onClick={() => handleCalculateEvaluation("temporary")}>
                          临时评估
                        </Button>
                        <Button variant="outlined" onClick={() => handleCalculateEvaluation("final")}>
                          最终评估
                        </Button>
                        <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadEvaluation}>
                          导出
                        </Button>
                      </Stack>
                      {evaluationReport && (
                        <Paper variant="outlined" sx={{ p: 1.5, maxHeight: 260, overflow: "auto" }}>
                          <Typography fontWeight={700}>
                            {evaluationReport.version_type ?? "未生成"} v{evaluationReport.version_no ?? "-"}
                          </Typography>
                          <Typography color="text.secondary">
                            共 {evaluationReport.summary.total ?? 0} 人，平均分 {evaluationReport.summary.average_score ?? 0}，
                            出勤率 {evaluationReport.summary.attendance_rate ?? 0}%
                          </Typography>
                          <Stack spacing={0.5} sx={{ mt: 1 }}>
                            {evaluationReport.records.slice(0, 8).map((record) => (
                              <Typography key={String(record.student_id)} variant="body2" color="text.secondary">
                                {String(record.student_number)} {String(record.student_name)}：{String(record.total_score)} /{" "}
                                {String(record.level)}
                              </Typography>
                            ))}
                          </Stack>
                        </Paper>
                      )}
                    </Stack>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                    <Stack spacing={1.5}>
                      <Typography fontWeight={700}>中断恢复</Typography>
                      <FormControl fullWidth>
                        <InputLabel id="recovery-session-label">恢复课堂</InputLabel>
                        <Select
                          labelId="recovery-session-label"
                          label="恢复课堂"
                          value={recoverySessionId}
                          onChange={(event) => handleLoadRecoveryEvents(Number(event.target.value))}
                        >
                          {sessions.map((session) => (
                            <MenuItem key={session.id} value={session.id}>
                              #{session.id} {session.course_name} / {session.title}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                        <TextField
                          label="中断开始"
                          type="datetime-local"
                          value={recoveryStartedAt}
                          onChange={(event) => setRecoveryStartedAt(event.target.value)}
                          InputLabelProps={{ shrink: true }}
                          fullWidth
                        />
                        <TextField
                          label="中断结束"
                          type="datetime-local"
                          value={recoveryEndedAt}
                          onChange={(event) => setRecoveryEndedAt(event.target.value)}
                          InputLabelProps={{ shrink: true }}
                          fullWidth
                        />
                      </Stack>
                      <Button variant="contained" startIcon={<RestoreIcon />} onClick={handleRecordInterruption}>
                        记录中断
                      </Button>
                      <Paper variant="outlined" sx={{ p: 1.5, maxHeight: 260, overflow: "auto" }}>
                        <Stack spacing={1}>
                          {recoveryEvents.map((event) => (
                            <Box key={String(event.id)} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                              <Typography fontWeight={700}>
                                #{String(event.id)} {String(event.event_type)} / {String(event.duration_seconds ?? 0)} 秒
                              </Typography>
                              <Typography color="text.secondary" variant="body2">
                                {String(event.started_at ?? event.created_at ?? "")} {String(event.action_taken ?? "")}
                              </Typography>
                              {event.event_type === "interruption" && (
                                <Stack direction="row" spacing={1} sx={{ mt: 0.75 }}>
                                  <Button size="small" variant="outlined" onClick={() => handleApplyRecovery(Number(event.id), "extend_questions")}>
                                    延长答题
                                  </Button>
                                  <Button size="small" variant="outlined" onClick={() => handleApplyRecovery(Number(event.id), "reopen_sign_in")}>
                                    重开签到
                                  </Button>
                                </Stack>
                              )}
                            </Box>
                          ))}
                          {recoveryEvents.length === 0 && <Typography color="text.secondary">暂无中断或重放记录。</Typography>}
                        </Stack>
                      </Paper>
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>
            </Stack>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && activeTeacherSection === "classroom" && (
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
                            {signInSummary.stats.late}，请假 {signInSummary.stats.leave}，缺勤 {signInSummary.stats.absent}，未处理{" "}
                            {signInSummary.stats.unsigned}
                          </Typography>
                        </Box>
                        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                          <TextField
                            size="small"
                            label="调整原因"
                            value={signInReason}
                            onChange={(event) => setSignInReason(event.target.value)}
                            fullWidth
                          />
                          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadSignIns}>
                            导出
                          </Button>
                        </Stack>
                        <Paper variant="outlined" sx={{ maxHeight: 320, overflow: "auto" }}>
                          <Table size="small" stickyHeader>
                            <TableHead>
                              <TableRow>
                                <TableCell>学号</TableCell>
                                <TableCell>姓名</TableCell>
                                <TableCell>状态</TableCell>
                                <TableCell>时间</TableCell>
                                <TableCell>调整</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {signInSummary.records.map((record) => (
                                <TableRow key={record.student_pk}>
                                  <TableCell>{record.student_number}</TableCell>
                                  <TableCell>{record.student_name}</TableCell>
                                  <TableCell>{record.status ? SIGN_IN_STATUS_LABELS[record.status] ?? record.status : "未签到"}</TableCell>
                                  <TableCell>{record.sign_time ?? "-"}</TableCell>
                                  <TableCell>
                                    <Stack direction="row" spacing={0.5}>
                                      <Button size="small" onClick={() => handleUpdateSignIn(record.student_pk, "normal")}>
                                        补签
                                      </Button>
                                      <Button size="small" onClick={() => handleUpdateSignIn(record.student_pk, "late")}>
                                        迟到
                                      </Button>
                                      <Button size="small" color="warning" onClick={() => handleUpdateSignIn(record.student_pk, "absent")}>
                                        缺勤
                                      </Button>
                                      <Button size="small" color="info" onClick={() => handleUpdateSignIn(record.student_pk, "leave")}>
                                        请假
                                      </Button>
                                    </Stack>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </Paper>
                        <Paper variant="outlined" sx={{ p: 1.5, maxHeight: 160, overflow: "auto" }}>
                          <Typography fontWeight={700} sx={{ mb: 1 }}>
                            修改日志
                          </Typography>
                          <Stack spacing={0.5}>
                            {signInLogs.map((log) => (
                              <Typography key={String(log.id)} variant="body2" color="text.secondary">
                                {String(log.created_at)} / {String(log.student_number)} {String(log.student_name)}：
                                {String(log.previous_status ? SIGN_IN_STATUS_LABELS[String(log.previous_status)] ?? log.previous_status : "未签到")}{" "}
                                {"->"} {String(SIGN_IN_STATUS_LABELS[String(log.new_status)] ?? log.new_status)} / {String(log.reason ?? "")}
                              </Typography>
                            ))}
                            {signInLogs.length === 0 && <Typography color="text.secondary">暂无手动调整记录。</Typography>}
                          </Stack>
                        </Paper>
                        {deviceAlerts.length > 0 && (
                          <Paper variant="outlined" sx={{ p: 1.5, borderColor: "warning.main", bgcolor: "warning.50" }}>
                            <Stack spacing={1}>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <WarningAmberIcon color="warning" fontSize="small" />
                                <Typography fontWeight={700} color="warning.dark">
                                  设备共用警告
                                </Typography>
                              </Stack>
                              {deviceAlerts.filter((a) => !a.reviewed).length > 0 && (
                                <Alert severity="warning" sx={{ py: 0 }}>
                                  发现 {deviceAlerts.filter((a) => !a.reviewed).length} 条未审核的设备共用记录，可能存在替签到行为
                                </Alert>
                              )}
                              {deviceAlerts.map((alert) => (
                                <Box key={alert.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                                  <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" useFlexGap>
                                    <Typography variant="body2" fontWeight={600}>
                                      {alert.alert_level === "critical" ? "🔴 " : "🟡 "}
                                      {alert.student_count} 人共用设备
                                    </Typography>
                                    <Stack direction="row" spacing={0.5} alignItems="center">
                                      <Chip
                                        size="small"
                                        color={alert.reviewed ? "default" : "warning"}
                                        label={alert.reviewed ? "已审核" : "待审核"}
                                      />
                                      {!alert.reviewed && (
                                        <Button size="small" variant="outlined" onClick={() => handleReviewAlert(alert.id)}>
                                          标记已审核
                                        </Button>
                                      )}
                                    </Stack>
                                  </Stack>
                                  <Typography variant="body2" color="text.secondary">
                                    学生：{alert.student_list || (Array.isArray(alert.student_ids) ? alert.student_ids.join(", ") : alert.student_ids_json)}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {alert.created_at} / 设备标识：{(alert.device_hash || "").substring(0, 16)}...
                                  </Typography>
                                </Box>
                              ))}
                            </Stack>
                          </Paper>
                        )}
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

      {isAuthenticated && activeTeacherSection === "system" && accessInfo && (
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

      {isAuthenticated && activeTeacherSection === "questions" && (
        <Card>
          <CardContent>
            <Stack spacing={2.5}>
              <Box>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <QuizIcon color="primary" />
                  <Typography variant="h2">课堂问答</Typography>
                </Stack>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  发布课堂题目，学生在线作答后可查看提交和正确率统计。
                </Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <Stack spacing={1.5}>
                    <FormControl fullWidth>
                      <InputLabel id="question-session-label">问答课堂</InputLabel>
                      <Select
                        labelId="question-session-label"
                        label="问答课堂"
                        value={questionSessionId}
                        onChange={(event) => handleLoadQuestions(Number(event.target.value))}
                      >
                        {sessions.map((session) => (
                          <MenuItem key={session.id} value={session.id}>
                            #{session.id} {session.course_name} / {session.title} / {sessionStatusLabel(session.status)}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                      <FormControl fullWidth>
                        <InputLabel id="question-type-label">题型</InputLabel>
                        <Select
                          labelId="question-type-label"
                          label="题型"
                          value={questionType}
                          onChange={(event) => {
                            const nextType = event.target.value as QuestionType;
                            setQuestionType(nextType);
                            setQuestionAnswer("");
                            setQuestionOptions(nextType === "true_false" ? [] : DEFAULT_OPTIONS);
                          }}
                        >
                          {Object.entries(QUESTION_TYPE_LABELS).map(([value, label]) => (
                            <MenuItem key={value} value={value}>
                              {label}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <TextField
                        label="分值"
                        type="number"
                        value={questionScore}
                        onChange={(event) => setQuestionScore(event.target.value === "" ? "" : Number(event.target.value))}
                        fullWidth
                      />
                    </Stack>
                    <TextField
                      label="题目标题"
                      value={questionTitle}
                      onChange={(event) => setQuestionTitle(event.target.value)}
                      fullWidth
                    />
                    <TextField
                      label="题干"
                      value={questionContent}
                      onChange={(event) => setQuestionContent(event.target.value)}
                      multiline
                      minRows={3}
                      fullWidth
                    />
                    <TextField
                      label="截止时间"
                      type="datetime-local"
                      value={questionDeadline}
                      onChange={(event) => setQuestionDeadline(event.target.value)}
                      InputLabelProps={{ shrink: true }}
                      fullWidth
                    />

                    {questionType === "true_false" && (
                      <FormControl fullWidth>
                        <InputLabel id="true-false-answer-label">正确答案</InputLabel>
                        <Select
                          labelId="true-false-answer-label"
                          label="正确答案"
                          value={questionAnswer}
                          onChange={(event) => setQuestionAnswer(event.target.value)}
                        >
                          <MenuItem value="T">正确</MenuItem>
                          <MenuItem value="F">错误</MenuItem>
                        </Select>
                      </FormControl>
                    )}

                    {(questionType === "single_choice" || questionType === "multiple_choice") && (
                      <Stack spacing={1}>
                        {questionOptions.map((option, index) => (
                          <Stack key={option.option_key} direction="row" spacing={1} alignItems="center">
                            <FormControlLabel
                              control={
                                <Checkbox
                                  checked={Boolean(option.is_correct)}
                                  onChange={(event) => {
                                    if (questionType === "single_choice") {
                                      setQuestionOptions((current) =>
                                        current.map((item, itemIndex) => ({
                                          ...item,
                                          is_correct: itemIndex === index ? event.target.checked : false
                                        }))
                                      );
                                    } else {
                                      updateQuestionOption(index, { is_correct: event.target.checked });
                                    }
                                  }}
                                />
                              }
                              label={option.option_key}
                              sx={{ minWidth: 72 }}
                            />
                            <TextField
                              label="选项内容"
                              value={option.content}
                              onChange={(event) => updateQuestionOption(index, { content: event.target.value })}
                              fullWidth
                            />
                          </Stack>
                        ))}
                      </Stack>
                    )}

                    {questionType === "fill_blank" && (
                      <>
                        <TextField
                          label="标准答案"
                          value={questionAnswer}
                          onChange={(event) => setQuestionAnswer(event.target.value)}
                          helperText="多个答案可用逗号、分号或换行分隔"
                          multiline
                          minRows={2}
                          fullWidth
                        />
                        <TextField
                          label="关键词"
                          value={questionKeywords}
                          onChange={(event) => setQuestionKeywords(event.target.value)}
                          helperText="设置后答案需包含全部关键词"
                          fullWidth
                        />
                      </>
                    )}

                    {questionType === "short_answer" && (
                      <TextField
                        label="参考答案"
                        value={questionAnswer}
                        onChange={(event) => setQuestionAnswer(event.target.value)}
                        multiline
                        minRows={2}
                        fullWidth
                      />
                    )}

                    <Button variant="contained" startIcon={<SendIcon />} onClick={handlePublishQuestion}>
                      发布问题
                    </Button>
                  </Stack>
                </Grid>

                <Grid item xs={12} md={7}>
                  <Stack spacing={1.5}>
                    {questionSessionId && (
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Stack spacing={1.5}>
                          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
                            <Typography fontWeight={700}>加分与导出</Typography>
                            <Button size="small" variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadQuestionAnswers}>
                              答案导出
                            </Button>
                          </Stack>
                          <Grid container spacing={1}>
                            {Object.entries(bonusSettings).map(([key, value]) => (
                              <Grid item xs={6} sm={4} key={key}>
                                <TextField
                                  size="small"
                                  label={key}
                                  type="number"
                                  value={value}
                                  onChange={(event) =>
                                    setBonusSettings((current) => ({ ...current, [key]: event.target.value }))
                                  }
                                  fullWidth
                                />
                              </Grid>
                            ))}
                          </Grid>
                          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                            <Button variant="outlined" onClick={handleSaveBonusSettings}>
                              保存加分规则
                            </Button>
                            <Button
                              variant="outlined"
                              onClick={async () => setBonusSummary(await fetchQuestionBonusSummary(Number(questionSessionId)))}
                            >
                              刷新加分
                            </Button>
                          </Stack>
                          {bonusSummary && (
                            <Stack spacing={0.5}>
                              {bonusSummary.records.slice(0, 5).map((record) => (
                                <Typography key={String(record.student_number)} variant="body2" color="text.secondary">
                                  {String(record.student_number)} {String(record.student_name)}：{String(record.total_score ?? 0)} 分
                                </Typography>
                              ))}
                              {bonusSummary.records.length === 0 && <Typography color="text.secondary">暂无加分记录。</Typography>}
                            </Stack>
                          )}
                        </Stack>
                      </Paper>
                    )}
                    <Paper variant="outlined" sx={{ p: 2, minHeight: 220 }}>
                      <Stack spacing={1.5}>
                        {questions.map((item) => (
                          <Box key={item.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
                              <Box>
                                <Typography fontWeight={700}>{item.title}</Typography>
                                <Typography color="text.secondary" variant="body2">
                                  {QUESTION_TYPE_LABELS[item.question_type]} / {item.status}
                                  {item.deadline ? ` / 截止 ${item.deadline}` : ""}
                                </Typography>
                              </Box>
                              <Button size="small" variant="outlined" onClick={() => handleLoadQuestionStats(item.id)}>
                                统计
                              </Button>
                            </Stack>
                          </Box>
                        ))}
                        {questions.length === 0 && (
                          <Typography color="text.secondary">选择课堂后可查看已发布问题。</Typography>
                        )}
                      </Stack>
                    </Paper>

                    <Paper variant="outlined" sx={{ p: 2, minHeight: 220 }}>
                      {questionStats ? (
                        <Stack spacing={1.5}>
                          <Box>
                            <Typography fontWeight={700}>{questionStats.question.title}</Typography>
                            <Typography color="text.secondary">
                              应答 {questionStats.total_students} 人，已交 {questionStats.submitted_count}，正确{" "}
                              {questionStats.correct_count}，正确率 {questionStats.correct_rate}%
                            </Typography>
                          </Box>
                          {Object.keys(questionStats.option_distribution).length > 0 && (
                            <Stack spacing={0.5}>
                              {Object.entries(questionStats.option_distribution).map(([key, count]) => (
                                <Typography key={key}>
                                  选项 {key}：{count} 人
                                </Typography>
                              ))}
                            </Stack>
                          )}
                          {anonymousStats && (
                            <Alert severity="info">
                              匿名统计：已提交 {String(anonymousStats.submitted_count ?? 0)} 人，正确率{" "}
                              {String(anonymousStats.correct_rate ?? 0)}%。
                            </Alert>
                          )}
                          {questionStats.typical_answers.length > 0 && (
                            <Stack spacing={0.5}>
                              {questionStats.typical_answers.map((item) => (
                                <Typography key={item.answer}>
                                  {item.answer}：{item.count} 次
                                </Typography>
                              ))}
                            </Stack>
                          )}
                        </Stack>
                      ) : (
                        <Typography color="text.secondary">点击问题右侧统计查看提交、正确率和答案分布。</Typography>
                      )}
                    </Paper>
                  </Stack>
                </Grid>
              </Grid>
            </Stack>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && activeTeacherSection === "homework" && (
        <Card>
          <CardContent>
            <Stack spacing={2.5}>
              <Box>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <AssignmentIcon color="primary" />
                  <Typography variant="h2">课堂作业</Typography>
                </Stack>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  发布课堂作业，学生可提交文本和附件，教师可查看提交状态与最新版本。
                </Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <Stack spacing={1.5}>
                    <FormControl fullWidth>
                      <InputLabel id="homework-session-label">作业课堂</InputLabel>
                      <Select
                        labelId="homework-session-label"
                        label="作业课堂"
                        value={homeworkSessionId}
                        onChange={(event) => handleLoadHomework(Number(event.target.value))}
                      >
                        {sessions.map((session) => (
                          <MenuItem key={session.id} value={session.id}>
                            #{session.id} {session.course_name} / {session.title} / {sessionStatusLabel(session.status)}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <TextField
                      label="作业标题"
                      value={homeworkTitle}
                      onChange={(event) => setHomeworkTitle(event.target.value)}
                      fullWidth
                    />
                    <TextField
                      label="作业说明"
                      value={homeworkDescription}
                      onChange={(event) => setHomeworkDescription(event.target.value)}
                      multiline
                      minRows={3}
                      fullWidth
                    />
                    <TextField
                      label="截止时间"
                      type="datetime-local"
                      value={homeworkDeadline}
                      onChange={(event) => setHomeworkDeadline(event.target.value)}
                      InputLabelProps={{ shrink: true }}
                      fullWidth
                    />
                    <TextField
                      label="评分标准"
                      value={homeworkCriteria}
                      onChange={(event) => setHomeworkCriteria(event.target.value)}
                      multiline
                      minRows={2}
                      fullWidth
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={homeworkAllowLate}
                          onChange={(event) => setHomeworkAllowLate(event.target.checked)}
                        />
                      }
                      label="允许截止后迟交"
                    />
                    <Button variant="contained" startIcon={<AssignmentIcon />} onClick={handleCreateHomework}>
                      发布作业
                    </Button>
                  </Stack>
                </Grid>

                <Grid item xs={12} md={7}>
                  <Stack spacing={1.5}>
                    <Paper variant="outlined" sx={{ p: 2, minHeight: 220 }}>
                      <Stack spacing={1.5}>
                        {homeworkList.map((item) => (
                          <Box key={item.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
                              <Box>
                                <Typography fontWeight={700}>{item.title}</Typography>
                                <Typography color="text.secondary" variant="body2">
                                  {item.status} / 截止 {item.deadline}
                                  {item.allow_late ? " / 允许迟交" : ""}
                                </Typography>
                                <Typography color="text.secondary" variant="body2">
                                  教师附件：{item.attachments?.length ?? 0} 个
                                </Typography>
                              </Box>
                              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                                <Button component="label" size="small" variant="outlined">
                                  附件
                                  <input
                                    type="file"
                                    multiple
                                    hidden
                                    onChange={(event) =>
                                      setHomeworkAttachmentFiles((current) => ({
                                        ...current,
                                        [item.id]: event.target.files ? Array.from(event.target.files) : []
                                      }))
                                    }
                                  />
                                </Button>
                                <Button size="small" variant="outlined" onClick={() => handleAddHomeworkAttachments(item.id)}>
                                  上传
                                </Button>
                                <Button size="small" variant="outlined" onClick={() => handleLoadHomeworkSummary(item.id)}>
                                  提交列表
                                </Button>
                              </Stack>
                            </Stack>
                            {(homeworkAttachmentFiles[item.id]?.length ?? 0) > 0 && (
                              <Typography color="text.secondary" variant="body2" sx={{ mt: 0.75 }}>
                                待上传：{homeworkAttachmentFiles[item.id].map((file) => file.name).join("，")}
                              </Typography>
                            )}
                          </Box>
                        ))}
                        {homeworkList.length === 0 && (
                          <Typography color="text.secondary">选择课堂后可查看已发布作业。</Typography>
                        )}
                      </Stack>
                    </Paper>

                    <Paper variant="outlined" sx={{ p: 2, minHeight: 260, overflow: "auto" }}>
                      {homeworkSummary ? (
                        <Stack spacing={1.5}>
                          <Box>
                            <Typography fontWeight={700}>{homeworkSummary.homework.title}</Typography>
                            <Typography color="text.secondary">
                              应交 {homeworkSummary.stats.total} 人，已交 {homeworkSummary.stats.submitted}，未交{" "}
                              {homeworkSummary.stats.not_submitted}，迟交 {homeworkSummary.stats.late}
                            </Typography>
                          </Box>
                          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                            <Button variant="outlined" startIcon={<PsychologyIcon />} onClick={() => handleStartHomeworkAiReview(homeworkSummary.homework.id)}>
                              AI 批阅
                            </Button>
                            <Button variant="outlined" onClick={() => handlePublishHomeworkGrades(homeworkSummary.homework.id)}>
                              发布成绩
                            </Button>
                            <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => handleDownloadHomework(homeworkSummary.homework.id)}>
                              导出
                            </Button>
                          </Stack>
                          <Table size="small" stickyHeader>
                            <TableHead>
                              <TableRow>
                                <TableCell>学号</TableCell>
                                <TableCell>姓名</TableCell>
                                <TableCell>状态</TableCell>
                                <TableCell>版本</TableCell>
                                <TableCell>提交时间</TableCell>
                                <TableCell>评分</TableCell>
                                <TableCell>内容/附件</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {homeworkSummary.records.map((record) => (
                                <TableRow key={record.student_pk}>
                                  <TableCell>{record.student_number}</TableCell>
                                  <TableCell>{record.student_name}</TableCell>
                                  <TableCell>{record.submission_status}</TableCell>
                                  <TableCell>{record.submit_version ?? "-"}</TableCell>
                                  <TableCell>{record.submitted_at ?? "-"}</TableCell>
                                  <TableCell sx={{ minWidth: 220 }}>
                                    {record.submission_id ? (
                                      <Stack spacing={1}>
                                        <Typography variant="body2" color="text.secondary">
                                          AI {record.ai_score ?? "-"} / 最终 {record.final_score ?? "-"}
                                        </Typography>
                                        <TextField
                                          size="small"
                                          label="复核分"
                                          type="number"
                                          value={reviewScores[record.submission_id] ?? record.final_score ?? record.ai_score ?? ""}
                                          onChange={(event) =>
                                            setReviewScores((current) => ({ ...current, [record.submission_id as number]: event.target.value }))
                                          }
                                        />
                                        <TextField
                                          size="small"
                                          label="反馈"
                                          value={reviewFeedback[record.submission_id] ?? record.final_feedback ?? ""}
                                          onChange={(event) =>
                                            setReviewFeedback((current) => ({
                                              ...current,
                                              [record.submission_id as number]: event.target.value
                                            }))
                                          }
                                        />
                                        <Button
                                          size="small"
                                          variant="outlined"
                                          onClick={() => handleReviewSubmission(record.submission_id as number, homeworkSummary.homework.id)}
                                        >
                                          保存复核
                                        </Button>
                                      </Stack>
                                    ) : (
                                      "-"
                                    )}
                                  </TableCell>
                                  <TableCell sx={{ minWidth: 220 }}>
                                    <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                                      {record.text_content || "-"}
                                    </Typography>
                                    {record.files.length > 0 && (
                                      <Stack spacing={0.25} sx={{ mt: 0.75 }}>
                                        {record.files.map((file) => (
                                          <Typography key={`${record.submission_id}-${file.original_name}`} variant="body2" color="text.secondary">
                                            {file.original_name} ({Math.ceil(file.file_size / 1024)} KB)
                                          </Typography>
                                        ))}
                                      </Stack>
                                    )}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </Stack>
                      ) : (
                        <Typography color="text.secondary">点击作业右侧提交列表查看学生提交状态。</Typography>
                      )}
                    </Paper>
                  </Stack>
                </Grid>
              </Grid>
            </Stack>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && activeTeacherSection === "announcements" && (
        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Box>
                <Typography variant="h2">课堂公告</Typography>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  公告会先保存到本地数据库，再实时推送给当前课堂在线学生。
                </Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <Stack spacing={1.5}>
                    <FormControl fullWidth>
                      <InputLabel id="announcement-session-label">公告课堂</InputLabel>
                      <Select
                        labelId="announcement-session-label"
                        label="公告课堂"
                        value={announcementSessionId}
                        onChange={(event) => handleLoadAnnouncements(Number(event.target.value))}
                      >
                        {sessions.map((session) => (
                          <MenuItem key={session.id} value={session.id}>
                            #{session.id} {session.course_name} / {session.title}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <TextField
                      label="公告内容"
                      value={announcementContent}
                      onChange={(event) => setAnnouncementContent(event.target.value)}
                      multiline
                      minRows={4}
                      helperText={`${announcementContent.length}/500`}
                      inputProps={{ maxLength: 500 }}
                      fullWidth
                    />
                    <Button variant="contained" onClick={handlePublishAnnouncement}>
                      发布公告
                    </Button>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={7}>
                  <Paper variant="outlined" sx={{ p: 2, minHeight: 220 }}>
                    <Stack spacing={1.5}>
                      {announcements.map((item) => (
                        <Box key={item.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                          <Typography>{item.content}</Typography>
                          <Typography color="text.secondary" variant="body2">
                            {item.sender_name} / {item.created_at}
                          </Typography>
                        </Box>
                      ))}
                      {announcements.length === 0 && (
                        <Typography color="text.secondary">选择课堂后可查看历史公告。</Typography>
                      )}
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>
            </Stack>
          </CardContent>
        </Card>
      )}

      {isAuthenticated && activeTeacherSection === "interaction" && (
        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Box>
                <Typography variant="h2">课堂互动</Typography>
                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  学生完成正常或迟到签到后可发言；教师可随时暂停学生发言。
                </Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <Stack spacing={1.5}>
                    <FormControl fullWidth>
                      <InputLabel id="interaction-session-label">互动课堂</InputLabel>
                      <Select
                        labelId="interaction-session-label"
                        label="互动课堂"
                        value={interactionSessionId}
                        onChange={(event) => handleLoadInteraction(Number(event.target.value))}
                      >
                        {sessions.map((session) => (
                          <MenuItem key={session.id} value={session.id}>
                            #{session.id} {session.course_name} / {session.title}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={Boolean(interactionSettings?.student_messages_enabled ?? true)}
                          disabled={!interactionSessionId}
                          onChange={(event) => handleToggleInteraction(event.target.checked)}
                        />
                      }
                      label="允许学生互动发言"
                    />
                    <TextField
                      label="教师互动消息"
                      value={interactionContent}
                      onChange={(event) => setInteractionContent(event.target.value)}
                      multiline
                      minRows={3}
                      helperText={`${interactionContent.length}/300`}
                      inputProps={{ maxLength: 300 }}
                      fullWidth
                    />
                    <Button variant="contained" onClick={handlePublishTeacherInteraction}>
                      发送互动消息
                    </Button>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={7}>
                  <Paper variant="outlined" sx={{ p: 2, minHeight: 260, maxHeight: 360, overflow: "auto" }}>
                    <Stack spacing={1.5}>
                      {interactionMessages.map((item) => (
                        <Box key={item.id} sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}>
                          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                            <Chip size="small" label={item.sender_role === "teacher" ? "教师" : "学生"} color={item.sender_role === "teacher" ? "primary" : "default"} />
                            <Typography fontWeight={700}>{item.sender_name}</Typography>
                            <Typography color="text.secondary" variant="body2">
                              {item.created_at}
                            </Typography>
                          </Stack>
                          <Typography sx={{ mt: 0.75, whiteSpace: "pre-wrap" }}>{item.content}</Typography>
                        </Box>
                      ))}
                      {interactionMessages.length === 0 && (
                        <Typography color="text.secondary">选择课堂后可查看互动留言。</Typography>
                      )}
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>
            </Stack>
          </CardContent>
        </Card>
      )}

          </Stack>
        </Box>
      )}

      <AppSnackbar open={Boolean(message)} message={message} severity="success" onClose={() => setMessage("")} />
    </Stack>
  );
}
