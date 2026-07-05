import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import LoginIcon from "@mui/icons-material/Login";

export function StudentPage() {
  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h1">学生入口</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.75 }}>
          阶段 1 已建立学生端路由和基础登录界面占位。
        </Typography>
      </Box>

      <Alert severity="info">学生签到与身份校验将在后续阶段接入。</Alert>

      <Card sx={{ maxWidth: 520 }}>
        <CardContent>
          <Stack spacing={2}>
            <TextField label="学号" fullWidth />
            <TextField label="姓名" fullWidth />
            <Button variant="contained" startIcon={<LoginIcon />}>
              进入课堂
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
