-- 新增 Agnes 2.0 Flash AI Provider 配置（OpenAI Chat Completions 兼容）
-- 后端 ai.py 的连通性自检(_check_provider_remote)与对话调用(_post_chat_completion)
-- 统一使用 OpenAI 兼容的 /models 与 /chat/completions 接口，不区分 api_format，
-- 因此无需在表中保存 api_format 等额外字段。api_key 由教师在界面填写后启用。
INSERT INTO ai_provider_configs (
    provider_name,
    display_name,
    base_url,
    model_name,
    api_key,
    enabled,
    is_active,
    last_status
)
SELECT
    'agnes-ai',
    'Agnes 2.0 Flash',
    'https://apihub.agnes-ai.com/v1',
    'agnes-2.0-flash',
    NULL,
    0,
    0,
    'disabled'
WHERE NOT EXISTS (
    SELECT 1 FROM ai_provider_configs WHERE provider_name = 'agnes-ai'
);
