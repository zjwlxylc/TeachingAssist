-- 默认 AI Provider 由 DeepSeek 改为智谱 GLM
-- 需求：系统第一个默认选项应为智谱，而非 DeepSeek。
-- 说明：_active_provider() 取 is_active=1 且 id 最小者；现将智谱置为 active、DeepSeek 置为非 active。
-- 匹配依据：迁移 008 中固定 id（1=DeepSeek, 2=智谱 GLM），不依赖可能被用户改过的 provider_name。
-- 幂等：重复执行结果一致。
UPDATE ai_provider_configs SET is_active = 0 WHERE id = 1;   -- DeepSeek
UPDATE ai_provider_configs SET is_active = 1 WHERE id = 2;   -- 智谱 GLM
