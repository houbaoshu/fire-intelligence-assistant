# AGENTS.md

# Fire Intelligence Platform

This repository is an AI-powered fire inspection system.

The project is designed for fire safety inspection officers and provides intelligent document generation, knowledge retrieval, and inspection assistance.

The target repository architecture is designed to contain:

- Lovable frontend
- FastAPI backend
- AI services
- RAG knowledge base
- OCR
- Vision models
- Document generation
- Database
- Object storage

Current implementation status must be determined from the files present in the repository. At present, the repository contains project documentation and specifications only; application code has not been initialized.

Always understand the existing architecture before making changes.

---

# Core Principles

Before writing code:

1. Read the existing implementation.
2. Reuse existing modules.
3. Avoid duplicate logic.
4. Keep changes focused.
5. Preserve backward compatibility whenever possible.

Never rewrite large portions of the project unless explicitly requested.

---

# Project Architecture

Frontend

- React
- TypeScript
- Vite
- TailwindCSS
- shadcn/ui
- TanStack Query

Backend

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic

AI

- OpenAI-compatible APIs
- Qwen
- DeepSeek
- GPT
- Vision models

Knowledge Base

- Chroma
- Local Embedding Models

Storage

- PostgreSQL
- Supabase Storage or Local Storage

---

# Architecture Responsibilities

Frontend is responsible for:

- UI
- Forms
- Uploads
- Progress
- Preview
- API calls

Backend is responsible for:

- AI
- OCR
- RAG
- Video analysis
- Image analysis
- Document generation
- Business logic
- Authentication
- Database

Never move AI logic into the frontend.

---

# Folder Responsibilities

Frontend

pages/

Page components.

components/

Reusable UI.

hooks/

Reusable React hooks.

services/

HTTP requests.

lib/

Utilities.

types/

Shared TypeScript types.

Backend

routers/

HTTP APIs.

services/

Business logic.

models/

Database models.

schemas/

Pydantic models.

core/

Configuration.

utils/

Utilities.

rag/

Knowledge base.

templates/

Word templates.

Never mix responsibilities.

---

# API Rules

Frontend never hardcodes API responses.

Always call backend APIs.

API Base URL must come from environment variables.

Never hardcode secrets.

Never hardcode tokens.

---

# AI Rules

Large Language Models generate text.

Vision Models understand images and videos.

OCR extracts text.

RAG retrieves knowledge.

Embedding models generate vectors.

Keep these responsibilities separate.

Never implement fake AI logic.

---

# RAG Rules

Knowledge retrieval should follow:

Documents

↓

Parsing

↓

Chunking

↓

Embedding

↓

Vector Store

↓

Retrieval

↓

Reranking

↓

LLM

Never skip retrieval.

Never let the LLM answer from imagination when RAG is enabled.

---

# Prompt Rules

Prompts should not be embedded inside UI components.

Store prompts separately.

Keep prompts reusable.

Avoid duplicate prompts.

---

# Document Generation

Word templates belong in

backend/data/templates/

Generated documents are produced by the backend.

Frontend only:

Upload

↓

Monitor progress

↓

Preview

↓

Download

Never generate Word documents in React.

---

# Video Processing

Video processing belongs to backend.

Frontend only uploads files.

Backend performs:

Frame extraction

Vision analysis

OCR

LLM reasoning

Document generation

---

# File Upload

Validate:

Extension

Size

Display upload progress.

Display readable errors.

Never silently ignore failures.

---

# TypeScript

Prefer strict typing.

Avoid any.

Remove unused imports.

Keep build clean.

---

# Python

Use type hints.

Use Pydantic.

Keep routers thin.

Business logic belongs inside services.

---

# Database

Never write raw SQL unless necessary.

Use SQLAlchemy.

Create migrations.

Never break existing schema.

---

# Environment Variables

Read configuration from:

.env

Never hardcode:

API Keys

Passwords

URLs

Secrets

---

# Logging

Log useful information.

Never log:

Passwords

Tokens

Sensitive documents

---

# UI

Use existing components.

Keep spacing consistent.

Use loading states.

Use empty states.

Use error states.

Keep the interface professional.

Avoid flashy animations.

---

# Performance

Avoid unnecessary rendering.

Lazy load large pages.

Avoid duplicate API requests.

Avoid unnecessary re-renders.

---

# Error Handling

Never swallow exceptions.

Return readable messages.

Display actionable errors.

---

# Security

Validate all uploaded files.

Escape untrusted content.

Never expose backend secrets.

Never trust client input.

---

# Testing

Before considering a task complete:

Build

Lint

Type Check

Fix errors.

Do not claim success if build fails.

---

# Git

Commit small logical changes.

Never rewrite published history.

Avoid force push.

Avoid rebasing pushed commits.

Keep the repository buildable.

---

<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to Lovable.
>
> Avoid rewriting published Git history.
>
> Do not force push.
>
> Do not amend pushed commits.
>
> Do not rebase pushed commits.
>
> Keep the branch in a working state.
<!-- LOVABLE:END -->

---

# Code Style

Prefer modifying existing code.

Avoid creating duplicate components.

Prefer composition over duplication.

Keep functions small.

Keep files focused.

---

# Decision Priority

When implementing features:

1. Reuse existing code.
2. Follow project architecture.
3. Keep code simple.
4. Keep types safe.
5. Keep modules independent.

---

# Execution

When given a development task:

1. Understand the existing implementation.
2. Create a plan.
3. Implement incrementally.
4. Keep the project buildable.
5. Verify the build.
6. Explain important changes.

Do not make unrelated refactors.

If uncertain, preserve the existing architecture.
