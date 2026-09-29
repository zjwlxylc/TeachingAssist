import { useState } from "react";
import { Alert, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from "@mui/material";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { request } from "../api/http";

export type AcademicKind = "classes" | "sessions";
interface DeletionPreview {
  name: string;
  can_delete: boolean;
  reason: string;
  preview_token: string;
  impacts: { label: string; count: number }[];
  blockers: { id: number; title: string; course_name: string; session_no: number }[];
}
interface Props {
  kind: AcademicKind;
  id: number;
  onDeleted: (kind: AcademicKind, id: number, retainedFiles: number) => Promise<void>;
  onViewSessions?: () => void;
}

export default function AcademicDeleteButton({ kind, id, onDeleted, onViewSessions }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<DeletionPreview | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const label = kind === "classes" ? "班级" : "课堂";

  async function inspect() {
    setOpen(true);
    setBusy(true);
    setPreview(null);
    setConfirmation("");
    setError("");
    try {
      setPreview(await request<DeletionPreview>(`/academic/${kind}/${id}/deletion-preview`));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!preview || !preview.can_delete || confirmation !== preview.name) return;
    setBusy(true);
    setError("");
    let retained = 0;
    try {
      const result = await request<{ retained_file_count: number }>(`/academic/${kind}/${id}`, {
        method: "DELETE",
        body: JSON.stringify({ confirmation_name: confirmation, preview_token: preview.preview_token })
      });
      retained = result.retained_file_count;
    } catch (err) {
      setError((err as Error).message);
      setPreview(null);
      setConfirmation("");
      setBusy(false);
      return;
    }
    setOpen(false);
    setBusy(false);
    await onDeleted(kind, id, retained);
  }

  return <>
    <Button size="small" color="error" startIcon={<DeleteOutlineIcon />} onClick={() => void inspect()}>删除</Button>
    <Dialog open={open} onClose={() => { if (!busy) setOpen(false); }} fullWidth maxWidth="sm" aria-labelledby={`delete-${kind}-${id}`}>
      <DialogTitle id={`delete-${kind}-${id}`}>删除{label} #{id}{preview ? `：${preview.name}` : ""}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          {busy && <CircularProgress size={24} aria-label="正在处理删除请求" />}
          {error && <Alert severity="error">{error}。可点击“重新检查”确认当前情况。</Alert>}
          {preview && <>
            {!preview.can_delete ? <>
              <Alert severity="warning">{preview.reason}</Alert>
              {preview.blockers.map(item => <Typography key={item.id}>
                #{item.id} {item.course_name} · 第 {item.session_no} 次：{item.title}
              </Typography>)}
              {kind === "classes" && onViewSessions && <Button onClick={() => { setOpen(false); onViewSessions(); }}>前往课堂签到管理</Button>}
            </> : <>
              <Alert severity="warning">删除后无法撤销。请确认这些内容不再需要。</Alert>
              <Typography>{kind === "sessions"
                ? "将删除本课堂及下列记录和作业附件。课程、班级、学生名单和其他课堂会保留。"
                : "将删除本班级及下列学生名单、课程关联和私信。课程与其他班级会保留。"}</Typography>
              {preview.impacts.length > 0 ? preview.impacts.map(item => <Typography key={item.label} variant="body2">
                {item.label}：{item.count} 条
              </Typography>) : <Typography variant="body2">没有关联记录。</Typography>}
              <TextField label={`请输入${label === "班级" ? "班级名称" : "课堂标题"}以确认`}
                helperText={`需完整输入：${preview.name}`} value={confirmation} disabled={busy}
                onChange={event => setConfirmation(event.target.value)} autoComplete="off" fullWidth />
            </>}
          </>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setOpen(false)} disabled={busy}>取消</Button>
        <Button onClick={() => void inspect()} disabled={busy}>重新检查</Button>
        <Button color="error" variant="contained" onClick={() => void remove()}
          disabled={busy || !preview?.can_delete || confirmation !== preview.name}>确认删除{label}</Button>
      </DialogActions>
    </Dialog>
  </>;
}
