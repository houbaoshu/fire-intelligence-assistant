# API.md

# Fire Intelligence Platform API

This document defines the approved target backend API used by the frontend.

The API will be implemented by FastAPI. No application API is currently implemented in this repository.

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
    "refresh_token": ""
}
```

---

## Register

POST /api/auth/register

---

## Current User

GET /api/auth/me

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
    "task_id":"..."
}
```

---

## Detail

GET /api/inspection-record/{id}

---

## Update

PUT /api/inspection-record/{id}

---

## Download

GET /api/inspection-record/{id}/download

---

# Photo Report

## Generate

POST /api/photo-report/generate

FormData

video

Response

task_id

---

## Detail

GET /api/photo-report/{id}

---

## Update

PUT /api/photo-report/{id}

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

task_id

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

---

## Upload

POST /api/knowledge/documents

FormData

file

---

## Delete

DELETE /api/knowledge/documents/{id}

---

## Rebuild Index

POST /api/knowledge/rebuild

---

# Statistics

GET /api/statistics

---

# Task

## Query Task

GET /api/tasks/{task_id}

Response

```json
{
    "status":"processing",
    "progress":42,
    "message":"..."
}
```

Task Status

- pending
- queued
- processing
- completed
- failed
- cancelled

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

`GET /health`, `POST /api/auth/login`, and `POST /api/auth/register` are public unless a later approved contract states otherwise.

---

# Future APIs

Reserved

- Agent
- Workflow
- Prompt Management
- Model Management
- Audit Log
- Batch Tasks
- User Management
