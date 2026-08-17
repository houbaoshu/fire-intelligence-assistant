# API.md

# Fire Intelligence Platform API 契约（权威文档）

本文档是后端 API 契约的唯一权威定义：所有端点的路径、请求与响应 schema 仅以本文档为准，`specs/` 只引用本文档，不另行定义契约。后端由 FastAPI 实现；前端不得硬编码任何 API 响应，必须调用本文档定义的端点。

# 1. 通用约定

## 1.1 路径与认证

- 所有业务端点以 `/api` 为前缀；唯一例外是 `GET /health`，不在 `/api` 前缀之下。
- 资源路径使用单数形式（`/api/inspection-record`，而非 `/api/inspection-records`），未经有意的 API 修订不得变更。
- 业务端点要求请求头 `Authorization: Bearer <access_token>`；token 缺失或无效返回 `401`。
- 公开端点白名单（无需认证）：`GET /health`、`POST /api/auth/login`、`POST /api/auth/register`。

## 1.2 请求与响应格式

- 文件上传端点使用 `multipart/form-data`，其余请求体均为 JSON。
- 文件下载端点返回文件流，其余响应均为 JSON；成功响应不包裹通用成功信封。
- ID 一律为 UUID；时间戳一律为 ISO 8601 UTC 格式。

## 1.3 错误信封

所有错误响应使用统一信封，并搭配合适的 HTTP 状态码（400 / 401 / 403 / 404 / 409 / 413 / 500）：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "可读的错误描述"
  }
}
```

常用 `code`：`VALIDATION_ERROR`、`UNAUTHORIZED`、`FORBIDDEN`、`NOT_FOUND`、`TASK_STATE_CONFLICT`、`INVALID_FILE_TYPE`、`FILE_TOO_LARGE`、`INTERNAL_ERROR`。

## 1.4 异步任务

耗时操作（AI 生成、知识库索引）不同步返回结果，而是返回 `task_id`。客户端轮询 `GET /api/tasks/{task_id}`（见第 8 章），任务进入 `completed` / `failed` / `cancelled` 后必须停止轮询。任务完成时，`result_data.record_id` 指向生成的业务记录。

## 1.5 幂等提交（Idempotency-Key）

以下创建任务的端点支持可选请求头 `Idempotency-Key`（最长 200 字符）：

- `POST /api/inspection-record/generate`
- `POST /api/photo-report/generate`
- `POST /api/interview-record/generate`
- `POST /api/knowledge/documents`
- `POST /api/knowledge/rebuild`

语义：同一用户 + 同一端点 + 同一 key 的重复提交返回首个任务的响应（相同的 `task_id` / `document_id`），不再创建重复任务、业务草稿或上传记录；同一 key 携带不同请求体（文件内容或参数不同）返回 `409` + `IDEMPOTENCY_CONFLICT`。未携带该头时行为与此前一致。客户端应在可能重试的提交（网络超时重发、双击等）中生成并复用同一 key。

# 2. Authentication

## 2.1 登录

**`POST /api/auth/login`**（公开）：邮箱密码登录，返回令牌与当前用户。

请求：

```json
{"email": "user@example.com", "password": "user-provided-password"}
```

响应：

```json
{
  "access_token": "jwt-access-token",
  "refresh_token": "jwt-refresh-token",
  "token_type": "bearer",
  "user": {"id": "uuid", "email": "user@example.com", "full_name": "张三", "role": "inspector"}
}
```

`role` 取值见 DATABASE.md `users` 表。凭证无效返回 `401` + `UNAUTHORIZED`。

## 2.2 注册

**`POST /api/auth/register`**（公开）：注册并直接返回令牌。

请求：

```json
{"email": "user@example.com", "password": "user-provided-password", "full_name": "张三"}
```

响应：字段与 2.1 登录响应完全相同（`access_token`、`refresh_token`、`token_type`、`user`）。邮箱已注册返回 `409`。

## 2.3 当前用户

**`GET /api/auth/me`**：返回当前 token 对应的用户。无请求体。

响应：

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "张三",
  "role": "inspector",
  "permissions": ["knowledge.read", "record.create", "record.read", "statistics.read", "task.manage"]
}
```

- `permissions`（M6 追加字段）：当前用户角色在权限矩阵中的生效权限码列表（权限码目录见 §11.4）。前端可据此控制功能入口可见性；授权始终以服务端校验为准。

## 2.4 刷新 Token

**`POST /api/auth/refresh`**：用 `refresh_token` 换取新的 `access_token`。

请求：

```json
{"refresh_token": "jwt-refresh-token"}
```

响应：

```json
{"access_token": "new-jwt-access-token", "token_type": "bearer"}
```

`refresh_token` 无效或过期返回 `401`。

# 3. Health

**`GET /health`**（公开，不在 `/api` 前缀之下）：后端存活探针。无请求体。

响应：

```json
{"status": "ok"}
```

# 4. 业务记录（Inspection / Photo / Interview）

三组业务记录共享同一模式：`generate` 上传素材并返回 `task_id`（异步，轮询见第 8 章），`GET` 列表 / 详情，`PUT` 更新，`download` 下载后端生成的 Word 文档。`generate` 支持 `Idempotency-Key` 幂等提交头（见 §1.5）。

## 4.1 Inspection Record（检查记录）

字段定义见 DATABASE.md `inspection_records` / `inspection_record_items` 表；记录 `status`、`item_type`、`severity` 枚举以该表为准。

**`POST /api/inspection-record/generate`**（生成）：上传现场视频，后端异步执行视频分析、OCR、语音转写与 LLM 生成。

请求（`multipart/form-data`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| video | file | 是 | 现场视频，`.mp4` / `.mov`，≤ 500MB |
| remarks | string | 否 | 检查人员补充说明 |

响应：

```json
{"task_id": "uuid"}
```

**`GET /api/inspection-record`**（列表）：返回当前用户有权查看的记录，按创建时间倒序。

查询参数：`page`（默认 1）、`page_size`（默认 20，最大 100）、`status`（可选，按记录状态过滤）。

响应：

```json
{
  "items": [
    {"id": "uuid", "record_number": "JC-2026-0001", "title": "某商场消防检查记录", "inspection_unit": "某商场", "inspection_date": "2026-01-01T00:00:00Z", "status": "draft", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**`GET /api/inspection-record/{id}`**（详情）：记录不存在返回 `404`。

响应：

```json
{
  "id": "uuid",
  "record_number": "JC-2026-0001",
  "title": "某商场消防检查记录",
  "inspection_unit": "某商场",
  "inspection_address": "某市某区某路 1 号",
  "inspection_date": "2026-01-01T00:00:00Z",
  "inspector_names": ["张三", "李四"],
  "contact_person": "王五",
  "contact_phone": "13800000000",
  "summary": "检查情况概述",
  "conclusion": "检查结论",
  "status": "draft",
  "items": [
    {"id": "uuid", "item_type": "violation", "location": "一层东侧", "description": "安全出口被锁闭", "legal_basis": "《中华人民共和国消防法》第二十八条", "correction_requirement": "立即解除锁闭", "severity": "high", "sort_order": 1}
  ],
  "source_task_id": "uuid",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

**`PUT /api/inspection-record/{id}`**（更新）：可编辑字段为详情中的 `title`、`inspection_unit`、`inspection_address`、`inspection_date`、`inspector_names`、`contact_person`、`contact_phone`、`summary`、`conclusion`、`status`、`items`；均为可选，未提交字段保持不变。`items` 为整体替换语义：新增 item 不传 `id`，省略已有 item 的 `id` 即删除。`finalized` 记录不得静默覆盖，冲突返回 `409`。

请求示例：

```json
{
  "title": "某商场消防检查记录（修订）",
  "status": "reviewed",
  "items": [
    {"item_type": "violation", "location": "一层东侧", "description": "安全出口被锁闭", "legal_basis": "《中华人民共和国消防法》第二十八条", "correction_requirement": "立即解除锁闭", "severity": "high", "sort_order": 1}
  ]
}
```

响应：更新后的完整记录，结构同详情。

**`GET /api/inspection-record/{id}/download`**（下载）：下载后端依据已保存结构化数据生成的 Word 文档。响应为文件流而非 JSON：

- `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `Content-Disposition: attachment; filename="inspection-record-{record_number}.docx"`

文档尚未生成返回 `409`，记录不存在返回 `404`。

## 4.2 Photo Report（拍照报告）

字段定义见 DATABASE.md `photo_reports` / `photo_report_images` 表。

**`POST /api/photo-report/generate`**（生成）：上传一段检查视频，后端异步抽帧、去重与质量筛选产出候选帧，并执行图像识别与报告生成。

请求（`multipart/form-data`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| video | file | 是 | 检查视频，单个，`.mp4` / `.mov`，≤ 500MB |
| remarks | string | 否 | 检查人员补充说明 |

响应：

```json
{"task_id": "uuid"}
```

**`GET /api/photo-report`**（列表）：查询参数与分页响应信封同 4.1 列表，`items` 元素字段如下。

```json
{"id": "uuid", "title": "某厂房消防拍照报告", "inspection_unit": "某厂房", "status": "draft", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
```

**`GET /api/photo-report/{id}`**（详情）：报告不存在返回 `404`。

响应：

```json
{
  "id": "uuid",
  "title": "某厂房消防拍照报告",
  "inspection_unit": "某厂房",
  "inspection_address": "某市某区某路 2 号",
  "violation_summary": "隐患概述",
  "status": "draft",
  "images": [
    {"id": "uuid", "uploaded_file_id": "uuid", "frame_timestamp": 12.5, "caption": "疏散通道堆放杂物", "detected_address": "某市某区某路 2 号", "detected_violation": "疏散通道被占用", "is_selected": true, "sort_order": 1, "created_at": "2026-01-01T00:00:00Z"}
  ],
  "source_task_id": "uuid",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

**`PUT /api/photo-report/{id}`**（更新）：可编辑字段为 `title`、`inspection_unit`、`inspection_address`、`violation_summary`、`status`、`images`，均为可选。`images` 按 `id` 匹配逐项更新，仅 `caption`、`is_selected`、`sort_order` 可编辑，不涉及图片增删。

请求示例：

```json
{
  "violation_summary": "隐患概述（修订）",
  "status": "finalized",
  "images": [
    {"id": "uuid", "caption": "疏散通道堆放杂物", "is_selected": true, "sort_order": 1}
  ]
}
```

响应：更新后的完整报告，结构同详情。

**`GET /api/photo-report/{id}/download`**（下载）：契约同 4.1 下载端点，`filename="photo-report-{id}.docx"`。

## 4.3 Interview Record（询问记录）

字段定义见 DATABASE.md `interview_records` 表。v1 仅支持音频来源，不接受视频字段。

**`POST /api/interview-record/generate`**（生成）：上传询问录音，后端异步执行语音转写与结构化生成。

请求（`multipart/form-data`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| audio | file | 是 | 询问录音，`.wav` / `.mp3` / `.m4a`，≤ 200MB |
| remarks | string | 否 | 检查人员补充说明 |

响应：

```json
{"task_id": "uuid"}
```

**`GET /api/interview-record`**（列表）：查询参数与分页响应信封同 4.1 列表，`items` 元素字段如下。

```json
{"id": "uuid", "title": "某单位负责人询问记录", "interviewee_name": "赵某", "status": "draft", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
```

**`GET /api/interview-record/{id}`**（详情）：记录不存在返回 `404`。

响应：

```json
{
  "id": "uuid",
  "title": "某单位负责人询问记录",
  "interviewee_name": "赵某",
  "interviewer_names": ["张三", "李四"],
  "location": "某单位会议室",
  "started_at": "2026-01-01T09:00:00Z",
  "ended_at": "2026-01-01T09:30:00Z",
  "transcript": "询问全程转写文本",
  "structured_content": {"questions_and_answers": [{"question": "……", "answer": "……"}]},
  "status": "draft",
  "source_task_id": "uuid",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

`structured_content` 为 JSONB，内部结构由后端生成，随 DATABASE.md 对应表约束演进。

**`PUT /api/interview-record/{id}`**（更新）：可编辑字段为 `title`、`interviewee_name`、`interviewer_names`、`location`、`started_at`、`ended_at`、`transcript`、`structured_content`、`status`，均为可选，未提交字段保持不变。

请求示例：

```json
{"transcript": "经人工校对的转写文本", "structured_content": {"questions_and_answers": [{"question": "……", "answer": "……"}]}, "status": "reviewed"}
```

响应：更新后的完整记录，结构同详情。

**`GET /api/interview-record/{id}/download`**（下载）：契约同 4.1 下载端点，`filename="interview-record-{id}.docx"`。

# 5. Regulation QA（法规问答）

**`POST /api/qa/query`**：基于 RAG 检索知识库后由 LLM 生成回答；检索不得跳过，回答必须附引用来源。

请求：

```json
{"question": "消防安全出口被锁闭时适用哪些规定？"}
```

响应：

```json
{
  "answer": "根据《中华人民共和国消防法》第二十八条……",
  "sources": [
    {"document_id": "uuid", "title": "中华人民共和国消防法", "article": "第二十八条", "page": 12, "excerpt": "任何单位、个人不得……锁闭、封堵安全出口。", "effective_date": "2021-04-29"}
  ]
}
```

`sources` 元素字段以本契约为准，前端不得假设后端返回其他字段。无可靠来源时 `sources` 为空数组，后端不得编造引用。

# 6. Knowledge Base（知识库）

字段定义见 DATABASE.md `knowledge_documents` 表；文档 `status` 取值（`uploaded` / `parsing` / `indexing` / `indexed` / `failed` / `outdated`）以该表为准。

**`GET /api/knowledge/documents`**（列表）：查询参数 `page` / `page_size` / `status`，语义同 4.1 列表。

响应：

```json
{
  "items": [
    {"id": "uuid", "title": "中华人民共和国消防法", "document_type": "regulation", "status": "indexed", "version": "2021 修正", "issuing_authority": "全国人民代表大会常务委员会", "effective_date": "2021-04-29", "chunk_count": 320, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

**`POST /api/knowledge/documents`**（上传）：上传知识库源文档；解析与索引为异步任务（`task_type = knowledge_indexing`）。

请求（`multipart/form-data`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| file | file | 是 | 文档文件，类型与大小限制见第 9 章 |

响应：

```json
{"document_id": "uuid", "task_id": "uuid"}
```

**`DELETE /api/knowledge/documents/{id}`**（删除）：软删除文档并移除其索引数据。无请求体。

响应：

```json
{"id": "uuid", "deleted": true}
```

**`POST /api/knowledge/rebuild`**（重建索引）：对全部知识库文档重建向量索引，异步任务（`task_type = knowledge_reindexing`）。无请求体。

响应：

```json
{"task_id": "uuid"}
```

**`GET /api/knowledge/status`**（状态）：返回知识库聚合计数。无请求体。

响应：

```json
{
  "document_count": 10,
  "indexed_count": 8,
  "indexing_count": 1,
  "failed_count": 1,
  "last_indexed_at": "2026-01-01T00:00:00Z"
}
```

尚无文档时各计数为 0，`last_indexed_at` 为 `null`。

# 7. Statistics（统计）

**`GET /api/statistics`**：返回按当前用户权限范围聚合的只读统计。所有计数来自后端既有业务表并遵循软删除规则；前端不得硬编码指标。无请求体。

响应：

```json
{
  "scope": "personal",
  "generated_at": "2026-01-01T00:00:00Z",
  "records": {
    "inspection_records": {"total": 12, "by_status": {"draft": 2, "generated": 1, "reviewed": 1, "finalized": 8}},
    "photo_reports": {"total": 5, "by_status": {"draft": 1, "finalized": 4}},
    "interview_records": {"total": 3, "by_status": {"draft": 1, "finalized": 2}}
  },
  "tasks": {"total": 20, "by_status": {"pending": 1, "processing": 1, "completed": 15, "failed": 2, "cancelled": 1}},
  "knowledge": {"document_count": 10, "indexed_count": 8, "indexing_count": 1, "failed_count": 1},
  "generated_documents": {"total": 30}
}
```

- `scope` 表示数据范围：`personal` / `team` / `organization` / `system`，由后端按用户角色决定，前端过滤不能扩大范围。
- `by_status` 只包含有数据的键；某状态计数为 0 时键可省略，前端必须区分「零」「缺失」与「不可用」。
- `tasks.by_status` 的取值与 DATABASE.md `ai_tasks` 表状态枚举一致。

# 8. Tasks（异步任务）

任务数据定义权属于 DATABASE.md `ai_tasks` 表。任务状态枚举见该表，取值为 `pending`、`queued`、`processing`、`completed`、`failed`、`cancelled`。`task_type` 取值为 `inspection_record_generation`、`photo_report_generation`、`interview_record_generation`、`speech_transcription`、`video_analysis`、`document_generation`、`knowledge_indexing`、`knowledge_reindexing`。

**`GET /api/tasks/{task_id}`**（查询）：任务不存在或无权限返回 `404`。

响应：

```json
{
  "task_id": "uuid",
  "task_type": "inspection_record_generation",
  "status": "processing",
  "progress": 42,
  "current_stage": "video_analysis",
  "result_data": null,
  "error_code": null,
  "error_message": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

- `progress` 取值 0–100，单次执行内单调不减。
- `completed` 时 `result_data` 携带安全结果引用，生成类任务为 `{"record_id": "uuid"}`。
- `failed` 时 `error_code` 与 `error_message` 必填，`error_message` 必须可读且不含敏感信息。

**`GET /api/tasks`**（列表）：返回当前用户有权查看的最近任务，按创建时间倒序。

查询参数：`limit`（默认 20，最大 100）、`status`（可选，按任务状态过滤）。

响应：

```json
{
  "items": [
    {"task_id": "uuid", "task_type": "photo_report_generation", "status": "completed", "progress": 100, "current_stage": null, "result_data": {"record_id": "uuid"}, "error_code": null, "error_message": null, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
  ],
  "total": 1
}
```

**`POST /api/tasks/{task_id}/retry`**（重试）：仅 `failed` / `cancelled` 状态允许重试，其他状态返回 `409` + `TASK_STATE_CONFLICT`。重试创建新的任务实例，原任务保留用于审计；重试不得静默重复生成已定稿的业务记录或文档。无请求体。

响应：

```json
{"task_id": "new-task-uuid"}
```

**`POST /api/tasks/{task_id}/cancel`**（取消）：仅 `pending` / `queued` / `processing` 状态允许取消，其他状态返回 `409` + `TASK_STATE_CONFLICT`。取消为尽力而为：后端确认执行状态已调和后才将任务标记为 `cancelled`，已提交的成果不会被隐式删除。无请求体。

响应：

```json
{"task_id": "uuid", "status": "cancelled"}
```

## 8.1 状态机与执行追踪（M5）

- 任务状态转移由后端统一的转移表校验（见 specs/workflow.md 与 backend README），非法转移返回 `409` + `TASK_STATE_CONFLICT`。
- `ai_tasks` 的 `attempt_count` / `max_attempts` / `worker_id` / `lease_expires_at` / `queued_at` / `idempotency_key` / `request_hash` 为内部执行追踪字段（定义见 DATABASE.md），**不暴露**于上述任务响应契约；前端只消费 §8 既有字段。
- 重试次数达到上限后任务以 `failed` + `error_code=RETRY_EXHAUSTED` 终态停止（死信等价流程），`error_message` 可读并保留原始错误码。
- worker 崩溃导致的卡住任务由 reaper 自动恢复：可重试的重新入队，达到上限的以 `failed` + `error_code=STALE_TASK_RECOVERED` 终态落库。
- 任务进入终态时向创建者写入通知（见第 10 章）。

# 9. File Upload Rules（文件上传规则）

所有文件上传端点必须依次校验：扩展名白名单、MIME 类型与扩展名一致、文件签名（magic bytes）与声明类型一致、文件大小不超过上限。任一校验失败即拒绝：类型不符返回 `400` + `INVALID_FILE_TYPE`，超限返回 `413` + `FILE_TOO_LARGE`，错误信息必须可读，不得静默忽略。前端上传前应按本表预校验扩展名与大小，展示上传进度，并展示后端返回的可读错误。

| 类别 | 扩展名 | 单文件大小上限 | 用途 |
|---|---|---|---|
| 视频 | `.mp4`、`.mov` | 500MB | 检查记录生成、拍照报告生成（抽帧） |
| 图片 | `.jpg`、`.jpeg`、`.png` | 20MB | 预留（v1 无上传入口） |
| 音频 | `.wav`、`.mp3`、`.m4a` | 200MB | 询问记录生成 |
| 文档 | `.pdf`、`.doc`、`.docx`、`.ppt`、`.pptx`、`.txt`、`.md` | 50MB | 知识库上传 |


# 10. Notifications（通知）

通知数据定义权属于 DATABASE.md `notifications` 表。任务进入终态（`completed` / `failed` / `cancelled`）时，后端向任务创建者写入一条通知（`type` 分别为 `task_completed` / `task_failed` / `task_cancelled`）。通知内容可读且不含敏感信息；用户只能读取与操作自己的通知，无额外角色要求。

**`GET /api/notifications`**（列表）：返回当前用户的通知，按创建时间倒序。

查询参数：`unread_only`（bool，默认 `false`）、`page`（默认 1）、`page_size`（默认 20，最大 100）。

响应：

```json
{
  "items": [
    {"id": "uuid", "type": "task_completed", "title": "检查记录生成已完成", "body": "您的检查记录生成任务已完成，可前往查看生成结果。", "entity_type": "inspection_record", "entity_id": "uuid", "read_at": null, "created_at": "2026-01-01T00:00:00Z"}
  ],
  "total": 5,
  "unread_count": 2,
  "page": 1,
  "page_size": 20
}
```

- `entity_type` / `entity_id` 指向关联业务记录（如 `inspection_record` / `photo_report` / `interview_record` / `knowledge_document`）；无关联业务实体时指向任务本身（`ai_task`）。均可为 `null`。
- `unread_count` 为当前用户全部未读通知数，不受 `unread_only` 与分页影响。

**`POST /api/notifications/{id}/read`**（标记已读）：通知不存在或属于他人返回 `404`。重复标记幂等。无请求体。

响应：

```json
{"id": "uuid", "read_at": "2026-01-01T00:00:00Z"}
```

**`POST /api/notifications/read-all`**（全部已读）：将当前用户全部未读通知标记为已读。无请求体。

响应：

```json
{"updated": 3}
```

# 11. Administration（企业管理，M6）

本章端点均在 `/api/admin` 前缀下，按权限码授权（权限矩阵见 §11.4，默认仅 `admin` 角色持有 `admin.*` 权限）；权限不足返回 `403` + `FORBIDDEN`。组织、部门、用户的增删改与权限矩阵变更全部写入审计日志（`admin.organization.*` / `admin.department.*` / `admin.user.update` / `admin.permission.update`）。数据表定义见 DATABASE.md「表：organizations / departments / permissions / role_permissions」。

## 11.1 组织

**`GET /api/admin/organizations`**（需 `admin.orgs`）：分页列出组织。

查询参数：`page`（默认 1）、`page_size`（默认 20，最大 100）。

响应：

```json
{
  "items": [
    {"id": "uuid", "name": "某市消防救援支队", "code": "FD-001", "description": "描述", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**`POST /api/admin/organizations`**（需 `admin.orgs`）：创建组织。

请求：

```json
{"name": "某市消防救援支队", "code": "FD-001", "description": "可选"}
```

响应：组织对象（字段同上）。`code` 已存在返回 `409` + `ORGANIZATION_CODE_EXISTS`。

**`PUT /api/admin/organizations/{id}`**（需 `admin.orgs`）：更新组织，`name` / `code` / `description` 均可选，仅更新提交的字段。响应：更新后的组织对象。组织不存在返回 `404`；`code` 冲突返回 `409` + `ORGANIZATION_CODE_EXISTS`。

**`DELETE /api/admin/organizations/{id}`**（需 `admin.orgs`）：软删除组织。

响应：

```json
{"id": "uuid", "deleted": true}
```

组织不存在返回 `404`；仍有用户归属该组织时返回 `409` + `ORGANIZATION_HAS_USERS`。

## 11.2 部门

**`GET /api/admin/departments`**（需 `admin.orgs`）：分页列出部门，可加 `organization_id` 过滤。分页信封同 §11.1，item 字段：

```json
{"id": "uuid", "organization_id": "uuid", "name": "防火监督科", "parent_id": null, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"}
```

**`POST /api/admin/departments`**（需 `admin.orgs`）：创建部门。

请求：

```json
{"organization_id": "uuid", "name": "防火监督科", "parent_id": null}
```

响应：部门对象。`organization_id` 不存在返回 `400` + `VALIDATION_ERROR`；`parent_id` 不属于同一组织返回 `400`。

**`PUT /api/admin/departments/{id}`**（需 `admin.orgs`）：更新部门，`name` / `parent_id` 可选（`parent_id` 显式传 `null` 表示清除上级）。响应：更新后的部门对象。`parent_id` 不属于本部门所在组织或等于部门自身返回 `400` + `VALIDATION_ERROR`。

**`DELETE /api/admin/departments/{id}`**（需 `admin.orgs`）：软删除部门，响应 `{"id": "uuid", "deleted": true}`。部门不存在返回 `404`；仍有用户归属该部门时返回 `409` + `DEPARTMENT_HAS_USERS`。

## 11.3 用户

**`GET /api/admin/users`**（需 `admin.users`）：分页列出用户。

查询参数：`page`、`page_size`（同 §11.1）、`organization_id`（可选过滤）、`role`（可选过滤）。

响应：

```json
{
  "items": [
    {"id": "uuid", "email": "user@example.com", "username": null, "full_name": "张三", "role": "inspector", "is_active": true, "organization_id": "uuid", "department_id": null, "last_login_at": "2026-01-01T00:00:00Z", "created_at": "2026-01-01T00:00:00Z"}
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**`PUT /api/admin/users/{id}`**（需 `admin.users`）：更新用户，`role` / `is_active` / `organization_id` / `department_id` 均可选，仅更新提交的字段；`organization_id` / `department_id` 显式传 `null` 表示清除归属。响应：更新后的用户对象（字段同上）。

- `role` 非法（不在 DATABASE.md `users` 角色枚举内）返回 `400` + `VALIDATION_ERROR`。
- 生效的 `department_id` 必须属于生效的 `organization_id`（提交值优先，未提交则取当前值），不一致返回 `400` + `VALIDATION_ERROR`。
- 禁止把当前登录的管理员自己停用或降权（`is_active=false` 或将 `role` 改为非 `admin`），返回 `409` + `SELF_LOCKOUT_FORBIDDEN`。
- 目标用户不存在返回 `404`。

## 11.4 权限矩阵

权限码目录（种子见 `app/services/permission_service.py`）：

| code | 说明 |
|---|---|
| `record.read` | 查看业务记录 |
| `record.create` | 创建并编辑本人业务记录 |
| `record.review` | 审阅可见范围内他人业务记录 |
| `record.finalize` | 定稿业务记录 |
| `knowledge.read` | 查询知识库 |
| `knowledge.manage` | 管理知识库（上传/删除/重建） |
| `task.manage` | 任务重试与取消 |
| `statistics.read` | 查看统计 |
| `admin.users` | 用户管理 |
| `admin.orgs` | 组织与部门管理 |
| `admin.permissions` | 权限矩阵管理 |
| `admin.audit` | 审计日志查询 |

**`GET /api/admin/permissions`**（需 `admin.permissions`）：返回权限目录与生效矩阵。

响应：

```json
{
  "permissions": [{"code": "record.read", "name": "查看业务记录", "description": "..."}],
  "matrix": {"admin": ["..."], "supervisor": ["..."], "inspector": ["..."], "viewer": ["..."]}
}
```

**`PUT /api/admin/permissions/{role}`**（需 `admin.permissions`）：整体替换某角色的权限码集合。

请求：

```json
{"permission_codes": ["record.read", "knowledge.read"]}
```

响应：

```json
{"role": "viewer", "permission_codes": ["knowledge.read", "record.read"]}
```

- `role` 非法返回 `400` + `VALIDATION_ERROR`；`permission_codes` 含未知权限码返回 `400` + `VALIDATION_ERROR`。
- 不允许移除 `admin` 角色的任何 `admin.*` 权限（防止平台被锁死），返回 `409` + `ADMIN_PERMISSION_LOCKED`。

## 11.5 审计日志

**`GET /api/admin/audit-logs`**（需 `admin.audit`）：分页查询审计日志，按创建时间倒序。

查询参数：`page`、`page_size`（同 §11.1）、`user_id`（可选）、`action`（可选，精确匹配）、`entity_type`（可选，精确匹配）。

响应：

```json
{
  "items": [
    {"id": "uuid", "user_id": "uuid", "action": "admin.user.update", "entity_type": "user", "entity_id": "uuid", "request_id": "hex", "ip_address": "127.0.0.1", "details": {"changes": {"role": "supervisor"}}, "created_at": "2026-01-01T00:00:00Z"}
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```
