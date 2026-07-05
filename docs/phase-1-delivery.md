# 阶段 1 交付说明

## 已完成

1. FastAPI 项目结构与 Uvicorn 启动入口。
2. SQLite 数据库连接、WAL 模式、`synchronous=NORMAL`、外键开启。
3. SQL 文件迁移机制，当前初始迁移为 `001_initial.sql`。
4. 统一 API 响应格式：`success/code/message/data`。
5. 全局异常处理：业务异常、参数校验异常、未知异常。
6. 日志系统：控制台 + 本地滚动日志文件。
7. 配置文件加载：`config/default.yaml` + 可选 `config/local.yaml`。
8. 后端静态资源托管：前端构建后自动挂载 `frontend/dist`。
9. 本地数据库目录初始化与启动检查。
10. U 盘路径识别占位：优先读取配置，否则返回当前项目所在盘根路径。
11. 健康检查接口：`/api/v1/health`。
12. 启动检查接口：`/api/v1/system/startup`。
13. React + Vite + TypeScript + MUI 前端工程。
14. 教师端与学生端路由、基础布局、API 封装、WebSocket 客户端封装、登录状态 store。

## 留待后续阶段

- 教师首次设置密码与登录鉴权属于阶段 2。
- 网卡枚举、防火墙引导、备份恢复完整流程属于阶段 2。
- 学生导入、签到、公告、问答、作业等业务模块按后续阶段推进。
- 后端 WebSocket 业务通道将在实时功能阶段接入。
