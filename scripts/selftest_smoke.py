"""迭代自检冒烟测试：逐模块验证后端改进。

运行：PYTHONPATH=backend python scripts/selftest_smoke.py
依赖 config/local.yaml 将 storage.local_root 指向隔离测试库（.selftest）。
"""
import os
import sys
import traceback
from pathlib import Path

# 确保使用隔离测试库（本地配置优先）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.main import create_app  # noqa: E402
from app.core.config import get_settings  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, cond, detail))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" -- {detail}" if detail else ""))


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_teacher(client: TestClient) -> str:
    # 若已设密码则直接登录，否则先 setup
    st = client.get("/api/v1/auth/status").json()
    if st.get("data", {}).get("password_set"):
        r = client.post("/api/v1/auth/login", json={"password": "Test@1234"})
        return r.json()["data"]["token"]
    r = client.post("/api/v1/auth/setup", json={"password": "Test@1234", "confirm_password": "Test@1234"})
    return r.json()["data"]["token"]


def test_module1_auth_system_backup(client: TestClient, settings) -> None:
    token = setup_teacher(client)
    check("module1: teacher token issued", bool(token))

    # Fix1: cached_replay 未鉴权应被拒
    r = client.post("/api/v1/recovery/sessions/1/cached-replays", json={"payload": {}})
    check("module1: cached_replay 无 token 返回 401", r.status_code == 401, f"status={r.status_code}")
    r2 = client.post(
        "/api/v1/recovery/sessions/1/cached-replays",
        json={"payload": {}},
        headers=auth_headers(token),
    )
    # 鉴权通过即应进入业务逻辑（测试库无 session 1，业务层返回 404 属正常），
    # 关键断言是“不再被 401 拦截”。
    check("module1: cached_replay 带 token 通过鉴权(非401)", r2.status_code != 401, f"status={r2.status_code}")

    # Fix3/4: 访问配置落库
    r = client.post(
        "/api/v1/system/access",
        json={"selected_ip": "192.168.1.100", "selected_port": 8081},
        headers=auth_headers(token),
    )
    check("module1: 保存访问配置 200", r.status_code == 200, f"status={r.status_code}")
    r = client.get("/api/v1/system/access", headers=auth_headers(token))
    data = r.json().get("data", {})
    check("module1: 访问配置持久化回读", data.get("selected_ip") == "192.168.1.100" and data.get("port") == 8081,
          f"selected_ip={data.get('selected_ip')} port={data.get('port')}")

    # Fix2: 备份创建
    r = client.post("/api/v1/system/backups", headers=auth_headers(token))
    check("module1: 手动备份成功", r.status_code == 200 and r.json().get("success"), f"status={r.status_code}")

    # Fix2: 损坏备份应被完整性校验拒绝
    backups_dir = settings.storage.backups_dir
    corrupt = Path(backups_dir) / "teaching_assist_corrupt_test.db"
    corrupt.write_bytes(b"this is not a sqlite database file at all")
    r = client.post(
        "/api/v1/system/backups/restore",
        json={"file_path": str(corrupt)},
        headers=auth_headers(token),
    )
    check("module1: 损坏备份恢复被拒(422)", r.status_code == 422, f"status={r.status_code} body={r.text[:120]}")
    corrupt.unlink(missing_ok=True)

    # Fix6: 认证状态不崩溃
    r = client.get("/api/v1/auth/status")
    check("module1: 认证状态可读取", r.status_code == 200 and "password_set" in r.json().get("data", {}),
          f"status={r.status_code}")


def test_module3_questions_homework_eval() -> None:
    from app.db.session import get_connection
    from app.services import questions as questions_service, evaluation as evaluation_service

    # 填空题：字符串与列表两种提交都应命中标准答案（修复 list 被 str(list) 污染）
    q = {"question_type": "fill_blank", "score": 2, "correct_answer": ["北京"], "keywords": []}
    mark_str, _ = questions_service._grade_answer(q, "北京", "submitted")
    mark_list, _ = questions_service._grade_answer(q, ["北京"], "submitted")
    check("module3: 填空 字符串提交命中", mark_str == 1, f"mark={mark_str}")
    check("module3: 填空 列表提交命中(修复)", mark_list == 1, f"mark={mark_list}")

    # 构造最小场景验证 evaluate 聚合重构（避免 N+1）可执行且按学生产出
    sid = 99001
    with get_connection() as connection:
        connection.execute("INSERT OR IGNORE INTO courses(id, name) VALUES (?, ?)", (sid, "测试课"))
        connection.execute("INSERT OR IGNORE INTO classes(id, name) VALUES (?, ?)", (sid, "测试班"))
        connection.execute("INSERT OR IGNORE INTO course_classes(course_id, class_id) VALUES (?, ?)", (sid, sid))
        connection.execute(
            "INSERT OR IGNORE INTO classroom_sessions(id, course_id, title, session_no, status) VALUES (?, ?, ?, ?, 'active')",
            (sid, sid, "测试课堂", 1),
        )
        connection.execute("INSERT OR IGNORE INTO session_classes(session_id, class_id) VALUES (?, ?)", (sid, sid))
        connection.execute(
            "INSERT OR IGNORE INTO students(id, student_id, name, class_id) VALUES (?, ?, ?, ?)",
            (sid, "T99001", "张三", sid),
        )
        connection.execute(
            "INSERT OR IGNORE INTO sign_in_records(session_id, student_id, status) VALUES (?, ?, 'normal')",
            (sid, sid),
        )
        connection.execute(
            "INSERT OR IGNORE INTO questions(id, session_id, title, content, question_type, status) "
            "VALUES (?, ?, 'q', 'c', 'fill_blank', 'published')",
            (sid, sid),
        )
        connection.execute(
            "INSERT OR IGNORE INTO question_answers(question_id, session_id, student_id, status, score) "
            "VALUES (?, ?, ?, 'submitted', 1)",
            (sid, sid, sid),
        )
        connection.execute(
            "INSERT OR IGNORE INTO homework(id, session_id, title, deadline, status) VALUES (?, ?, 'hw', '2099-01-01 00:00:00', 'active')",
            (sid, sid),
        )
        connection.execute(
            "INSERT OR IGNORE INTO homework_submissions(homework_id, session_id, student_id, status, is_latest) "
            "VALUES (?, ?, ?, 'submitted', 1)",
            (sid, sid, sid),
        )
    try:
        report = evaluation_service.calculate_session(sid, "temporary")
        ok_eval = isinstance(report, dict)
        evals = report.get("records") or report.get("evaluations") or report.get("students") or []
        check("module3: calculate_session 执行并返回评估结果(聚合重构)", ok_eval and len(evals) >= 1,
              f"type={type(report).__name__} records={len(evals)}")
    except Exception:
        check("module3: calculate_session 执行无异常", False, traceback.format_exc())


def test_module4_ai() -> None:
    from app.services import ai as ai_service

    # 结构化生成场景：关闭截断后，超长文本应原样返回（不再因 max_length 截断破坏 JSON 解析）
    long_json = '{"score": 95, "comment": "' + ("学" * 3000) + '"}'
    safety = ai_service.check_content_safety(long_json, source_type="homework_submission", truncate=False, replace_keywords=False)
    check("module4: 结构化场景超长文本不被截断", len(safety["text"]) == len(long_json) and safety["action"] != "truncate",
          f"orig={len(long_json)} out={len(safety['text'])} action={safety['action']}")
    # 关闭截断后，原本会被截断的 JSON 现可正常解析
    try:
        import json as _json
        parsed = _json.loads(safety["text"])
        ok_parse = isinstance(parsed, dict)
    except Exception:
        ok_parse = False
    check("module4: 关闭截断后 JSON 可解析", ok_parse)

    # 默认 keyword_action='replace' 但显式关闭替换时，应强制走 block 分支拦截
    safety_block = ai_service.check_content_safety(
        "这是暴力内容测试", source_type="manual_test", blocked_keywords=["暴力"], replace_keywords=False
    )
    check("module4: 关键词 block 拦截生效", bool(safety_block["blocked"]) and safety_block["action"] == "block",
          f"blocked={safety_block['blocked']} action={safety_block['action']}")

    # 默认 replace 策略（不关闭替换）时，关键词应被替换放行而非拦截
    safety_replace = ai_service.check_content_safety(
        "这是暴力内容测试", source_type="manual_test", blocked_keywords=["暴力"]
    )
    check("module4: 默认 replace 策略关键词被替换放行",
          safety_replace["action"] == "replace" and not safety_replace["blocked"] and "***" in safety_replace["text"],
          f"action={safety_replace['action']} blocked={safety_replace['blocked']} text={safety_replace['text']}")


def test_module4_apikey_encryption() -> None:
    from app.db.session import get_connection
    from app.services import ai as ai_service

    # 保存一个带 API Key 的 Provider，验证入库为密文、读出为明文
    saved = ai_service.save_provider({
        "provider_name": "selftest_enc",
        "display_name": "自检测密",
        "base_url": "https://example.com/v1",
        "model_name": "test-model",
        "api_key": "sk-SECRET-0123456789",
        "enabled": False,
    })
    pid = saved["id"]
    try:
        with get_connection() as connection:
            raw = connection.execute(
                "SELECT api_key FROM ai_provider_configs WHERE id = ?", (pid,)
            ).fetchone()
        raw_key = dict(raw)["api_key"]
        check("module4: API Key 入库为密文(enc::前缀)", bool(raw_key) and raw_key.startswith("enc::"),
              f"stored={raw_key[:12]}..." if raw_key else "stored=None")
        # 读出应解密为原始明文
        ai_service.activate_provider(pid)
        with get_connection() as connection:
            active = ai_service._active_provider(connection)
        check("module4: 读取 Provider 时 API Key 解密为明文",
              active is not None and active["api_key"] == "sk-SECRET-0123456789",
              f"decrypted={active['api_key'] if active else None}")
    finally:
        with get_connection() as connection:
            connection.execute("DELETE FROM ai_provider_configs WHERE id = ?", (pid,))


def test_module2_student_token() -> None:
    from app.db.session import get_connection
    from app.services import classroom as classroom_service, messages as message_service

    sid = 99002
    with get_connection() as connection:
        connection.execute("INSERT OR IGNORE INTO courses(id, name) VALUES (?, ?)", (sid, "令牌课"))
        connection.execute("INSERT OR IGNORE INTO classes(id, name) VALUES (?, ?)", (sid, "令牌班"))
        connection.execute("INSERT OR IGNORE INTO course_classes(course_id, class_id) VALUES (?, ?)", (sid, sid))
        connection.execute(
            "INSERT OR IGNORE INTO classroom_sessions(id, course_id, title, session_no, status) VALUES (?, ?, ?, ?, 'active')",
            (sid, sid, "令牌课堂", 1),
        )
        connection.execute("INSERT OR IGNORE INTO session_classes(session_id, class_id) VALUES (?, ?)", (sid, sid))
        connection.execute(
            "INSERT OR IGNORE INTO students(id, student_id, name, class_id) VALUES (?, ?, ?, ?)",
            (sid, "T99002", "李四", sid),
        )

    # 签到应返回会话令牌
    sign_in = classroom_service.student_sign_in(sid, "T99002", "李四", None, None, None)
    token = sign_in.get("token")
    check("module2: 签到返回学生会话令牌", bool(token), f"token={'set' if token else 'none'}")

    # 带令牌发私信应成功
    import asyncio

    try:
        msg = asyncio.run(message_service.send_student_message("T99002", "李四", "老师好", token))
        send_ok = isinstance(msg, dict) and msg.get("id") is not None
    except Exception as exc:
        send_ok = False
        msg = exc
    check("module2: 带令牌发送私信成功", send_ok, f"msg={msg if not send_ok else 'ok'}")

    # 错误令牌应被拒（401）
    blocked = False
    try:
        asyncio.run(message_service.send_student_message("T99002", "李四", "伪造", "invalid-token"))
    except Exception as exc:
        blocked = getattr(exc, "status_code", None) == 401 or "STUDENT_TOKEN_INVALID" in str(getattr(exc, "code", ""))
    check("module2: 错误令牌发送被拒(401)", blocked)

    # 带令牌读取会话应由令牌解析身份
    try:
        pk = message_service.resolve_student_pk_for_read("T99002", "李四", token)
        read_ok = pk == sid
    except Exception:
        read_ok = False
    check("module2: 带令牌读取会话解析身份正确", read_ok, f"pk={pk if read_ok else 'err'}")

    # 错误令牌读取应被拒
    read_blocked = False
    try:
        message_service.resolve_student_pk_for_read("T99002", "李四", "invalid-token")
    except Exception as exc:
        read_blocked = getattr(exc, "status_code", None) == 401
    check("module2: 错误令牌读取会话被拒(401)", read_blocked)

    # === 迭代3 #3：PII 读取令牌优先验证 ===
    from app.services import questions as question_service

    qid = 99002
    with get_connection() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO questions(id, session_id, title, content, question_type, score, status) "
            "VALUES (?, ?, ?, ?, 'short_answer', 5, 'published')",
            (qid, sid, "令牌优先题", "草稿测试",),
        )
        connection.execute(
            "INSERT INTO question_answers(question_id, session_id, student_id, answer_text, status, is_latest) "
            "VALUES (?, ?, ?, '李四的草稿', 'draft', 1)",
            (qid, sid, sid),
        )

    # ① 带令牌 + 伪造他人姓名：令牌身份优先，仍只返回令牌本人(李四)的草稿
    draft = question_service.get_student_draft(qid, "T99999", "王五", token)
    token_ok = isinstance(draft, dict) and draft.get("draft") is not None and draft["draft"].get("answer_text") == "李四的草稿"
    check("module3: 带令牌读取草稿(令牌优先/防伪名)", token_ok, f"answer={draft.get('draft')}")

    # ② 无令牌兜底：正确学号+姓名仍可读取（供 AI 课堂等服务端路径）
    draft_fb = question_service.get_student_draft(qid, "T99002", "李四", None)
    fallback_ok = isinstance(draft_fb, dict) and draft_fb.get("draft") is not None
    check("module3: 无令牌兜底读取草稿(服务端兼容)", fallback_ok, f"answer={draft_fb.get('draft')}")


def main() -> int:
    settings = get_settings()
    print(f"测试库: {settings.storage.database_path}")
    app = create_app()
    with TestClient(app) as client:
        try:
            test_module1_auth_system_backup(client, settings)
        except Exception:
            check("module1: 测试执行异常", False, traceback.format_exc())

    try:
        test_module3_questions_homework_eval()
    except Exception:
        check("module3: 测试执行异常", False, traceback.format_exc())

    try:
        test_module4_ai()
    except Exception:
        check("module4: 测试执行异常", False, traceback.format_exc())

    try:
        test_module4_apikey_encryption()
    except Exception:
        check("module4: API Key 加密测试异常", False, traceback.format_exc())

    try:
        test_module2_student_token()
    except Exception:
        check("module2: 学生令牌测试异常", False, traceback.format_exc())

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n=== 总结果: {len(RESULTS)-len(failed)}/{len(RESULTS)} 通过 ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
