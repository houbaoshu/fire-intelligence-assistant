# PROJECT.md

# Fire Intelligence Platform

## Overview

Fire Intelligence Platform is an AI-powered assistant for fire safety inspection officers.

The project digitizes the entire inspection workflow and integrates AI to improve document generation, knowledge retrieval, and inspection efficiency.

The system follows a Frontend + Backend architecture.

The frontend is responsible for user interaction.

The backend is responsible for AI reasoning and business logic.

---

# Technology Stack

## Frontend

- React
- TypeScript
- Vite
- TailwindCSS
- shadcn/ui
- TanStack Query

## Backend

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic

## AI

- OpenAI Compatible APIs
- Qwen
- DeepSeek
- GPT
- Vision Models

## Knowledge Base

- Chroma
- Local Embedding Models
- Reranker

## Storage

- PostgreSQL
- Supabase Storage

---

# Project Goals

The system should eventually support:

✓ Fire regulation QA

✓ Inspection record generation

✓ Photo report generation

✓ Interview record generation

✓ Knowledge base retrieval

✓ OCR

✓ Video understanding

✓ AI-assisted report generation

✓ User authentication

✓ Statistics dashboard

---

# Overall Architecture

```text
Frontend

↓

FastAPI

↓

AI Services

↓

RAG

↓

Database

↓

Storage
```

---

# Frontend Modules

Target frontend modules:

Dashboard

Fire Regulation QA

Inspection Record

Photo Report

Interview Record

Knowledge Base

Statistics

Settings

Authentication

---

# Backend Modules

Target backend modules:

Authentication

User Management

Inspection Records

Photo Reports

Interview Records

Knowledge Base

AI Services

OCR

Vision

Document Generation

Statistics

---

# AI Architecture

LLM

Responsible for:

- Question answering
- Text generation
- Report generation

Vision

Responsible for:

- Image understanding
- Video understanding

OCR

Responsible for:

- Text extraction

RAG

Responsible for:

- Knowledge retrieval

Embedding

Responsible for:

- Vector generation

Reranker

Responsible for:

- Retrieval ranking

---

# Knowledge Base Workflow

```text
Documents

↓

Parsing

↓

Chunking

↓

Embedding

↓

Vector Database

↓

Retrieval

↓

Reranking

↓

LLM
```

Target document types:

- PDF
- DOC
- DOCX
- PPT
- PPTX
- TXT
- Markdown

Future:

- XLSX

The currently approved upload contract in `API.md` includes PDF, DOC, DOCX, PPT, and PPTX only. TXT and Markdown require an API contract update before implementation.

---

# Video Workflow

```text
Upload Video

↓

Extract Frames

↓

Vision Model

↓

OCR

↓

LLM

↓

Generate Report

↓

Word Template

↓

Download
```

---

# Document Generation Workflow

Inspection Record

Video

↓

AI Extraction

↓

Structured Fields

↓

User Review

↓

Word Template

↓

Download

Photo Report

Video

↓

Key Frames

↓

Vision

↓

Caption

↓

Word Template

↓

Download

Interview Record

Audio / Video

↓

Speech Recognition

↓

LLM

↓

Structured Interview

↓

Word Template

↓

Download

---

# Backend Responsibilities

The backend owns:

Business Logic

AI

OCR

Video Processing

Vision

Knowledge Retrieval

Document Generation

Authentication

Database

Storage

The frontend should never duplicate backend logic.

---

# Current Development Status

Roadmap Milestones 1–8 are implemented for the current specifications. The platform provides
authenticated inspection, photo-report, interview, knowledge, statistics, task, enterprise, and
AI-platform APIs plus corresponding inspector-facing workflows. Long-running processing is durable
and recoverable in the supported single-worker deployment topology. AI capabilities use configured
OpenAI-compatible providers and fail explicitly when a required capability is unavailable.

## Implementation Checklist

- [x] Authentication
- [x] Dashboard
- [x] Fire Regulation QA
- [x] Inspection Record
- [x] Photo Report
- [x] Interview Record
- [x] Knowledge Base
- [x] Statistics
- [x] Settings

Update this checklist continuously.

---

# API Convention

RESTful API

JSON Response

Long-running AI tasks return:

task_id

The frontend polls task status.

---

# Task Status

Possible task states:

pending

queued

processing

completed

failed

cancelled

---

# Environment Variables

Frontend

VITE_API_BASE_URL

Implemented backend foundation

APP_ENVIRONMENT

APP_DATABASE_URL

APP_STORAGE_BACKEND

APP_STORAGE_ROOT

APP_AUTH_SECRET_KEY

APP_ACCESS_TOKEN_MINUTES

APP_REFRESH_TOKEN_DAYS

APP_REGISTRATION_ENABLED

APP_CORS_ORIGINS

APP_LOG_LEVEL

AI configuration

APP_AI_BASE_URL

APP_AI_API_KEY

APP_LLM_MODEL

APP_VISION_MODEL

APP_SPEECH_MODEL

APP_EMBEDDING_MODEL

SUPABASE_URL

SUPABASE_KEY

Example environment files exist in `frontend/.env.example` and `backend/.env.example`. Production deployments must supply `APP_AUTH_SECRET_KEY`; development creates a git-ignored local signing key when one is not supplied.

---

# Coding Principles

Prefer reuse.

Avoid duplication.

Keep frontend lightweight.

Keep backend authoritative.

Keep AI logic centralized.

Keep prompts reusable.

---

# Future Roadmap

Future features include:

- Agent Workflow
- Multi-Agent Collaboration
- MCP Integration
- Fine-grained Permission Management
- Workflow Engine
- Batch Document Generation
- AI Quality Evaluation
- Audit Log
- Model Management
- Prompt Management

---

# Notes

This document should evolve together with the project.

Keep architecture diagrams and module descriptions up to date.

Do not store implementation details that belong in code.

Use this document as the single source of truth for project structure.
