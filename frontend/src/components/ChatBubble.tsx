import { Avatar, Box, Paper, Stack, Typography } from "@mui/material";

interface ChatBubbleProps {
  role: "teacher" | "student";
  name: string;
  time: string;
  content: string;
  /** 教师侧气泡顶部显示名，默认"我"；课堂互动可传真实教师名 */
  selfName?: string;
}

/**
 * 统一的对话气泡：头像 + 姓名/时间 + 气泡正文。
 * 教师消息靠右、实心主色；学生消息靠左、白底描边。
 * 气泡最大宽度响应式收敛，避免宽屏下单行过长；头像圆角朝内，强化对话感。
 */
export default function ChatBubble({ role, name, time, content, selfName = "我" }: ChatBubbleProps) {
  const isTeacher = role === "teacher";
  const displayName = isTeacher ? selfName : name || "匿名";
  const initial = (displayName || "?").trim().charAt(0) || "?";

  return (
    <Stack direction={isTeacher ? "row-reverse" : "row"} spacing={1} alignItems="flex-start">
      <Avatar
        sx={{
          width: 36,
          height: 36,
          fontSize: "0.95rem",
          flexShrink: 0,
          bgcolor: isTeacher ? "primary.main" : "action.selected",
          color: isTeacher ? "primary.contrastText" : "text.primary",
        }}
      >
        {initial}
      </Avatar>
      <Box sx={{ maxWidth: { xs: "82%", sm: "75%", md: "68%" } }}>
        <Stack
          direction={isTeacher ? "row-reverse" : "row"}
          spacing={0.5}
          alignItems="baseline"
          sx={{ mb: 0.25 }}
        >
          <Typography variant="caption" fontWeight={700} color="text.primary">
            {displayName}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {time}
          </Typography>
        </Stack>
        <Paper
          elevation={0}
          sx={{
            p: 1.25,
            bgcolor: isTeacher ? "primary.main" : "background.paper",
            color: isTeacher ? "primary.contrastText" : "text.primary",
            border: isTeacher ? "none" : "1px solid",
            borderColor: isTeacher ? "transparent" : "divider",
            borderRadius: 1.5,
            borderTopRightRadius: isTeacher ? 0.5 : 1.5,
            borderTopLeftRadius: isTeacher ? 1.5 : 0.5,
          }}
        >
          <Typography sx={{ whiteSpace: "pre-wrap", fontSize: "0.9rem", lineHeight: 1.55 }}>
            {content}
          </Typography>
        </Paper>
      </Box>
    </Stack>
  );
}
