# ROADMAP.md

# Fire Intelligence Platform 开发路线图

本文档定义 Fire Intelligence Platform 的长期开发路线图，描述产品的演进方向，而不是具体的编码任务。

各功能的详细实现要求维护在 `specs/` 目录下的独立规格文档中，目录结构见下方"规格文档"章节。

路线图应保持稳定；各规格文档可独立演进。

---

# 愿景

构建完整的 AI 消防检查平台，在检查员的整个工作流程中提供辅助：

准备 → 检查 → 取证 → 文书生成 → 知识检索 → 复核 → 统计 → 管理 → 持续的 AI 辅助

---

# 开发原则

按里程碑逐个推进。每个里程碑必须：

- 不破坏已有功能
- 保持项目可构建
- 遵循 AGENTS.md
- 遵循 ARCHITECTURE.md
- 遵循 AI_CONTEXT.md
- 遵循 API.md
- 遵循 DATABASE.md

在当前里程碑达到可用状态之前，不开始后续里程碑。

---

# Milestone 1：基础平台

## 目标

搭建稳定的技术基础。

## 范围

前端

- 项目初始化
- 路由
- 布局
- 导航
- 主题
- 共享组件

后端

- FastAPI 初始化
- 配置
- 日志
- API 约定
- 错误处理

基础设施

- 数据库
- 对象存储
- 认证
- 环境变量配置

## 交付物

- 稳定的前端
- 稳定的后端
- 用户认证
- 健康检查接口
- API client
- 共享布局

---

# Milestone 2：消防检查工作流

## 目标

支持日常检查工作。

## 范围

- Inspection Record
- Photo Report
- Interview Record
- Statistics
- Settings

## 交付物

用户可以：

- 上传检查材料
- 管理检查记录
- 编辑生成的内容
- 下载文书

---

# Milestone 3：消防法规知识库

## 目标

提供法规检索与智能问答。

## 范围

- 文档解析（Document Parsing）
- 语义切分（Semantic Chunking）
- Embedding
- Retriever
- Reranker
- Fire Regulation QA
- 知识库管理

## 交付物

用户可以：

- 上传法规文档
- 重建索引
- 检索法规
- 提问法律问题
- 获得带引用来源的回答

---

# Milestone 4：AI 文书生成

## 目标

自动生成正式检查文书。

## 范围

- Inspection Record 生成
- Photo Report 生成
- Interview Record 生成
- 模板渲染（Template Rendering）
- 文书下载

AI 处理管线：Video → Vision → OCR → LLM → 结构化数据 → Word Template → 下载

## 交付物

支持自动生成：

- 检查记录
- 影像报告
- 询问笔录

---

# Milestone 5：智能工作流

## 目标

自动化检查工作流程。

## 范围

- Task Queue
- Workflow Engine
- Background Processing
- AI Task Management
- Notification
- Batch Processing

## 交付物

支持：

- 异步 AI 任务
- 长时间运行的任务
- 工作流编排

---

# Milestone 6：企业管理

## 目标

支持企业级部署。

## 范围

- 组织（Organizations）
- 部门（Departments）
- 角色管理
- 权限管理
- 审计日志
- 操作日志
- Statistics

## 交付物

支持多组织；支持细粒度权限。

---

# Milestone 7：平台工程化

## 目标

提升可靠性与部署能力。

## 范围

- Docker
- CI/CD
- 监控
- 备份
- 性能优化
- 缓存
- Task Queue
- 部署

## 交付物

支持生产环境部署。

---

# Milestone 8：AI 平台

## 目标

构建可复用的 AI 平台。

## 范围

- Prompt 管理
- 模型管理
- Agent
- Multi-Agent
- MCP
- 评估（Evaluation）
- 模型路由（Model Routing）
- 插件系统
- 工作流编辑器

## 交付物

平台能够在不做重大架构调整的情况下支持未来的 AI 能力。

---

# 规格文档

详细需求独立维护在 `specs/` 目录：

```text
specs/
├── _common.md
├── authentication.md
├── dashboard.md
├── regulation-qa.md
├── inspection-record.md
├── photo-report.md
├── interview-record.md
├── knowledge-base.md
├── settings.md
└── workflow.md
```

跨功能公共约定（角色权限、任务轮询、文件上传、AI 通用约束、安全日志、通用验收标准）集中维护在 `_common.md`，各功能规格引用而不复制。

每份功能规格只包含本功能独有内容：

- 目的与范围
- 功能要求与业务规则
- 字段清单（如有）
- UI 结构
- API 端点（schema 见 API.md）
- 数据影响
- 验收标准
