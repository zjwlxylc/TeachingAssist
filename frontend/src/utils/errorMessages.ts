/**
 * 错误消息翻译工具
 * 将后端技术性错误消息翻译为用户友好的中文提示
 */

// 错误消息映射表
const ERROR_MESSAGES: Record<string, string> = {
  // 网络相关
  "Network Error": "网络连接失败，请检查网络后重试",
  "Network timeout": "网络连接超时，请稍后重试",
  "Failed to fetch": "无法连接到服务器，请检查网络连接",
  "Connection refused": "服务器连接被拒绝，请联系管理员",

  // 认证相关
  "Invalid credentials": "用户名或密码错误",
  "Unauthorized": "未授权访问，请先登录",
  "Token expired": "登录已过期，请重新登录",
  "Authentication failed": "认证失败，请重新登录",

  // 数据库相关
  "Database integrity check failed": "数据库完整性检查失败，请联系管理员",
  "Database error": "数据库错误，请稍后重试或联系管理员",
  "Connection pool timeout": "数据库连接超时，请稍后重试",

  // 学生相关
  "Student not found": "该学号不在课堂名单中，请检查后重试",
  "STUDENT_NOT_FOUND": "该学号不在课堂名单中，请检查后重试",
  "STUDENT_NAME_MISMATCH": "学号与姓名不匹配，请检查输入",
  "STUDENT_ID_NAME_REQUIRED": "学号和姓名不能为空",

  // 课堂相关
  "SESSION_NOT_ACTIVE": "课堂尚未开始或已结束",
  "SESSION_ENDED": "课堂已结束，不能进行此操作",
  "Session not found": "未找到该课堂，请检查课堂ID",

  // 文件上传相关
  "File too large": "文件过大，请选择小于10MB的文件",
  "Invalid file type": "不支持的文件格式",
  "Upload failed": "文件上传失败，请重试",

  // AI相关
  "AI service unavailable": "AI服务暂不可用，已切换为基础模式",
  "AI timeout": "AI处理超时，请稍后重试",
  "AI provider not configured": "AI服务未配置，请联系教师",

  // 权限相关
  "Permission denied": "权限不足，无法执行此操作",
  "Access denied": "访问被拒绝",

  // 通用错误
  "Internal server error": "服务器内部错误，请稍后重试或联系管理员",
  "Bad request": "请求参数错误，请检查输入",
  "Not found": "请求的资源不存在",
  "Conflict": "操作冲突，请刷新后重试",
};

// 错误关键词映射（用于模糊匹配）
const ERROR_KEYWORDS: Array<{ keyword: string; message: string }> = [
  { keyword: "网络", message: "网络连接异常，请检查网络后重试" },
  { keyword: "超时", message: "操作超时，请稍后重试" },
  { keyword: "timeout", message: "操作超时，请稍后重试" },
  { keyword: "连接", message: "连接失败，请检查网络或稍后重试" },
  { keyword: "数据库", message: "数据操作失败，请稍后重试或联系管理员" },
  { keyword: "database", message: "数据操作失败，请稍后重试或联系管理员" },
  { keyword: "权限", message: "权限不足，无法执行此操作" },
  { keyword: "permission", message: "权限不足，无法执行此操作" },
  { keyword: "unauthorized", message: "未授权访问，请先登录" },
  { keyword: "token", message: "登录状态已过期，请重新登录" },
  { keyword: "学号", message: "学号相关错误，请检查输入" },
  { keyword: "姓名", message: "姓名相关错误，请检查输入" },
  { keyword: "not found", message: "请求的资源不存在" },
  { keyword: "找不到", message: "未找到相关数据" },
];

/**
 * 翻译错误消息
 * @param error - 错误对象或错误消息字符串
 * @returns 用户友好的中文错误消息
 */
export function translateError(error: Error | string): string {
  const errorMessage = typeof error === "string" ? error : error.message;

  // 如果已经是中文错误消息，直接返回
  if (/[一-龥]/.test(errorMessage)) {
    return errorMessage;
  }

  // 1. 尝试精确匹配
  if (ERROR_MESSAGES[errorMessage]) {
    return ERROR_MESSAGES[errorMessage];
  }

  // 2. 尝试包含匹配
  for (const [key, value] of Object.entries(ERROR_MESSAGES)) {
    if (errorMessage.includes(key)) {
      return value;
    }
  }

  // 3. 尝试关键词匹配
  const lowerMessage = errorMessage.toLowerCase();
  for (const { keyword, message } of ERROR_KEYWORDS) {
    if (lowerMessage.includes(keyword.toLowerCase())) {
      return message;
    }
  }

  // 4. 默认通用错误消息
  return "操作失败，请稍后重试";
}

/**
 * 从HTTP响应中提取错误消息
 * @param response - HTTP响应对象
 * @returns 用户友好的错误消息
 */
export function extractErrorFromResponse(response: any): string {
  try {
    // 尝试从响应中提取错误消息
    if (response?.message) {
      return translateError(response.message);
    }
    if (response?.error) {
      return translateError(response.error);
    }
    if (response?.data?.message) {
      return translateError(response.data.message);
    }

    // 根据HTTP状态码返回默认消息
    if (response?.status) {
      switch (response.status) {
        case 400:
          return "请求参数错误，请检查输入";
        case 401:
          return "未授权访问，请先登录";
        case 403:
          return "权限不足，无法执行此操作";
        case 404:
          return "请求的资源不存在";
        case 409:
          return "操作冲突，请刷新后重试";
        case 500:
          return "服务器内部错误，请稍后重试";
        case 502:
          return "服务器网关错误，请稍后重试";
        case 503:
          return "服务暂时不可用，请稍后重试";
        default:
          return "操作失败，请稍后重试";
      }
    }
  } catch {
    // 解析失败，返回通用错误
  }

  return "操作失败，请稍后重试";
}

/**
 * 判断错误是否为网络错误
 * @param error - 错误对象
 * @returns 是否为网络错误
 */
export function isNetworkError(error: Error | string): boolean {
  const errorMessage = typeof error === "string" ? error : error.message;
  const lowerMessage = errorMessage.toLowerCase();

  return (
    lowerMessage.includes("network") ||
    lowerMessage.includes("timeout") ||
    lowerMessage.includes("fetch") ||
    lowerMessage.includes("连接") ||
    lowerMessage.includes("网络")
  );
}

/**
 * 判断错误是否为认证错误
 * @param error - 错误对象
 * @returns 是否为认证错误
 */
export function isAuthError(error: Error | string): boolean {
  const errorMessage = typeof error === "string" ? error : error.message;
  const lowerMessage = errorMessage.toLowerCase();

  return (
    lowerMessage.includes("unauthorized") ||
    lowerMessage.includes("token") ||
    lowerMessage.includes("authentication") ||
    lowerMessage.includes("未授权") ||
    lowerMessage.includes("登录")
  );
}
