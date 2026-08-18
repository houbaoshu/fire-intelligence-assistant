# MASTER_PROMPT.md

# 代码助手任务入口提示词

你是本项目的代码助手。接到任何开发任务时，按以下要求执行。

## 文档阅读顺序

动手前依次阅读权威文档：

1. AGENTS.md（编码规则与协作约定）
2. docs/ARCHITECTURE.md（技术栈与整体架构）
3. docs/DATABASE.md（数据表结构）
4. docs/API.md（API 契约）
5. docs/AI_CONTEXT.md（AI 工作流）
6. 与当前任务相关的 specs/*.md（功能规格）

## 单一信息源

每类信息只信其权威文件：技术栈以 ARCHITECTURE.md 为准，AI 工作流以 AI_CONTEXT.md 为准，编码规则以 AGENTS.md 为准，API 契约以 API.md 为准，表结构以 DATABASE.md 为准。其他文件中的同类描述仅为引用，不作依据。

## 实施要求

- 动手前先检查现有实现，理解已有代码；复用优先，避免重复逻辑。
- frontend/ 尚未实现：前端由模型依据 ARCHITECTURE.md §4.1/§6 与 specs/ 从零选型并生成，禁止引入低代码平台（Lovable、v0 等）产物。
- 按 ROADMAP.md 的里程碑顺序实现，只实现当前任务要求的里程碑或规格，不做无关里程碑。
- 保持项目可构建、可运行：完成后执行构建、Lint 与类型检查，修复全部错误。
- 保持现有架构；不确定时维持现状，不做大范围重写。
