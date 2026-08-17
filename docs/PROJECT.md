# PROJECT.md

# Fire Intelligence Platform 项目说明

本文档描述项目的定位、目标、模块划分与环境变量。

技术栈见 ARCHITECTURE.md。AI 工作流见 AI_CONTEXT.md。API 契约见 API.md。数据表结构见 DATABASE.md。编码规则见 AGENTS.md。里程碑规划见 ROADMAP.md。

---

# 项目定位

Fire Intelligence Platform 是面向消防安全检查人员的 AI 辅助系统。

项目将检查工作全流程数字化，并通过 AI 提升文书生成、知识检索与检查工作的效率。

系统采用 前端 + 后端 架构：

- 前端负责用户交互
- 后端负责 AI 推理与业务逻辑

---

# 项目目标

系统最终需要支持：

- 消防法规智能问答（Fire Regulation QA）
- 检查记录生成（Inspection Record）
- 影像报告生成（Photo Report）
- 询问笔录生成（Interview Record）
- 知识库检索（Knowledge Base）
- OCR 文字识别
- 视频理解（Video Understanding）
- AI 辅助报告生成
- 用户认证（Authentication）
- 统计看板（Statistics Dashboard）

---

# 前端模块

目标前端模块：

- Dashboard
- Fire Regulation QA
- Inspection Record
- Photo Report
- Interview Record
- Knowledge Base
- Statistics
- Settings
- Authentication

---

# 后端模块

目标后端模块：

- Authentication
- User Management
- Inspection Records
- Photo Reports
- Interview Records
- Knowledge Base
- AI Services
- OCR
- Vision
- Document Generation
- Statistics

---

# 前后端职责划分

后端统一负责业务逻辑、AI、OCR、视频处理、Vision、知识检索、文档生成、认证、数据库与存储。

前端不重复实现任何后端逻辑。详细职责规则见 AGENTS.md。

---

# API 约定

RESTful API，JSON 响应。

长时间运行的 AI 任务返回 task_id，前端轮询任务状态。

详细 API 契约见 API.md，任务状态定义见 DATABASE.md。

---

# 环境变量

目标环境变量名清单：

前端

- VITE_API_BASE_URL

后端

- OPENAI_API_KEY
- LLM_MODEL
- VISION_MODEL
- EMBEDDING_MODEL
- DATABASE_URL
- SUPABASE_URL（仅 Supabase 方案需要）
- SUPABASE_KEY（仅 Supabase 方案需要）

文件存储支持 Supabase Storage 或本地存储，由环境变量配置二选一。

严禁在代码中硬编码任何密钥、密码、URL 或 Token。
