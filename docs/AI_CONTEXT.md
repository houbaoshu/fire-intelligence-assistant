# AI_CONTEXT.md

# AI 组件职责与工作流

本文档描述项目中 AI 能力的组织方式：组件职责边界与工作流步骤。

本文档**不**定义具体模型名称；模型选择一律来自环境变量配置。

---

# AI 基本原则

- 全部 AI 能力归后端所有，由后端统一编排整个 AI 工作流。
- 前端只负责：用户交互、上传文件、展示进度、预览结果、下载生成的文档。
- 整体管线：`User → Frontend → Backend → AI Components → Structured Data → Document / Response`

---

# AI 组件

## Large Language Model (LLM)

职责：

- 问答（Question answering）
- 结构化信息抽取
- 报告生成
- 文档生成
- 文本摘要
- JSON 生成

LLM 负责推理（reasoning）。LLM 不做 OCR，也不做向量检索。

## Vision Model

职责：

- 图像理解
- 视频理解
- 目标识别
- 场景理解
- 消防检查分析

Vision 模型负责解读视觉信息，不生成最终文档。

## OCR

职责：

- 从图像中提取文字
- 从视频帧中提取文字
- 保留原始内容

OCR 只负责读取文字；推理归 LLM。

## Speech Recognition

职责：

- 音频转写
- 视频语音转写

转写文本（transcript）交给 LLM 做进一步处理。

## Embedding Model

职责：

- 生成向量 embeddings

Embedding 模型仅用于检索（retrieval），不用于生成。

## Retriever

职责：

- 从 Vector Database 中检索相关知识。

## Reranker

职责：

- 在上下文送入 LLM 之前提升检索质量。

## Vector Database

职责，存储：

- embeddings
- chunk metadata
- document references

不在这里存放业务逻辑。

---

# 业务工作流

## Knowledge Base Workflow

索引管线：`Document → Parsing → Chunking → Embedding → Vector Database`

查询管线：`Question → Retriever → Reranker → LLM → Answer`

启用 RAG 时，LLM 必须尽可能基于检索到的上下文作答，避免幻觉（hallucination）。

## Video Workflow

输入：用户上传的视频。输出：结构化结果渲染成的文档。

步骤：

1. 前端上传视频，后端接收。
2. Frame Extraction：抽帧。
3. Vision：帧图像理解。
4. OCR：帧内文字提取。
5. LLM：综合分析，产出 Structured Result（JSON）。
6. Template Rendering：套用模板生成文档。
7. 前端提供 Download。

链路：`Upload → Frame Extraction → Vision → OCR → LLM → Structured Result → Template Rendering → Download`

前端不处理视频本身。

## Inspection Record Generation

输入：Video。输出：Inspection Record（检查记录文档）。

步骤：

1. 音频与帧抽取：音频经 Speech Recognition 转写，帧经 Vision 分析画面、OCR 提取文字（语音识别与视觉分析并行）。
2. LLM 综合转写文本与视觉证据，产出 Structured JSON。
3. User Review：用户确认/修改结构化结果。
4. 套用 Word Template 生成文档。
5. Download。

链路：`Video → 音频/帧抽取 →（Speech Recognition ∥ Vision）→ OCR → LLM → Structured JSON → User Review → Word Template → Download`

## Photo Report Generation

输入：Video。输出：Photo Report（照片报告文档）。

步骤：

1. Key Frame Extraction：从视频中提取关键帧。
2. Vision：分析关键帧。
3. LLM：为照片生成 Photo Captions，并产出 Structured JSON。
4. 套用 Word Template 生成文档。
5. Download。

链路：`Video → Key Frame Extraction → Vision → LLM → Photo Captions → Structured JSON → Word Template → Download`

## Interview Record Generation

输入：Audio（v1 仅音频；视频来源为后续版本候选，契约见 API.md）。输出：Interview Record（询问笔录文档）。

步骤：

1. Speech Recognition：语音转写为 Transcript。
2. LLM：整理为 Structured Interview（结构化笔录）。
3. 套用 Word Template 生成文档。
4. Download。

链路：`Speech Recognition → Transcript → LLM → Structured Interview → Word Template → Download`

## Fire Regulation QA

输入：用户关于消防法规的 Question。输出：带 Citation 的 Answer。

链路：`Question → Retriever → Reranker → LLM → Answer → Citation`

凡有可用检索证据时，答案必须附上检索到的依据。

---

# Prompt Principles

- Prompt 归后端所有，不得嵌入前端组件。
- Prompt 保持可复用。
- 优先使用结构化输出；中间态 AI 输出在可行时一律使用 JSON。

---

# Document Templates

模板由后端管理，典型位置：`backend/data/templates/`。前端不生成 Word 文档。

---

# Structured Output

在可行时，AI 一律返回结构化 JSON。示例：

```json
{
  "inspection_address": "",
  "violations": [],
  "photos": [],
  "summary": ""
}
```

文档由结构化数据生成，而不是由自由文本直接拼装。

---

# Model Configuration

模型提供方与模型名称通过环境变量配置。典型配置项包括：

- LLM
- Vision
- OCR
- Embedding
- Reranker

模型名一律走环境变量，不在源代码中硬编码。

---

# Error Handling

AI 服务可能失败，必须支持：

- retry（重试）
- timeout（超时）
- cancellation（取消）
- partial failure（部分失败）

不得静默吞掉 AI 错误。
