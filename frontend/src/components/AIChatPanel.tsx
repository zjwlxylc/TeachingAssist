import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweep";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { chatWithAi, studentChatWithAi, type AiChatMessage } from "../api/ai";

interface AIChatPanelProps {
  role: "teacher" | "student";
  sessionId: number;
  courseName?: string;
  studentId?: string;
  studentName?: string;
}

interface ChatTurn extends AiChatMessage {
  role: "user" | "assistant";
  content: string;
  guarded?: boolean;
}

export function AIChatPanel({
  role,
  sessionId,
  courseName,
  studentId,
  studentName
}: AIChatPanelProps) {
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend() {
    const userContent = input.trim();
    if (!userContent || loading) return;
    const nextMessages: ChatTurn[] = [...messages, { role: "user", content: userContent }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError("");
    try {
      const payloadMessages = nextMessages.map(({ role, content }) => ({ role, content }));
      const result =
        role === "student"
          ? await studentChatWithAi(sessionId, studentId ?? "", studentName ?? "", payloadMessages)
          : await chatWithAi(sessionId, payloadMessages);
      setMessages([
        ...nextMessages,
        { role: "assistant", content: result.reply, guarded: result.guarded }
      ]);
    } catch (err) {
      setError((err as Error).message || "AI 课堂请求失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setMessages([]);
    setInput("");
    setError("");
  }

  function handleKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  }

  return (
    <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 2, height: "100%" }}>
      {/* 左侧提示栏 */}
      <Paper
        variant="outlined"
        sx={{
          width: { md: 210 },
          p: 1.5,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          gap: 1,
          bgcolor: "info.50",
          maxHeight: { md: "100%" },
          overflow: "auto"
        }}
      >
        <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 700 }}>
          💡 AI 课堂
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", lineHeight: 1.7 }}>
          可以问我：
        </Typography>
        {[
          "课程知识（概念、例题）",
          "本课堂公告 / 作业要求",
          "练习题相关问题",
          "签到情况",
          "作业提交与成绩",
          "答题与判分",
          "学习评估反馈",
        ].map((item) => (
          <Box key={item} sx={{ pl: 1 }}>
            <Typography variant="body2" sx={{ color: "text.secondary", lineHeight: 1.6 }}>
              · {item}
            </Typography>
          </Box>
        ))}
        <Divider sx={{ my: 0.5 }} />
        <Typography variant="body2" sx={{ color: "warning.main", lineHeight: 1.6 }}>
          ⚠️ 离题内容不会回答
        </Typography>
      </Paper>

      {/* 右侧对话区 */}
      <Stack spacing={1.5} sx={{ flex: 1, minHeight: 0 }}>
        <Paper
          variant="outlined"
          sx={{ p: 2, flex: 1, minHeight: 380, overflow: "auto", bgcolor: "background.default", display: "flex", flexDirection: "column" }}
        >
          <Stack spacing={1.5} sx={{ flex: 1 }}>
            {messages.length === 0 && !loading && (
              <Typography color="text.secondary" sx={{ textAlign: "center", mt: 4 }}>
                还没有对话，从下面的输入框开始提问吧。
              </Typography>
            )}

            {messages.map((turn, index) => (
              <Box
                key={index}
                sx={{ display: "flex", justifyContent: turn.role === "user" ? "flex-end" : "flex-start" }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    p: 1.5,
                    maxWidth: "82%",
                    whiteSpace: "pre-wrap",
                    bgcolor: turn.role === "user" ? "primary.main" : "background.paper",
                    color: turn.role === "user" ? "primary.contrastText" : "text.primary",
                    border: turn.role === "assistant" ? "1px solid" : "none",
                    borderColor: "divider"
                  }}
                >
                  {turn.role === "assistant" && (
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
                      <SmartToyIcon fontSize="small" color="primary" />
                      {turn.guarded && <Chip size="small" color="warning" label="话题已拦截" />}
                    </Stack>
                  )}
                  <Typography sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{turn.content}</Typography>
                </Paper>
              </Box>
            ))}

            {loading && (
              <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
                <Paper
                  elevation={0}
                  variant="outlined"
                  sx={{ p: 1.5, display: "flex", alignItems: "center", gap: 1 }}
                >
                  <SmartToyIcon fontSize="small" color="primary" />
                  <CircularProgress size={16} />
                  <Typography variant="body2" color="text.secondary">
                    AI 正在思考…
                  </Typography>
                </Paper>
              </Box>
            )}

            <div ref={endRef} />
          </Stack>
        </Paper>

        {error && <Alert severity="error">{error}</Alert>}

        <Divider />

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField
            label="向 AI 课堂提问（与课程相关）"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            multiline
            minRows={1}
            maxRows={3}
            fullWidth
            disabled={loading}
            helperText={`${input.length}/1000（Enter 发送，Shift+Enter 换行）`}
            inputProps={{ maxLength: 1000 }}
          />
          <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
            <Button
              variant="contained"
              startIcon={<SendIcon />}
              onClick={() => void handleSend()}
              disabled={loading || !input.trim()}
              sx={{ minWidth: 110, height: 40 }}
            >
              发送
            </Button>
            <IconButton
              color="default"
              onClick={handleClear}
              disabled={loading || messages.length === 0}
              title="清空对话"
            >
              <DeleteSweepIcon />
            </IconButton>
          </Stack>
        </Stack>
      </Stack>
    </Box>
  );
}
