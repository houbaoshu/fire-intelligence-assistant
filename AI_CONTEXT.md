# AI_CONTEXT.md

# AI Context

This document describes how AI capabilities are organized in this project.

It defines responsibilities, workflows, and design principles.

It does **not** define specific model names.

Model selection always comes from environment configuration.

---

# AI Principles

The backend owns all AI capabilities.

The frontend is responsible only for:

- User interaction
- Uploading files
- Displaying progress
- Previewing results
- Downloading generated documents

Never implement AI inference in the frontend.

Never duplicate backend AI logic.

---

# AI Pipeline

User

↓

Frontend

↓

Backend

↓

AI Components

↓

Structured Data

↓

Document / Response

The backend orchestrates the entire AI workflow.

---

# AI Components

## Large Language Model (LLM)

Responsibilities

- Question answering
- Structured information extraction
- Report generation
- Document generation
- Text summarization
- JSON generation

The LLM performs reasoning.

It should not perform OCR or vector search.

---

## Vision Model

Responsibilities

- Image understanding
- Video understanding
- Object recognition
- Scene understanding
- Fire inspection analysis

Vision models interpret visual information.

They do not generate final documents.

---

## OCR

Responsibilities

- Extract text from images
- Extract text from video frames
- Preserve original content

OCR only reads text.

Reasoning belongs to the LLM.

---

## Speech Recognition

Responsibilities

- Audio transcription
- Video speech transcription

The transcript is passed to the LLM for further processing.

---

## Embedding Model

Responsibilities

- Generate vector embeddings

Embedding models are only used for retrieval.

Never use embeddings for generation.

---

## Retriever

Responsibilities

Retrieve relevant knowledge from the vector database.

---

## Reranker

Responsibilities

Improve retrieval quality before context is sent to the LLM.

---

## Vector Database

Responsibilities

Store:

- embeddings
- chunk metadata
- document references

Do not store business logic here.

---

# Knowledge Base Workflow

Document

↓

Parsing

↓

Chunking

↓

Embedding

↓

Vector Database

↓

Retriever

↓

Reranker

↓

LLM

↓

Answer

When RAG is enabled:

The LLM must answer from retrieved context whenever possible.

Avoid hallucinations.

---

# Video Workflow

Upload

↓

Frame Extraction

↓

Vision

↓

OCR

↓

LLM

↓

Structured Result

↓

Template Rendering

↓

Download

The frontend never processes videos.

---

# Inspection Record Generation

Input

Video

Output

Inspection Record

Workflow

Video

↓

Vision

↓

OCR

↓

LLM

↓

Structured JSON

↓

User Review

↓

Word Template

↓

Download

---

# Photo Report Generation

Input

Video

Output

Photo Report

Workflow

Video

↓

Key Frame Extraction

↓

Vision

↓

LLM

↓

Photo Captions

↓

Structured JSON

↓

Word Template

↓

Download

---

# Interview Record Generation

Input

Video or Audio

Workflow

Speech Recognition

↓

Transcript

↓

LLM

↓

Structured Interview

↓

Word Template

↓

Download

---

# Fire Regulation QA

Workflow

Question

↓

Retriever

↓

Reranker

↓

LLM

↓

Answer

↓

Citation

Answers should include retrieved evidence whenever available.

---

# Prompt Principles

Prompts belong to the backend.

Do not embed prompts inside frontend components.

Keep prompts reusable.

Prefer structured output.

Intermediate AI outputs should use JSON whenever practical.

---

# Document Templates

Templates are managed by the backend.

Typical location:

backend/data/templates/

The frontend never generates Word documents.

---

# Structured Output

Whenever practical, AI should return structured JSON.

Example

```json
{
  "inspection_address": "",
  "violations": [],
  "photos": [],
  "summary": ""
}
```

Generate documents from structured data rather than free-form text.

---

# Model Configuration

Model providers and model names are configured through environment variables.

Typical configuration includes:

- LLM
- Vision
- OCR
- Embedding
- Reranker

Never hardcode model names in source code.

---

# Error Handling

AI services may fail.

Support:

- retry
- timeout
- cancellation
- partial failure

Never silently ignore AI errors.

---

# Future AI Capabilities

The architecture should support future extensions such as:

- Agent
- Multi-Agent
- Workflow Engine
- MCP
- Tool Calling
- Model Routing
- Prompt Versioning
- Evaluation Pipeline
- Batch Processing

These features should remain modular and loosely coupled.

---

# Design Principles

Keep responsibilities clearly separated.

LLM

↓

Reasoning

Vision

↓

Visual Understanding

OCR

↓

Text Extraction

Embedding

↓

Retrieval

Backend

↓

AI Orchestration

Frontend

↓

User Interface
