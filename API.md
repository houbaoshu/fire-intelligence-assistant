# API.md

# Fire Intelligence Platform API

This document defines the approved backend API used by the frontend.

The documented health, authentication, business, knowledge, task, statistics, enterprise, and
AI-platform contracts are implemented. All IDs are UUID strings and timestamps are UTC ISO 8601.

Unless otherwise noted:

- Request Body: JSON
- Response: JSON
- Authentication: Bearer Token for business APIs
- Long-running tasks return task_id

---

# Response Convention

Successful responses use the endpoint-specific JSON shapes documented below. They are not wrapped in a generic success envelope.

Errors use one consistent envelope:

```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "...",
        "details": null
    }
}
```

---

# Authentication

## Public Configuration

GET /api/auth/config

Response

```json
{
    "registration_enabled": true
}
```

---

## Login

POST /api/auth/login

Request

```json
{
    "email": "",
    "password": ""
}
```

Response

```json
{
    "access_token": "",
    "refresh_token": "",
    "token_type": "bearer",
    "expires_in": 1800
}
```

---

## Register

POST /api/auth/register

Request

```json
{
    "email": "inspector@example.com",
    "password": "user-provided-password",
    "username": "Inspector Name"
}
```

Registration passwords contain 12 to 128 characters. `username` is optional. Ordinary registration always creates the backend-controlled `inspector` role.

Response: `201 Created`

```json
{
    "id": "uuid",
    "email": "inspector@example.com",
    "username": "Inspector Name",
    "role": "inspector",
    "is_active": true,
    "created_at": "2026-07-14T00:00:00Z"
}
```

---

## Current User

GET /api/auth/me

Requires `Authorization: Bearer <access_token>` and returns the same user shape as registration.

---

# Health

## Backend Status

GET /health

Response

```json
{
    "status":"ok"
}
```

---

# Fire Regulation QA

## Ask Question

POST /api/qa/query

Request

```json
{
    "question":"..."
}
```

Response

```json
{
    "answer":"...",
    "sources":[]
}
```

---

# Inspection Record

## Generate

POST /api/inspection-record/generate

Request

FormData

video

remarks

Response

```json
{
    "task_id":"...",
    "entity_id":"..."
}
```

---

## Detail

GET /api/inspection-record/{id}

Returns the record header, `revision`, `status`, separately preserved `source_notes`, and ordered
`findings`. A completed task also exposes the record ID in `result.entity_id`.

---

## Update

PUT /api/inspection-record/{id}

The complete editable record is submitted with its current `revision`. Stale revisions return
`409 REVISION_CONFLICT`. Finalized records are immutable.

---

## Download

GET /api/inspection-record/{id}/download

Returns an authenticated DOCX generated from the saved revision. The backend preserves prior
generated versions.

---

# Photo Report

## Generate

POST /api/photo-report/generate

FormData

video

Response

```json
{"task_id":"...","entity_id":"..."}
```

---

## Detail

GET /api/photo-report/{id}

---

## Update

PUT /api/photo-report/{id}

Updates report fields and the complete ordered image list. Image IDs must belong to the report.

## Protected Image Preview

GET /api/photo-report/{id}/images/{image_id}

---

## Download

GET /api/photo-report/{id}/download

---

# Interview Record

## Generate

POST /api/interview-record/generate

FormData

audio

video

Response

```json
{"task_id":"...","entity_id":"..."}
```

Exactly one of `audio` or `video` is required.

---

## Detail

GET /api/interview-record/{id}

---

## Update

PUT /api/interview-record/{id}

---

## Download

GET /api/interview-record/{id}/download

---

# Knowledge Base

## List Documents

GET /api/knowledge/documents

Returns authorized source metadata, indexing status, chunk count, and safe failure details.

---

## Upload

POST /api/knowledge/documents

FormData

file

Response: `202 Accepted`

```json
{
  "document": {"id":"...","title":"...","status":"uploaded","task_id":"..."},
  "task_id":"..."
}
```

---

## Delete

DELETE /api/knowledge/documents/{id}

---

## Rebuild Index

POST /api/knowledge/rebuild

Returns `{"task_id":"..."}`. Equivalent active rebuilds reuse the existing task.

---

# Statistics

GET /api/statistics

```json
{
  "scope":"personal",
  "period_start":null,
  "period_end":"2026-07-14T00:00:00Z",
  "timezone":"UTC",
  "last_updated_at":"2026-07-14T00:00:00Z",
  "metrics":[{"id":"inspection_records","label":"检查记录","value":0,"unit":"条","available":true}],
  "task_statuses":{},
  "knowledge_statuses":{}
}
```

---

# Task

## Query Task

GET /api/tasks/{task_id}

Response

```json
{
    "id":"...",
    "task_type":"inspection_record_generation",
    "status":"processing",
    "progress":42,
    "current_stage":"analyzing_evidence",
    "message":"analyzing_evidence",
    "result":{"entity_type":"inspection_record","entity_id":"..."},
    "error_code":null,
    "error_message":null,
    "attempt":1,
    "cancel_requested":false,
    "created_at":"...",
    "updated_at":"...",
    "started_at":"...",
    "completed_at":null
}
```

Task Status

- pending
- queued
- processing
- completed
- failed
- cancelled

## List Tasks

GET /api/tasks?status={status}&task_type={type}&limit=20&offset=0

## Retry Task

POST /api/tasks/{task_id}/retry

Retry is limited by state, authorization, and `APP_TASK_MAX_ATTEMPTS`.

## Cancel Task

POST /api/tasks/{task_id}/cancel

Cancellation is best effort and reconciled by the worker.

---

# Enterprise Management

Administrator contracts:

```text
GET  /api/organizations
POST /api/organizations
GET  /api/departments?organization_id={id}
POST /api/departments
GET  /api/memberships?organization_id={id}
POST /api/memberships
GET  /api/role-permissions
PUT  /api/role-permissions/{role}
GET  /api/audit-logs
```

Supervisor visibility is limited to users sharing an organization membership. Administrators have
system scope; inspectors and viewers have personal scope unless a later contract grants assignment.

---

# AI Platform Administration

Administrator-only registries:

```text
GET|POST /api/platform/models
GET|POST /api/platform/prompts
GET|POST /api/platform/workflows
GET|POST /api/platform/plugins
GET|POST /api/platform/evaluations
DELETE   /api/platform/{resource}/{id}
```

Registry payloads use `{"data": {...}}`. Secret-like configuration keys are rejected; credentials
remain deployment configuration.

Authenticated safe capability metadata:

```text
GET /api/system/capabilities
```

Administrator operational counters:

```text
GET /api/system/metrics
```

---

# File Upload Rules

Supported

Video

- mp4
- mov

Images

- jpg
- jpeg
- png

Documents

- pdf
- doc
- docx
- ppt
- pptx

Audio

- wav
- mp3
- m4a

---

# Authentication

All business APIs require:

Authorization

Bearer Token

`GET /health`, `GET /api/auth/config`, `POST /api/auth/login`, and `POST /api/auth/register` are public unless a later approved contract states otherwise.

---

# Extension Boundary

Agent, multi-agent, MCP, and tool providers use backend platform contracts and registered workflows.
No generic HTTP endpoint executes arbitrary user-supplied tools or code.
