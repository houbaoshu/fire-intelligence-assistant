# ROADMAP.md

# Fire Intelligence Platform Roadmap

This document defines the long-term development roadmap of the Fire Intelligence Platform.

It describes the evolution of the product rather than individual coding tasks.

Detailed implementation requirements belong in the dedicated documents under `specs/`. The current directory structure is recorded in the **Specification Documents** section below and in `specs/README.md`.

The roadmap should remain stable.

Individual specifications may evolve independently.

---

# Vision

Build a complete AI-powered platform for fire safety inspection.

The platform should assist inspectors throughout the entire workflow:

Preparation

↓

Inspection

↓

Evidence Collection

↓

Document Generation

↓

Knowledge Retrieval

↓

Review

↓

Statistics

↓

Management

↓

Continuous AI Assistance

---

# Development Principles

Development proceeds milestone by milestone.

Each milestone should:

- preserve existing functionality
- keep the project buildable
- follow AGENTS.md
- follow ARCHITECTURE.md
- follow AI_CONTEXT.md
- follow API.md
- follow DATABASE.md

Do not begin a later milestone before the current milestone reaches a usable state.

---

# Milestone 1

## Foundation Platform

### Goal

Build a stable technical foundation.

### Scope

Frontend

- Project initialization
- Routing
- Layout
- Navigation
- Theme
- Shared components

Backend

- FastAPI initialization
- Configuration
- Logging
- API conventions
- Error handling

Infrastructure

- Database
- Object storage
- Authentication
- Environment configuration

### Deliverables

- Stable frontend
- Stable backend
- Authentication
- Health endpoint
- API client
- Shared layouts

### Status

- [ ]

---

# Milestone 2

## Fire Inspection Workflow

### Goal

Support daily inspection work.

### Modules

Inspection Record

Photo Report

Interview Record

Statistics

Settings

### Deliverables

Users can:

- upload inspection materials
- manage inspection records
- edit generated content
- download documents

### Status

- [ ]

---

# Milestone 3

## Fire Regulation Knowledge Base

### Goal

Provide regulation retrieval and intelligent QA.

### Modules

Document Parsing

Semantic Chunking

Embedding

Retriever

Reranker

Fire Regulation QA

Knowledge Management

### Deliverables

Users can:

- upload regulations
- rebuild indexes
- search regulations
- ask legal questions
- receive cited answers

### Status

- [ ]

---

# Milestone 4

## AI Document Generation

### Goal

Generate official inspection documents automatically.

### Modules

Inspection Record Generation

Photo Report Generation

Interview Record Generation

Template Rendering

Document Download

### AI Pipeline

Video

↓

Vision

↓

OCR

↓

LLM

↓

Structured Data

↓

Word Template

↓

Download

### Deliverables

Support automatic generation of:

- inspection records
- photo reports
- interview records

### Status

- [ ]

---

# Milestone 5

## Intelligent Workflow

### Goal

Automate inspection workflows.

### Modules

Task Queue

Workflow Engine

Background Processing

AI Task Management

Notification

Batch Processing

### Deliverables

Support:

- asynchronous AI tasks
- long-running jobs
- workflow orchestration

### Status

- [ ]

---

# Milestone 6

## Enterprise Management

### Goal

Support enterprise deployment.

### Modules

Organizations

Departments

Role Management

Permission Management

Audit Logs

Operation Logs

Statistics

### Deliverables

Support multiple organizations.

Support fine-grained permissions.

### Status

- [ ]

---

# Milestone 7

## Platform Engineering

### Goal

Improve reliability and deployment.

### Modules

Docker

CI/CD

Monitoring

Backup

Performance Optimization

Caching

Task Queue

Deployment

### Deliverables

Support production deployment.

### Status

- [ ]

---

# Milestone 8

## AI Platform

### Goal

Build a reusable AI platform.

### Modules

Prompt Management

Model Management

Agent

Multi-Agent

MCP

Evaluation

Model Routing

Plugin System

Workflow Editor

### Deliverables

The platform supports future AI capabilities without major architectural changes.

### Status

- [ ]

---

# Future Extensions

Potential future capabilities:

- Mobile application
- Voice assistant
- Real-time inspection guidance
- GIS integration
- IoT device integration
- Fire equipment recognition
- Digital twin support
- Large-scale document processing

These features are not required for the current roadmap.

---

# Specification Documents

Detailed requirements should be maintained separately.

Current structure:

```text
specs/
├── README.md
├── authentication.md
├── dashboard.md
├── regulation-qa.md
├── inspection-record.md
├── photo-report.md
├── interview-record.md
├── knowledge-base.md
├── settings.md
├── statistics.md
└── workflow.md
```

Each specification should include:

- Purpose
- User workflow
- UI requirements
- API requirements
- Database impact
- AI workflow
- Acceptance criteria

---

# AI Execution

When an AI coding assistant is asked to implement a feature:

1. Read AGENTS.md
2. Read PROJECT.md
3. Read ARCHITECTURE.md
4. Read AI_CONTEXT.md
5. Read API.md
6. Read DATABASE.md
7. Read the relevant specification
8. Implement only the requested milestone or specification
9. Preserve existing architecture
10. Verify the project builds successfully

Do not implement unrelated milestones.

---

# Current Progress

| Milestone | Name | Status |
|-----------|------|--------|
| 1 | Foundation Platform | ⬜ Not Started |
| 2 | Fire Inspection Workflow | ⬜ Not Started |
| 3 | Fire Regulation Knowledge Base | ⬜ Not Started |
| 4 | AI Document Generation | ⬜ Not Started |
| 5 | Intelligent Workflow | ⬜ Not Started |
| 6 | Enterprise Management | ⬜ Not Started |
| 7 | Platform Engineering | ⬜ Not Started |
| 8 | AI Platform | ⬜ Not Started |

Update this table as the project evolves.
