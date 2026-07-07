import json
import logging
import re
import time
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from app.core.exceptions import AppError
from app.db.session import get_connection


logger = logging.getLogger(__name__)
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_TIMEOUT_SECONDS = 5

DEGRADATION_STRATEGIES = [
    {
        "scenario": "excel_mapping",
        "normal_mode": "AI 自动识别表头语义并映射",
        "degraded_mode": "手动字段映射",
        "affected_features": ["Excel 字段解析"],
        "base_flow_available": True,
    },
    {
        "scenario": "short_answer_feedback",
        "normal_mode": "AI 生成优点、问题和改进建议",
        "degraded_mode": "标记为待教师批阅",
        "affected_features": ["简答题反馈"],
        "base_flow_available": True,
    },
    {
        "scenario": "homework_review",
        "normal_mode": "AI 按评分标准批阅并评分",
        "degraded_mode": "进入待人工批阅队列",
        "affected_features": ["作业 AI 批阅", "自动评分"],
        "base_flow_available": True,
    },
    {
        "scenario": "learning_advice",
        "normal_mode": "AI 生成个性化学习建议",
        "degraded_mode": "按等级和维度得分生成模板建议",
        "affected_features": ["学习建议文本"],
        "base_flow_available": True,
    },
]


def _now() -> str:
    return datetime.now().strftime(TIME_FORMAT)


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _redact_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def _sanitize_provider(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    api_key = str(result.pop("api_key", "") or "")
    result["api_key_set"] = bool(api_key)
    result["api_key_masked"] = _redact_secret(api_key)
    result["enabled"] = bool(result.get("enabled"))
    result["is_active"] = bool(result.get("is_active"))
    return result


def _active_provider(connection: Any) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT *
        FROM ai_provider_configs
        WHERE is_active = 1
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()
    return _row_to_dict(row) if row else None


def _load_safety_settings(connection: Any) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM ai_safety_settings WHERE id = 1").fetchone()
    if row is None:
        connection.execute(
            """
            INSERT INTO ai_safety_settings(id, max_length, blocked_keywords_json, keyword_action, display_strategy)
            VALUES (1, 2000, '[]', 'replace', 'review_first')
            """
        )
        row = connection.execute("SELECT * FROM ai_safety_settings WHERE id = 1").fetchone()
    data = _row_to_dict(row)
    data["blocked_keywords"] = _json_loads(data.pop("blocked_keywords_json", "[]"), [])
    return data


def get_ai_overview() -> dict[str, Any]:
    with get_connection() as connection:
        providers = [
            _sanitize_provider(_row_to_dict(row))
            for row in connection.execute("SELECT * FROM ai_provider_configs ORDER BY id").fetchall()
        ]
        safety = _load_safety_settings(connection)
        logs = [
            _row_to_dict(row)
            for row in connection.execute(
                """
                SELECT l.*, p.display_name AS provider_display_name
                FROM ai_check_logs l
                LEFT JOIN ai_provider_configs p ON p.id = l.provider_id
                ORDER BY l.checked_at DESC, l.id DESC
                LIMIT 10
                """
            ).fetchall()
        ]
        active = next((item for item in providers if item["is_active"]), None)
    status = active["last_status"] if active else "disabled"
    return {
        "status": status,
        "basic_mode": status != "available",
        "active_provider": active,
        "providers": providers,
        "safety": safety,
        "degradation_strategies": DEGRADATION_STRATEGIES,
        "recent_checks": logs,
        "affected_features": sorted(
            {feature for strategy in DEGRADATION_STRATEGIES for feature in strategy["affected_features"]}
        ),
    }


def save_provider(payload: dict[str, Any], provider_id: int | None = None) -> dict[str, Any]:
    provider_name = str(payload.get("provider_name") or "").strip()
    display_name = str(payload.get("display_name") or "").strip()
    base_url = str(payload.get("base_url") or "").strip().rstrip("/")
    model_name = str(payload.get("model_name") or "").strip()
    http_proxy = str(payload.get("http_proxy") or "").strip() or None
    api_key = payload.get("api_key")
    enabled = 1 if bool(payload.get("enabled")) else 0

    if not provider_name:
        raise AppError("Provider 标识不能为空", code="AI_PROVIDER_NAME_REQUIRED")
    if not display_name:
        raise AppError("Provider 名称不能为空", code="AI_DISPLAY_NAME_REQUIRED")
    if not base_url:
        raise AppError("AI 接口地址不能为空", code="AI_BASE_URL_REQUIRED")
    if not model_name:
        raise AppError("AI 模型名称不能为空", code="AI_MODEL_REQUIRED")

    with get_connection() as connection:
        if provider_id is None:
            cursor = connection.execute(
                """
                INSERT INTO ai_provider_configs(
                    provider_name, display_name, base_url, model_name, api_key, http_proxy, enabled, is_active, last_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    provider_name,
                    display_name,
                    base_url,
                    model_name,
                    str(api_key).strip() if api_key else None,
                    http_proxy,
                    enabled,
                    "unknown" if enabled else "disabled",
                ),
            )
            provider_id = int(cursor.lastrowid)
        else:
            existing = connection.execute("SELECT * FROM ai_provider_configs WHERE id = ?", (provider_id,)).fetchone()
            if existing is None:
                raise AppError("AI Provider 不存在", code="AI_PROVIDER_NOT_FOUND", status_code=404)
            fields = [
                "provider_name = ?",
                "display_name = ?",
                "base_url = ?",
                "model_name = ?",
                "http_proxy = ?",
                "enabled = ?",
                "last_status = CASE WHEN ? = 1 THEN last_status ELSE 'disabled' END",
                "updated_at = datetime('now')",
            ]
            values: list[Any] = [provider_name, display_name, base_url, model_name, http_proxy, enabled, enabled]
            if payload.get("clear_api_key"):
                fields.append("api_key = NULL")
            elif isinstance(api_key, str) and api_key.strip():
                fields.append("api_key = ?")
                values.append(api_key.strip())
            values.append(provider_id)
            connection.execute(f"UPDATE ai_provider_configs SET {', '.join(fields)} WHERE id = ?", values)
        row = connection.execute("SELECT * FROM ai_provider_configs WHERE id = ?", (provider_id,)).fetchone()
    return _sanitize_provider(_row_to_dict(row))


def activate_provider(provider_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM ai_provider_configs WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            raise AppError("AI Provider 不存在", code="AI_PROVIDER_NOT_FOUND", status_code=404)
        connection.execute("UPDATE ai_provider_configs SET is_active = 0")
        connection.execute("UPDATE ai_provider_configs SET is_active = 1, updated_at = datetime('now') WHERE id = ?", (provider_id,))
        updated = connection.execute("SELECT * FROM ai_provider_configs WHERE id = ?", (provider_id,)).fetchone()
    return _sanitize_provider(_row_to_dict(updated))


def _check_provider_remote(provider: dict[str, Any]) -> tuple[str, str, int]:
    if not provider.get("enabled"):
        return "disabled", "AI 未启用，系统进入基础模式", 0
    if not provider.get("api_key"):
        return "disabled", "未配置 API Key，系统进入基础模式", 0
    if not provider.get("base_url"):
        return "disabled", "未配置接口地址，系统进入基础模式", 0

    url = f"{str(provider['base_url']).rstrip('/')}/models"
    request = Request(url, headers={"Authorization": f"Bearer {provider['api_key']}", "Accept": "application/json"})
    proxy = str(provider.get("http_proxy") or "").strip()
    opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}) if proxy else ProxyHandler({}))
    started = time.perf_counter()
    try:
        with opener.open(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            latency_ms = int((time.perf_counter() - started) * 1000)
            if 200 <= response.status < 300:
                return "available", "AI 连通性自检通过", latency_ms
            return "unavailable", f"AI 自检返回 HTTP {response.status}", latency_ms
    except HTTPError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        if exc.code in {401, 403}:
            return "unavailable", "API Key 无效或无权限", latency_ms
        if exc.code == 429:
            return "unavailable", "AI 服务限流或额度不足", latency_ms
        return "unavailable", f"AI 自检返回 HTTP {exc.code}", latency_ms
    except URLError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return "unavailable", f"网络不可达或代理不可用：{exc.reason}", latency_ms
    except TimeoutError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return "unavailable", "AI 自检超时", latency_ms
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.warning("AI connectivity check failed for provider=%s: %s", provider.get("provider_name"), exc)
        return "unavailable", "AI 自检失败", latency_ms


def _post_chat_completion(provider: dict[str, Any], messages: list[dict[str, str]], response_format: dict[str, str] | None = None) -> str:
    if not provider.get("enabled") or not provider.get("api_key"):
        raise AppError("AI 不可用，系统进入降级模式", code="AI_UNAVAILABLE")
    payload: dict[str, Any] = {
        "model": provider["model_name"],
        "messages": messages,
        "temperature": 0.2,
    }
    if response_format:
        payload["response_format"] = response_format
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{str(provider['base_url']).rstrip('/')}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    proxy = str(provider.get("http_proxy") or "").strip()
    opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}) if proxy else ProxyHandler({}))
    try:
        with opener.open(request, timeout=DEFAULT_TIMEOUT_SECONDS * 3) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise AppError("API Key 无效或无权限", code="AI_AUTH_FAILED") from exc
        if exc.code == 429:
            raise AppError("AI 服务限流或额度不足", code="AI_RATE_LIMITED") from exc
        raise AppError(f"AI 调用失败：HTTP {exc.code}", code="AI_REQUEST_FAILED") from exc
    except (URLError, TimeoutError) as exc:
        raise AppError("AI 网络不可达或请求超时", code="AI_NETWORK_FAILED") from exc

    data = json.loads(raw)
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise AppError("AI 返回格式异常", code="AI_RESPONSE_INVALID") from exc


def generate_structured_json(
    scenario: str,
    prompt: str,
    source_type: str | None = None,
    source_id: int | None = None,
    retries: int = 2,
) -> dict[str, Any]:
    with get_connection() as connection:
        provider = _active_provider(connection)
    if provider is None:
        raise AppError("未配置 AI Provider", code="AI_PROVIDER_NOT_CONFIGURED")

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            content = _post_chat_completion(
                provider,
                [
                    {"role": "system", "content": "你是大学课堂教学辅助系统的 JSON 输出助手。只输出合法 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                {"type": "json_object"},
            )
            safety = check_content_safety(content, source_type or scenario, source_id)
            if safety["blocked"]:
                raise AppError("AI 返回内容未通过安全检查", code="AI_CONTENT_BLOCKED")
            parsed = json.loads(safety["text"])
            if not isinstance(parsed, dict):
                raise AppError("AI 返回不是 JSON 对象", code="AI_JSON_OBJECT_REQUIRED")
            return parsed
        except Exception as exc:
            last_error = exc
            logger.info("AI structured generation retry scenario=%s attempt=%s", scenario, attempt + 1)
    raise AppError(str(last_error or "AI 结构化生成失败"), code="AI_GENERATION_FAILED")


def is_ai_available() -> bool:
    with get_connection() as connection:
        provider = _active_provider(connection)
    return bool(provider and provider.get("enabled") and provider.get("api_key"))


def check_connectivity(provider_id: int | None = None) -> dict[str, Any]:
    with get_connection() as connection:
        if provider_id is None:
            provider = _active_provider(connection)
        else:
            row = connection.execute("SELECT * FROM ai_provider_configs WHERE id = ?", (provider_id,)).fetchone()
            provider = _row_to_dict(row) if row else None
        if provider is None:
            raise AppError("未配置 AI Provider", code="AI_PROVIDER_NOT_CONFIGURED", status_code=404)

    status, message, latency_ms = _check_provider_remote(provider)

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE ai_provider_configs
            SET last_status = ?, last_checked_at = ?, last_error = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (status, _now(), None if status == "available" else message, provider["id"]),
        )
        cursor = connection.execute(
            """
            INSERT INTO ai_check_logs(provider_id, status, message, latency_ms)
            VALUES (?, ?, ?, ?)
            """,
            (provider["id"], status, message, latency_ms),
        )
        row = connection.execute("SELECT * FROM ai_provider_configs WHERE id = ?", (provider["id"],)).fetchone()
    logger.info(
        "AI connectivity check provider=%s model=%s status=%s latency_ms=%s",
        provider.get("provider_name"),
        provider.get("model_name"),
        status,
        latency_ms,
    )
    return {
        "log_id": int(cursor.lastrowid),
        "status": status,
        "message": message,
        "latency_ms": latency_ms,
        "provider": _sanitize_provider(_row_to_dict(row)),
        "basic_mode": status != "available",
    }


def update_safety_settings(payload: dict[str, Any]) -> dict[str, Any]:
    max_length = int(payload.get("max_length") or 2000)
    if max_length < 100 or max_length > 8000:
        raise AppError("AI 反馈长度限制应在 100 到 8000 字之间", code="AI_SAFETY_LENGTH_INVALID")
    keyword_action = str(payload.get("keyword_action") or "replace")
    display_strategy = str(payload.get("display_strategy") or "review_first")
    if keyword_action not in {"replace", "block"}:
        raise AppError("敏感词处理策略不支持", code="AI_SAFETY_ACTION_INVALID")
    if display_strategy not in {"review_first", "direct_with_report"}:
        raise AppError("AI 展示策略不支持", code="AI_DISPLAY_STRATEGY_INVALID")
    keywords = [str(item).strip() for item in payload.get("blocked_keywords") or [] if str(item).strip()]
    keywords = sorted(set(keywords))

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE ai_safety_settings
            SET max_length = ?, blocked_keywords_json = ?, keyword_action = ?, display_strategy = ?,
                updated_at = datetime('now')
            WHERE id = 1
            """,
            (max_length, json.dumps(keywords, ensure_ascii=False), keyword_action, display_strategy),
        )
        return _load_safety_settings(connection)


def check_content_safety(text: str, source_type: str = "manual_test", source_id: int | None = None) -> dict[str, Any]:
    original = str(text or "")
    with get_connection() as connection:
        settings = _load_safety_settings(connection)

    sanitized = original
    matched_keywords: list[str] = []
    action = "pass"
    max_length = int(settings["max_length"])
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        action = "truncate"

    for keyword in settings["blocked_keywords"]:
        pattern = re.compile(re.escape(str(keyword)), re.IGNORECASE)
        if pattern.search(sanitized):
            matched_keywords.append(str(keyword))
            if settings["keyword_action"] == "replace":
                sanitized = pattern.sub("***", sanitized)
                action = "replace"
            else:
                action = "block"

    blocked = action == "block"
    visible_text = "" if blocked else sanitized
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO ai_content_safety_logs(
                source_type, source_id, action, matched_keywords_json, original_length, sanitized_length
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                source_type,
                source_id,
                action,
                json.dumps(matched_keywords, ensure_ascii=False),
                len(original),
                len(visible_text),
            ),
        )

    return {
        "safe": not blocked,
        "blocked": blocked,
        "action": action,
        "matched_keywords": matched_keywords,
        "original_length": len(original),
        "sanitized_length": len(sanitized),
        "text": visible_text,
        "display_strategy": settings["display_strategy"],
        "message": "AI 反馈内容异常，请联系教师" if blocked else "内容安全检查通过",
    }


def record_failure_task(
    scenario: str,
    source_type: str | None = None,
    source_id: int | None = None,
    reason: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if scenario not in {item["scenario"] for item in DEGRADATION_STRATEGIES}:
        raise AppError("AI 降级场景不支持", code="AI_SCENARIO_UNSUPPORTED")
    strategy = next(item for item in DEGRADATION_STRATEGIES if item["scenario"] == scenario)
    status = "template_generated" if scenario == "learning_advice" else "pending_manual"
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO ai_failure_tasks(scenario, source_type, source_id, status, reason, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (scenario, source_type, source_id, status, reason, json.dumps(payload or {}, ensure_ascii=False)),
        )
        row = connection.execute("SELECT * FROM ai_failure_tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
    task = _row_to_dict(row)
    task["degraded_mode"] = strategy["degraded_mode"]
    task["payload"] = _json_loads(task.pop("payload_json", "{}"), {})
    return task


def list_failure_tasks(limit: int = 30) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM ai_failure_tasks
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    tasks = []
    for row in rows:
        item = _row_to_dict(row)
        item["payload"] = _json_loads(item.pop("payload_json", "{}"), {})
        tasks.append(item)
    return tasks
