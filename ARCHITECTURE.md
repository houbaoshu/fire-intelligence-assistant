# ARCHITECTURE.md

# Fire Intelligence Platform Architecture

## 1. Purpose

This document describes the system architecture of the Fire Intelligence Platform.

It defines:

- system boundaries
- frontend and backend responsibilities
- module organization
- data flow
- AI orchestration
- asynchronous task processing
- storage responsibilities
- deployment structure
- security boundaries

This document describes the target architecture.

Before changing the architecture, inspect the existing implementation and preserve compatible project patterns whenever practical.

---

## 2. System Overview

Fire Intelligence Platform is an AI-assisted application for fire safety inspection work.

The platform supports:

- fire regulation question answering
- inspection record generation
- photo report generation
- interview record generation
- knowledge base management
- document generation
- file upload and storage
- task progress tracking
- user and permission management
- statistics and audit records

The system follows a separated frontend and backend architecture.

```text
User
  |
  v
Lovable React Frontend
  |
  | HTTPS / REST API
  v
FastAPI Backend
  |
  +-------------------+
  |                   |
  v                   v
Business Services    AI Orchestrator
  |                   |
  v                   +---------------------------+
PostgreSQL            |       |       |           |
                      v       v       v           v
                     LLM    Vision   OCR      Speech Recognition
                      |
                      v
                     RAG
                      |
                      v
                 Vector Database
```

---

## 3. Architecture Principles

The architecture should follow these principles:

1. The frontend handles presentation and user interaction.
2. The backend owns all business logic.
3. AI inference runs only in the backend.
4. PostgreSQL is the source of truth for business data.
5. Object storage stores uploaded and generated files.
6. The vector database stores retrieval data only.
7. Long-running AI operations use asynchronous tasks.
8. AI output should be converted into structured data before document generation.
9. Modules should remain loosely coupled.
10. External providers must be replaceable through configuration.

---

## 4. System Boundaries

### 4.1 Frontend Boundary

The frontend is responsible for:

- page rendering
- navigation
- forms
- file selection
- frontend validation
- API requests
- server-state display
- task progress display
- AI result preview
- user editing
- document download
- loading, empty, error, and success states

The frontend must not perform:

- OCR
- video frame extraction
- speech recognition
- RAG retrieval
- vector indexing
- LLM inference
- vision inference
- Word document generation
- authoritative permission checks
- direct database access

---

### 4.2 Backend Boundary

The backend is responsible for:

- authentication
- authorization
- business validation
- database access
- file storage
- AI orchestration
- OCR
- vision analysis
- speech recognition
- RAG
- document generation
- asynchronous task management
- audit logging
- backend error handling

The backend is the authoritative system boundary.

Frontend validation improves user experience but does not replace backend validation.

---

### 4.3 AI Boundary

AI components provide suggestions and structured extraction results.

AI-generated content must not automatically become a finalized inspection document.

Recommended flow:

```text
AI Generation
    |
    v
Structured Draft
    |
    v
User Review
    |
    v
User Modification
    |
    v
Final Document
```

---

## 5. Technology Architecture

### 5.1 Frontend

Default frontend stack:

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- React Router
- TanStack Query

Frontend code should remain independent from specific AI providers.

---

### 5.2 Backend

Default backend stack:

- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL

Optional asynchronous processing:

- FastAPI background tasks for lightweight development tasks
- Redis-based task queue for production workloads
- Celery, Dramatiq, RQ, or another configured task system

Long-running video and document tasks should not block normal HTTP requests.

---

### 5.3 AI Services

AI capabilities are accessed through backend service abstractions.

Supported capability categories:

- language model
- vision model
- OCR engine
- speech recognition
- embedding model
- reranker
- retrieval service

Specific model names and providers must come from configuration.

---

### 5.4 Storage

Storage is divided into three categories.

#### Relational Database

Stores:

- users
- permissions
- inspection records
- photo reports
- interview records
- AI task states
- file metadata
- knowledge document metadata
- generated document metadata
- audit logs

#### Object Storage

Stores:

- uploaded videos
- uploaded images
- uploaded audio
- source documents
- generated Word documents
- generated PDF documents
- extracted key frames
- temporary processing files

#### Vector Database

Stores:

- document chunk embeddings
- chunk metadata
- source references
- retrieval identifiers

The vector database must not be treated as the primary business database.

---

## 6. High-Level Modules

The platform is divided into the following modules:

```text
Authentication
User Management
Dashboard
Fire Regulation QA
Inspection Record
Photo Report
Interview Record
Knowledge Base
File Management
AI Task Management
Document Generation
Statistics
Audit Logging
System Settings
```

Each module should have a clear boundary.

---

## 7. Frontend Architecture

Recommended frontend layers:

```text
Pages
  |
  v
Feature Components
  |
  v
Query Hooks
  |
  v
API Services
  |
  v
Central API Client
```

### 7.1 Pages

Pages are responsible for:

- page layout
- feature composition
- route-level state
- displaying results

Pages should not contain large amounts of API or transformation logic.

---

### 7.2 Components

Components are responsible for reusable UI behavior.

Examples:

```text
FileUploader
TaskProgress
BackendStatus
ResultPreview
SourceCitation
DocumentDownloadButton
EditableField
EmptyState
ErrorState
```

Avoid creating multiple components with nearly identical responsibilities.

---

### 7.3 Hooks

Hooks encapsulate reusable UI and server-state behavior.

Examples:

```text
useHealth
useTaskStatus
useFileUpload
useRegulationQuery
useInspectionRecord
usePhotoReport
useKnowledgeDocuments
```

TanStack Query should manage backend server state.

Local React state should only manage temporary UI state.

---

### 7.4 API Services

API services define calls to the FastAPI backend.

Examples:

```text
authService
healthService
qaService
inspectionService
photoReportService
interviewService
knowledgeService
taskService
```

Do not call `fetch` directly throughout page components.

Use one centralized API client.

---

### 7.5 Suggested Frontend Structure

```text
frontend/
└── src/
    ├── app/
    │   ├── router.tsx
    │   └── providers.tsx
    ├── components/
    │   ├── layout/
    │   ├── shared/
    │   └── ui/
    ├── features/
    │   ├── auth/
    │   ├── dashboard/
    │   ├── regulation-qa/
    │   ├── inspection-record/
    │   ├── photo-report/
    │   ├── interview-record/
    │   └── knowledge-base/
    ├── hooks/
    ├── lib/
    │   ├── api-client.ts
    │   ├── env.ts
    │   └── utils.ts
    ├── pages/
    ├── services/
    ├── types/
    └── main.tsx
```

This is a target structure, not a requirement to reorganize working code unnecessarily.

Adapt to the repository that already exists.

---

## 8. Backend Architecture

The backend should use a layered architecture.

```text
Router
  |
  v
Application Service
  |
  +--------------------+
  |                    |
  v                    v
Repository          AI Service
  |                    |
  v                    v
Database           External Models
```

---

### 8.1 Routers

Routers are responsible for:

- receiving HTTP requests
- parsing request parameters
- applying dependencies
- calling application services
- returning API responses

Routers should remain thin.

Routers should not contain:

- large AI prompts
- direct model calls
- long document-generation logic
- complex database workflows

---

### 8.2 Application Services

Application services implement business workflows.

Examples:

```text
InspectionRecordService
PhotoReportService
InterviewRecordService
KnowledgeBaseService
DocumentGenerationService
TaskService
```

Application services coordinate:

- database operations
- AI services
- storage services
- task execution
- document rendering

---

### 8.3 Repositories

Repositories encapsulate database access.

They are responsible for:

- queries
- inserts
- updates
- transaction-aware persistence

Business rules should not be hidden inside repositories.

---

### 8.4 AI Services

AI services should be divided by capability.

```text
LLMService
VisionService
OCRService
SpeechService
EmbeddingService
RerankerService
RetrievalService
```

The application service orchestrates these capability services.

---

### 8.5 Storage Services

Storage access should use an abstraction.

```text
StorageService
  |
  +-- LocalStorageProvider
  +-- SupabaseStorageProvider
  +-- S3StorageProvider
```

Business modules should not depend directly on one storage provider.

---

### 8.6 Suggested Backend Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routers/
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── security.py
│   │   └── exceptions.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   │   ├── ai/
│   │   ├── storage/
│   │   ├── documents/
│   │   └── tasks/
│   ├── rag/
│   │   ├── parsers/
│   │   ├── chunking/
│   │   ├── embedding/
│   │   ├── retrieval/
│   │   └── reranking/
│   └── utils/
├── data/
│   ├── templates/
│   └── temporary/
├── alembic/
├── tests/
└── pyproject.toml
```

Preserve existing project conventions when they already provide equivalent responsibilities.

---

## 9. API Architecture

The frontend communicates with the backend through REST APIs.

Default API prefix:

```text
/api
```

Approved target modules from `API.md`:

```text
/api/auth
/api/qa
/api/inspection-record
/api/photo-report
/api/interview-record
/api/knowledge
/api/tasks
/api/statistics
```

API details belong in `API.md`.

---

### 9.1 Standard Request Flow

```text
Frontend Component
      |
      v
TanStack Query Hook
      |
      v
Frontend API Service
      |
      v
FastAPI Router
      |
      v
Application Service
      |
      v
Database / AI / Storage
```

---

### 9.2 Standard Error Flow

```text
Backend Error
     |
     v
Application Exception
     |
     v
Global Exception Handler
     |
     v
Standard API Error
     |
     v
Frontend API Client
     |
     v
Readable UI Error
```

Errors should use a consistent shape.

Example:

```json
{
  "success": false,
  "error": {
    "code": "TASK_FAILED",
    "message": "The video analysis task failed.",
    "details": null
  }
}
```

Do not expose backend stack traces to normal users.

---

## 10. Asynchronous Task Architecture

The following operations may require asynchronous execution:

- video frame extraction
- vision analysis
- OCR
- speech transcription
- knowledge base indexing
- large document parsing
- Word document generation
- PDF conversion
- batch report generation

Recommended task flow:

```text
Frontend Upload
      |
      v
POST Generation API
      |
      v
Create Business Draft
      |
      v
Create AI Task
      |
      v
Return task_id
      |
      v
Background Worker
      |
      v
Update Progress
      |
      v
Save Structured Result
      |
      v
Frontend Polling
      |
      v
Preview and Review
```

---

### 10.1 Task States

Supported task states:

```text
pending
queued
processing
completed
failed
cancelled
```

A task should include:

- task type
- current status
- progress
- current stage
- result reference
- error code
- error message
- created time
- start time
- completion time

---

### 10.2 Task Polling

The frontend may poll:

```text
GET /api/tasks/{task_id}
```

Polling should:

- use a reasonable interval
- stop after completion
- stop after failure
- stop after cancellation
- handle temporary network errors
- avoid duplicate polling requests

Future versions may use:

- Server-Sent Events
- WebSocket
- push notifications

Polling remains the default initial implementation.

---

## 11. RAG Architecture

The RAG subsystem has separate indexing and query pipelines.

### 11.1 Indexing Pipeline

```text
Source Document
      |
      v
File Parser
      |
      v
Document Normalization
      |
      v
Semantic Chunking
      |
      v
Metadata Enrichment
      |
      v
Embedding
      |
      v
Vector Database
```

Metadata should preserve information such as:

- document ID
- title
- document type
- page number
- article number
- section
- source path
- version
- effective date
- issuing authority

---

### 11.2 Query Pipeline

```text
User Question
      |
      v
Query Normalization
      |
      v
Retriever
      |
      v
Candidate Chunks
      |
      v
Reranker
      |
      v
Context Construction
      |
      v
LLM
      |
      v
Answer and Citations
```

Regulation answers should include traceable evidence whenever possible.

The system should distinguish between:

- retrieved facts
- model-generated interpretation
- unavailable evidence

---

## 12. Inspection Record Architecture

```text
Upload Video
      |
      v
Create AI Task
      |
      v
Extract Audio and Frames
      |
      +------------------+
      |                  |
      v                  v
Speech Recognition     Vision Analysis
      |                  |
      +--------+---------+
               |
               v
              OCR
               |
               v
      Structured Extraction
               |
               v
      Inspection Record Draft
               |
               v
          User Review
               |
               v
       Template Rendering
               |
               v
        DOCX / PDF Output
```

The structured inspection record should be stored before document rendering.

---

## 13. Photo Report Architecture

```text
Upload Video or Images
          |
          v
     Create AI Task
          |
          v
   Extract Candidate Frames
          |
          v
   Remove Duplicate Frames
          |
          v
      Vision Analysis
          |
          v
      Address and Violation Extraction
          |
          v
      Select Key Frames
          |
          v
       Editable Captions
          |
          v
       Template Rendering
          |
          v
         Photo Report
```

The user should be able to:

- remove an incorrect frame
- change frame order
- edit descriptions
- verify the recognized address
- verify violation information

---

## 14. Interview Record Architecture

```text
Upload Audio or Video
          |
          v
    Speech Recognition
          |
          v
    Transcript Cleaning
          |
          v
    Speaker Segmentation
          |
          v
    Structured Extraction
          |
          v
    Interview Record Draft
          |
          v
       User Review
          |
          v
    Template Rendering
```

The original transcript and the structured record should remain separate.

---

## 15. Document Generation Architecture

Documents should be generated from structured business data.

```text
Database Record
      |
      v
Template Data Mapper
      |
      v
Template Renderer
      |
      v
Generated DOCX
      |
      v
Optional PDF Conversion
      |
      v
Object Storage
      |
      v
Generated Document Metadata
```

Word templates are stored in:

```text
backend/data/templates/
```

Do not generate documents directly from uncontrolled free-form model output.

---

## 16. File Architecture

Uploaded files are handled as follows:

```text
Client File
    |
    v
Frontend Validation
    |
    v
Backend Validation
    |
    v
Object Storage
    |
    v
File Metadata Record
    |
    v
Processing Task
```

Temporary files should be stored separately from permanent files.

Recommended categories:

```text
uploads/
temporary/
key-frames/
knowledge/
templates/
generated/
```

Temporary processing files should be cleaned automatically.

---

## 17. Database Architecture

PostgreSQL stores structured business data.

The main database domains are:

```text
Identity
Inspection
Photo Report
Interview Record
File Metadata
Generated Documents
AI Tasks
Knowledge Base Metadata
Audit Logs
```

Detailed table definitions belong in `DATABASE.md`.

The database should not store large file binaries unless explicitly required.

---

## 18. Authentication and Authorization

Authentication identifies the current user.

Authorization determines whether the user may perform an action.

Recommended roles:

```text
admin
supervisor
inspector
viewer
```

Authorization must be enforced in the backend.

Frontend route protection is only a user-interface measure.

Example authorization flow:

```text
Request
  |
  v
Authentication Dependency
  |
  v
Current User
  |
  v
Permission Check
  |
  v
Application Service
```

---

## 19. Audit Architecture

Important actions should generate audit records.

Examples:

- user login
- file upload
- inspection record creation
- AI document generation
- user modification of AI results
- record finalization
- knowledge document deletion
- generated document download
- permission modification

Audit logs should be append-only wherever practical.

Do not store secrets or complete sensitive document content in audit logs.

---

## 20. Configuration Architecture

Configuration comes from environment variables or secure configuration providers.

Typical configuration groups:

```text
Application
Database
Storage
Authentication
LLM
Vision
OCR
Speech
Embedding
Reranker
Vector Database
Task Queue
Logging
```

Configuration should be loaded through one centralized backend settings module.

Never scatter environment-variable reads throughout business code.

---

## 21. External Service Abstraction

External providers should be accessed through internal interfaces.

Example:

```text
Application Service
       |
       v
Vision Interface
       |
       +-- Provider A
       +-- Provider B
       +-- Local Model
```

The same pattern applies to:

- LLM
- OCR
- speech recognition
- embeddings
- reranker
- object storage
- vector database

Changing providers should not require rewriting business workflows.

---

## 22. Security Architecture

Security controls should include:

- authenticated business APIs
- backend authorization checks
- file type validation
- file size validation
- MIME type validation
- safe storage filenames
- signed or protected download URLs
- restricted CORS configuration
- secret management
- request rate limits where required
- input validation
- output escaping
- audit logging
- least-privilege database access

Never trust:

- frontend validation
- uploaded filenames
- client-provided MIME types
- client-provided user IDs
- AI-generated legal conclusions

---

## 23. Observability

The backend should support structured logging.

Useful log fields include:

```text
timestamp
level
request_id
user_id
task_id
module
operation
duration
status
error_code
```

Do not log:

- passwords
- access tokens
- API keys
- complete sensitive documents
- unnecessary model inputs and outputs

Recommended operational signals:

- API response time
- task processing duration
- task failure rate
- model request failure rate
- knowledge indexing failure rate
- storage failure rate
- database connection failures

---

## 24. Deployment Architecture

### 24.1 Development

```text
Browser
  |
  v
Vite Development Server
  |
  v
Local FastAPI
  |
  +-- Local PostgreSQL or development database
  +-- Local object storage
  +-- Local or remote AI services
  +-- Local vector database
```

---

### 24.2 Production

```text
User Browser
      |
      v
Frontend Hosting / CDN
      |
      v
Reverse Proxy / API Gateway
      |
      v
FastAPI Application
      |
      +-- PostgreSQL
      +-- Object Storage
      +-- Vector Database
      +-- Redis / Task Queue
      +-- Background Workers
      +-- External AI Providers
```

Frontend and backend deployments should remain independent.

---

## 25. Scalability

Initial development may run as one FastAPI application.

As workload grows, the following may be separated:

```text
API Server
AI Worker
Video Worker
Document Worker
Knowledge Index Worker
Scheduler
```

Do not introduce distributed complexity before it is required.

Keep module boundaries clean so services can be separated later.

---

## 26. Reliability

The architecture should handle:

- network timeouts
- provider failures
- model rate limits
- invalid AI output
- interrupted uploads
- worker restarts
- duplicate task submission
- document-generation failures
- partial pipeline failures

Long-running tasks should be idempotent where practical.

Retrying a task should not silently create duplicate final records.

---

## 27. Testing Architecture

Recommended test levels:

### Unit Tests

Test:

- utility functions
- schema validation
- parsers
- data mapping
- document field formatting
- task state transitions

### Integration Tests

Test:

- API and database interaction
- storage integration
- task execution
- RAG retrieval
- document generation

### End-to-End Tests

Test:

- login
- upload
- AI task progress
- result review
- record update
- document download

External AI providers should be mockable during automated testing.

---

## 28. Architectural Constraints

The following constraints must be preserved:

- No AI inference in the frontend.
- No direct frontend database access for business data.
- No hardcoded model names in business logic.
- No hardcoded secrets.
- No large binary files stored in normal database fields.
- No business records stored only in generated Word files.
- No regulation QA without retrieval when RAG is enabled.
- No finalized AI document without user review.
- No schema change without migration.
- No rewriting published Lovable Git history.

---

## 29. Architecture Decision Rules

When making a design decision, prefer this order:

1. Preserve existing working architecture.
2. Reuse existing project abstractions.
3. Keep frontend and backend responsibilities separated.
4. Keep business logic independent from AI providers.
5. Store business results as structured data.
6. Prefer simple synchronous code for short operations.
7. Use asynchronous tasks for long-running operations.
8. Avoid premature microservices.
9. Avoid duplicate data and duplicate modules.
10. Document meaningful architectural changes.

---

## 30. Architecture Change Process

Before changing the architecture:

1. Inspect the current implementation.
2. Identify affected modules.
3. Explain why the change is necessary.
4. Check API and database compatibility.
5. Create migrations when required.
6. Update relevant documentation.
7. Run tests and build checks.
8. Preserve a working Git state.

Documents that may require updates:

```text
AGENTS.md
PROJECT.md
AI_CONTEXT.md
API.md
DATABASE.md
ARCHITECTURE.md
ROADMAP.md
CHANGELOG.md
```

---

## 31. Current Architecture Status

Update this section as implementation progresses.

### Frontend

```text
Status: Roadmap inspector-facing frontend implemented
Framework: React 19 with Vite and TanStack Start
Routing: TanStack file routing with protected business routes
Server-state library: TanStack Query
API client: Centralized environment-based client with bearer auth and standard errors
```

### Backend

```text
Status: Roadmap APIs, durable tasks, business services, RAG, and document generation implemented
Framework: FastAPI
ORM: SQLAlchemy 2
Migration system: Alembic with initial identity and audit migration
Task system: Durable database task state with bounded thread workers, retry, cancellation, and startup recovery
```

### AI

```text
LLM abstraction: OpenAI-compatible provider implemented
Vision abstraction: OpenAI-compatible provider plus FFmpeg frame pipeline implemented
OCR abstraction: Vision evidence extraction boundary implemented
Speech abstraction: OpenAI-compatible transcription implemented
Embedding abstraction: Optional OpenAI-compatible embeddings implemented
Reranker abstraction: Embedding and lexical evidence ranking implemented
```

### Storage

```text
Relational database: PostgreSQL configurable; SQLite development default
Object storage: Local provider implemented for development
Vector database: Relational knowledge-chunk store with optional provider vectors implemented
Temporary storage: Local storage category initialized
```

### Known Architectural Boundaries

- AI generation requires deployment-provided capability models and credentials.
- The included durable dispatcher supports one API replica; multiple replicas require queue leases.
- Local protected storage is the implemented provider; S3-compatible production storage remains a replaceable adapter.

---

## 32. Final Architecture Summary

```text
Frontend
  |
  | User Interface
  v
FastAPI Backend
  |
  | Business Orchestration
  +-----------------------+
  |           |           |
  v           v           v
Database    Storage     AI Services
                          |
                          v
                         RAG
                          |
                          v
                    Vector Database
```

The frontend displays and edits information.

The backend controls business workflows.

AI components extract and generate information.

PostgreSQL stores authoritative structured records.

Object storage stores files.

The vector database supports knowledge retrieval.

Users review AI-generated results before final document generation.
