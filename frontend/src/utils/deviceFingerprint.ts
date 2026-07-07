/**
 * 浏览器会话标识
 *
 * 防止同一台设备替多人签到。
 *
 * 原理：
 * - 每台电脑/手机的浏览器有独立的 sessionStorage
 * - 页面加载时生成随机 ID 存入 sessionStorage
 * - 同一浏览器签不同学生 → ID 相同 → 触发告警
 * - 不同电脑（即使硬件完全一样）→ 不同浏览器 → ID 不同 → 正常
 *
 * 为什么不用 Canvas/WebGL 指纹？
 * - 机房电脑硬件完全相同，Canvas/WebGL 产出的 hash 也一样，无法区分
 */
const SESSION_KEY = "teaching_assist_browser_session_id";

function generateId(): string {
  const array = new Uint8Array(8);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

let cached: string | null = null;

/** 获取浏览器会话 ID（同一标签页内不变） */
export function getBrowserSessionId(): string {
  if (cached) {
    return cached;
  }
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = generateId();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  cached = id;
  return id;
}
