# Inspection Record（检查记录）

## 目的与范围

将检查现场视频与检查人员的可选补充说明，通过后端异步 AI 任务转换为结构化、可审阅的检查记录，并由后端生成 Word 文书。本功能减少誊录工作，但检查人员对最终内容负责。

范围（v1）：上传一个检查视频、填写可选备注、提交并监控异步 AI 任务、获取结构化草稿、审阅编辑记录字段与检查项、保存、生成并下载定稿文书；提供记录列表页作为入口。

范围外：多源视频、实时现场指导、离线编辑、电子签名、自动上报外部政务系统、未经用户审阅自动定稿。

## 角色与权限

通用规则见 specs/_common.md。本功能无额外角色要求：定稿、归档、下载操作均需后端授权校验，前端不得仅凭隐藏按钮放行。

## 功能要求

### 上传与提交

- 页面通过统一上传组件接受一个视频，使用文件类别的「视频」类（白名单与大小上限见 API.md §9）。
- 展示所选文件名与大小；提交前可替换或移除文件。
- 备注（`remarks`）可选，须与 AI 提取的证据在界面上明显区分。
- 上传与生成请求必须防止意外重复提交。

### 任务进度

- 提交生成请求返回 `task_id`；轮询协议、终态停止、失败展示与刷新恢复见 specs/_common.md，`completed` 后按 `result_data.record_id` 加载结构化草稿。
- 进度展示状态、百分比与当前阶段（均以后端返回为准，不伪造）。
- 视频处理流水线（抽帧与音频 → Vision → OCR → 语音转写 → 证据归一化 → 法规检索 → LLM 结构化抽取 → JSON 校验）与组件职责见 AI_CONTEXT.md。

### 检查项（Findings）编辑

- 定稿前可新增、编辑、排序、删除检查项。
- 每条检查项的类型、位置、描述、法律依据、整改要求、严重程度独立维护。
- 删除有内容的检查项时必须确认。

### 保存、定稿与下载

- 保存经后端持久化结构化记录；UI 明确展示是否有未保存更改，并给出保存成功 / 失败反馈。
- 文书生成必须使用已保存的结构化数据；下载使用后端生成的文书，前端不生成 Word。
- `finalized` 记录不得静默覆盖（更新冲突返回 `409`）；重新生成文书必须保留历史版本（版本规则见 DATABASE.md `generated_documents` 表）。

## 业务规则（本功能独有）

通用 AI 约束（不编造、证据分离、prompt 不下发、结构化 JSON 输出、定稿前可编辑）见 specs/_common.md，以下为检查记录独有规则：

- AI 生成内容在授权用户审阅前一律为草稿。
- 不得编造被检查单位、地址、检查人员、联系方式、检查日期、违法事实、法律依据或整改要求；缺失字段留空或要求用户确认，禁止填入貌似合理的值。
- 启用 RAG 时，法律依据必须基于检索到的权威材料，禁止模型凭想象作答。
- 低置信度结论必须标注为需人工复核。
- 结构化数据库记录是业务事实源，Word 文书只是输出；文书渲染内容必须与已保存的审阅版本一致。

## 字段清单（Structured Draft）

结构化草稿包含以下 13 个字段，是全仓库唯一的字段清单定义（存储定义权在 DATABASE.md `inspection_records` / `inspection_record_items` 表）：

1. `record_number` — 记录编号
2. `title` — 标题
3. `inspection_unit` — 被检查单位
4. `inspection_address` — 检查地址
5. `inspection_date` — 检查日期
6. `inspector_names` — 检查人员姓名（数组）
7. `contact_person` / `contact_phone` — 联系人及电话
8. `items` — 检查发现问题（findings 列表）
9. `legal_basis` — 法律依据（按检查项维护）
10. `correction_requirement` — 整改要求（按检查项维护）
11. `summary` — 检查情况概述
12. `conclusion` — 检查结论
13. `status` — 记录状态

每条检查项（item）字段：`item_type`、`location`、`description`、`legal_basis`、`correction_requirement`、`severity`、`sort_order`。

`status` / `item_type` / `severity` 枚举取值定义权在 DATABASE.md。

## UI 结构

列表页作为入口（按状态过滤、进入详情）；详情页按 `上传与备注 → 任务进度 → 记录头字段 → 检查项编辑器 → 概述与结论 → 保存 / 生成 / 下载操作` 组织。关键交互：

- 分阶段进度文案；未保存更改提示；保存成功 / 失败反馈。
- 删除检查项、覆盖定稿等危险操作需确认。
- 必填数据无效或保存中时禁用最终操作。
- 生成完成不代表内容已核实，UI 不得暗示 AI 内容已被验证。

## API 端点

请求/响应 schema 见 API.md §4.1 与 §8，本文件不复制：

- `POST /api/inspection-record/generate` — 提交视频与 `remarks`（`multipart/form-data`），返回 `task_id`。
- `GET /api/inspection-record` — 记录列表（分页、按 `status` 过滤）。
- `GET /api/inspection-record/{id}` — 记录详情。
- `PUT /api/inspection-record/{id}` — 更新字段与检查项（`items` 为整体替换语义；`finalized` 冲突返回 `409`）。
- `GET /api/inspection-record/{id}/download` — 下载后端生成的 Word 文书（文件流）。
- `GET /api/tasks/{task_id}` — 任务轮询。

## 数据影响

涉及表（定义权在 DATABASE.md）：`inspection_records`（结构化记录）、`inspection_record_items`（检查项）、`uploaded_files`（视频元数据）、`ai_tasks`（生成状态与结构化结果）、`generated_documents`（版本化文书元数据）、`audit_logs`（创建 / 编辑 / 定稿 / 下载审计）。

- 多记录写入必须使用事务；文件二进制存对象存储，不入库。
- 抽帧与音频等中间产物用后清理（见 specs/_common.md）。
- `remarks` 长度上限由后端配置；电话与日期校验不得破坏合法的地区格式。
- 定稿必填字段由后端业务规则定义。

## 错误处理（本功能独有）

通用错误约定见 specs/_common.md。

- 处理超时：保留任务引用，支持重试或刷新状态。
- Vision / OCR / 语音 / LLM 部分阶段失败：标识失败阶段并保留可用证据。
- 保存冲突（`409`）：保留用户编辑并提供重载 / 对比。
- 模板失败：保留结构化记录并允许重新生成文书；下载失败保留文书元数据，允许重试。

## 验收标准

- [ ] 有效视频与可选备注创建一个生成任务，完成后解析为结构化检查记录。
- [ ] 记录字段与检查项可编辑并保存；删除检查项有确认。
- [ ] 缺失或不确定的证据不被编造的事实替代；低置信度结论标注人工复核。
- [ ] 定稿文书内容与已保存的审阅记录一致；`finalized` 文书版本化而非静默覆盖。
- [ ] 文书由后端生成与下载；列表页可按状态过滤并进入详情。
- [ ] 通用验收标准见 specs/_common.md。
