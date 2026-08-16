# 询问记录（Interview Record）

## 目的与范围

询问记录功能将一段授权询问录音转换为独立保存的转写原文（transcript）、结构化询问记录草稿与后端生成的 Word 文书，在降低转写工作量的同时，要求用户核对说话人、措辞与结构化内容后方可定稿。

范围（v1）：上传单个音频 → 异步转写与结构化 → transcript 与结构化记录独立展示 → 编辑元数据与结构化内容 → 保存 → 生成并下载 Word 文书。

范围外：浏览器内录音、实时转写、身份自动核验、声纹识别、电子签名、翻译、对接外部案件系统、视频来源（v1 仅音频）。

## 角色与权限

通用规则见 specs/_common.md。本功能最低角色：创建与编辑 `inspector`，审阅与定稿 `supervisor`，`viewer` 仅可查看已定稿记录。录音、transcript、结构化记录与生成文书共享同一套后端授权。

## 功能要求

### 上传

- v1 每次只接受一个音频文件（音频类别，扩展名 `.wav` / `.mp3` / `.m4a`；白名单与大小上限见 API.md §9）。
- 表单字段仅 `audio`（必填）与 `remarks`（可选，检查人员补充说明），不接受视频字段。
- 展示所选文件名、大小与媒体类型；提交前可替换或移除；上传进度与处理进度分开展示。

### 任务进度

生成请求返回 `task_id`，前端轮询共享任务端点；终态停止、刷新恢复、结果取数等规则见 specs/_common.md「异步任务与轮询协议」。

### Transcript（转写原文）

- transcript 必须与结构化记录分开保存、独立展示；初始机器转写原文在结构化内容编辑后仍须保留可查。
- 后端返回说话人标签与时间戳时应展示；不确定或听不清的片段必须标注，禁止静默猜测补齐。
- 允许人工校对 transcript 时，UI 必须区分机器原文与人工校订版。

### 结构化记录

- 用户必须能审阅、编辑、保存全部生成字段，之后方可定稿。
- `started_at` 不得晚于 `ended_at`；定稿必填字段由后端业务规则定义。

### 文书生成

- 文书必须由已保存的结构化数据渲染，禁止用 transcript 原文顶替结构化记录。
- 使用后端 Word 模板；已定稿记录重新生成必须保留历史版本（见 DATABASE.md `generated_documents`）。

### AI 处理管线

`音频 → 语音识别 → 说话人分离（技术可行时）→ 带置信度标注的 transcript → LLM 结构化抽取 → 输出校验 → 记录草稿`。通用 AI 约束见 specs/_common.md，组件边界见 AI_CONTEXT.md。

## 业务规则（本功能独有）

- 系统不得虚构说话人、陈述、时间、地点、身份或承认事项；听不清的语音必须标注为不确定或无法听清。
- 说话人归属在用户确认前一律为草稿；无用户确认的证据时，说话人标签不得转为具体身份。
- 源录音、transcript、结构化询问记录是三个独立产物，任一编辑不得静默改动其他两者。
- 清理标点与口头语不得改变实质含义；不得把模糊陈述改写为更确定的陈述。
- 结构化问答内容应尽可能可追溯到 transcript 证据。
- 未经明确授权审阅不得定稿；已定稿记录不得被静默覆盖。

### 错误处理（本功能特有）

- 无可辨识语音：返回明确结果，禁止编造 transcript。
- 转写部分失败：保留可用片段并标注缺口。
- 说话人分离失败：生成带中性说话人标签的 transcript，不中断整体流程。
- LLM 结构化失败：保留 transcript，允许重新生成。

## 字段清单

完整列定义见 DATABASE.md `interview_records` 表；本功能读写字段：

- `title` 标题、`interviewee_name` 被询问人、`interviewer_names` 询问人列表、`location` 地点、`started_at` / `ended_at` 起止时间；
- `transcript` 转写原文（独立保存，与结构化内容分离）；
- `structured_content` 结构化内容（JSONB，核心为 `questions_and_answers` 问答列表）；
- `status` 状态、`source_task_id` 来源 AI 任务。

`status` 取值：`draft` / `processing` / `generated` / `reviewed` / `finalized` / `archived` / `failed`（定义权在 DATABASE.md）。

## UI 结构

页面按 `上传区 → 任务进度 → 录音 / Transcript 面板 → 结构化记录编辑器 → 保存 / 生成 / 下载` 组织；另有列表页承载记录查询。关键交互：拖拽与文件选择上传；上传与处理指示分离；录音元数据展示（支持时提供受保护回放）；transcript 带说话人与时间戳结构、不确定片段标记；结构化字段可编辑；未保存变更警告与放弃确认。transcript 与结构化记录不得在视觉上呈现为同一份内容。

## API 端点

- `POST /api/interview-record/generate` — 提交音频创建生成任务（multipart 表单：`audio` + `remarks`）。
- `GET /api/interview-record` — 记录列表（分页）。
- `GET /api/interview-record/{id}` — 详情（含 transcript 与 structured_content）。
- `PUT /api/interview-record/{id}` — 保存审阅后的编辑。
- `GET /api/interview-record/{id}/download` — 下载 Word 文书。
- `GET /api/tasks/{task_id}` — 任务轮询。

请求/响应 schema 见 API.md §4.3 与 §8。

## 数据影响

- `interview_records`：transcript、structured_content、元数据与状态。
- `uploaded_files`：源录音与生成文件的元数据。
- `ai_tasks`：转写与生成任务进度。
- `generated_documents`：版本化产出文书。
- `audit_logs`：访问、编辑、定稿、下载等关键操作留痕。

若需片段级 transcript 编辑或溯源，须先在 DATABASE.md 中设计独立的 transcript 片段表，禁止隐藏在未文档化的 schema 中。

## 验收标准

- [ ] 一个合法音频创建一个生成任务；视频字段被拒绝并返回可读错误。
- [ ] transcript 与结构化记录独立保存、独立展示；机器转写原文在校订后仍可查。
- [ ] 不确定或听不清的片段可见，且不被 AI 编造补齐。
- [ ] 用户可审阅、编辑并保存元数据与结构化内容，保存结果经后端持久化。
- [ ] 生成文书与已保存的审阅内容一致；已定稿文书版本不被静默覆盖。
- [ ] 列表页可分页查询记录；录音、transcript、记录与文书的访问均需后端授权。
- [ ] 通用验收标准见 specs/_common.md。
