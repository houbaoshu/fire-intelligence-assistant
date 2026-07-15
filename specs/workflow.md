# Intelligent Workflow and Task Management

## 1. Purpose

The Workflow feature coordinates long-running, multi-stage platform operations such as video analysis, transcription, knowledge indexing, and document generation. It provides consistent task state, retry behavior, cancellation, progress, and operational visibility without coupling business modules to one queue provider.

## 2. Status and Scope

**Status:** Implemented for Roadmap Milestone 5. Durable task state, startup recovery, bounded retries, cancellation, idempotency, progress, and the task center are verified.

Current target scope:

- shared asynchronous task model;
- backend task queue and workers;
- task progress and stage updates;
- idempotent submission where practical;
- safe retry and cancellation semantics;
- user-visible task center;
- internal workflow composition for supported business pipelines;
- bounded batch submission in a later increment of the milestone.

Out of scope for the first workflow increment:

- end-user visual workflow editor;
- arbitrary user-authored code;
- general-purpose automation platform;
- multi-agent collaboration;
- MCP orchestration;
- plugin marketplace;
- cross-tenant workflow sharing.

## 3. Users and Permissions

- **Inspector**: views and manages permitted tasks created for their work.
- **Supervisor**: views team tasks when authorized and may retry supported failures.
- **Administrator**: views operational task status and performs approved administrative recovery.
- **System worker**: claims and updates tasks using service credentials and least privilege.

Users must not view task inputs, results, or errors for records they cannot access.

## 4. Goals

The platform must be able to:

- move long-running work out of request/response handlers;
- represent task state consistently across modules;
- recover safely from worker or provider failures;
- prevent accidental duplicate final results;
- show users understandable progress and errors;
- evolve queue and worker providers without rewriting business workflows.

## 5. Workflow Model

```text
Business API Request
  ↓
Validate Authorization and Input
  ↓
Create Business Draft and ai_task
  ↓
Enqueue Workflow
  ↓
Worker Claims Task
  ↓
Execute Bounded Stages
  ↓
Persist Structured Result and Progress
  ↓
Completed / Failed / Cancelled
  ↓
Frontend Refreshes the Related Business Record
```

Example document workflow:

```text
Upload
  ↓
Media Extraction
  ↓
Vision / OCR / Speech
  ↓
Structured Generation
  ↓
Validation
  ↓
Persist Draft
  ↓
User Review
  ↓
Document Rendering
```

## 6. Functional Requirements

### Task Creation

- Long-running business APIs must create one durable task record before returning success.
- The response must include a `task_id`.
- Task creation and required business-draft creation must be transactionally consistent where practical.
- An idempotency key should prevent repeated client submissions from creating duplicate equivalent work.

### Task State

Approved states from `DATABASE.md`:

```text
pending
queued
processing
completed
failed
cancelled
```

Each task must expose safe values for:

- task type;
- status;
- progress from 0 to 100;
- current stage;
- safe result reference;
- safe error code and message;
- created, started, updated, and completion times when applicable.

### Progress

- Progress must be monotonic within one attempt unless the contract explicitly resets for retry.
- Stage names must be stable machine values with localized UI labels.
- `completed` tasks must have a result or an explicit no-result outcome.
- `failed` tasks must have a safe error code and message.

### Retry

- Retry eligibility depends on task type, state, and failure code.
- A retry must create an auditable new attempt or reset behavior defined by the backend.
- Retrying must not silently duplicate a finalized business record or generated document.
- Non-retryable validation and authorization failures must be clear.

### Cancellation

- Cancellation is best effort.
- The backend must verify that the current stage is cancellable.
- A cancel request must not mark a task cancelled before worker state is reconciled.
- Completed work already committed must not be deleted implicitly by cancellation.

### Task Center

- Users should be able to list their authorized recent tasks once a list API is approved.
- The UI should filter by status and task type when supported.
- Each task should link to its related business record rather than expose raw task result data.

## 7. Business Rules

- `ai_tasks` records operational execution; domain tables record business truth.
- A completed task must not be the only storage location for a final business record.
- Worker restarts must not cause silent duplicate finalization.
- Every stage must define whether it is retryable and idempotent.
- Partial outputs may be preserved for diagnostics or recovery but must not appear finalized.
- Provider-specific status values must be normalized into platform states.
- Users may cancel or retry only tasks they are authorized to manage.
- A task timeout must not be confused with confirmed provider failure when state is unknown.
- Batch work must have explicit size and concurrency limits.

## 8. UI Requirements

Shared task UI must provide:

- status label;
- progress percentage when meaningful;
- current localized stage;
- elapsed or updated time;
- safe error message;
- retry when allowed;
- cancel when allowed;
- link to related record when available;
- automatic stop of polling at terminal states.

A future task center should provide:

```text
Filters and Refresh
  ↓
Task List
  ↓
Task Detail / Related Record Link
```

Status must not rely on color alone. Screen readers must be informed of meaningful state changes without announcing every polling refresh.

## 9. API Requirements

Approved contract:

```text
GET /api/tasks/{task_id}
```

Current response example:

```json
{
  "status": "processing",
  "progress": 42,
  "message": "..."
}
```

Before implementing the full workflow milestone, update `API.md` with an explicit task schema and proposed contracts such as:

```text
GET  /api/tasks
POST /api/tasks/{task_id}/retry
POST /api/tasks/{task_id}/cancel
```

These proposed endpoints are not currently approved.

Every business generation API remains responsible for creating the appropriate business task. A generic task endpoint must not allow users to execute arbitrary internal workflows.

## 10. Data Impact

Primary target table:

- `ai_tasks`.

Related tables:

- business records referenced by task type;
- `generated_documents`;
- `knowledge_index_jobs`;
- `audit_logs`.

Before adding attempts, dependencies, schedules, notifications, or batch parents, define explicit tables in `DATABASE.md`. Do not encode a growing workflow engine entirely inside undocumented `input_data` or `result_data` JSON.

## 11. Backend Architecture Requirements

- Routers create or query tasks through application services.
- Business services define workflow semantics.
- Queue providers remain behind a task-service abstraction.
- Workers use the same validated configuration and storage/service interfaces as the API.
- Task state changes use guarded transitions.
- Long-running CPU or model work must not block normal API event loops.
- Provider callbacks, polling, and retries must normalize into the same platform task model.

Initial development may use a lightweight mechanism for short work, but production video and indexing tasks should use a durable queue and worker architecture.

## 12. Validation

- Task IDs must be valid and authorized.
- Progress must be between 0 and 100.
- Task type and status must use approved values.
- State transitions must follow a backend-defined transition map.
- Retry and cancellation must verify current state and task capability.
- Batch size and concurrency must be bounded.
- `input_data` must not contain raw sensitive files, tokens, or full document contents.

## 13. Error Handling

- Queue unavailable: do not report a queued task unless durable submission succeeded.
- Worker crash: return or recover the task to a defined retryable state.
- Provider timeout: record a safe code and preserve enough state for recovery.
- Duplicate delivery: guarded/idempotent stages must prevent duplicate final output.
- Progress update failure: task execution must not silently appear successful without final persistence.
- Cancellation race: reconcile completed work and return the true terminal state.
- Unknown state: surface an operational error instead of guessing completion.

## 14. Security and Privacy

- Task APIs require authentication and record-level authorization.
- Workers use least-privilege service credentials.
- Queue payloads must reference protected stored data instead of embedding large sensitive content.
- Secrets, prompts, tokens, recordings, full transcripts, and full documents must not appear in task logs.
- Administrative task access and retry/cancel actions must be audited.
- Error messages returned to users must omit stack traces and provider secrets.

## 15. Observability and Reliability

Useful safe signals include:

- queue wait time;
- stage duration;
- total task duration;
- retry count;
- failure code;
- worker identity;
- provider request status;
- task type and terminal state.

Requirements:

- use request and task correlation identifiers;
- define stuck-task detection and recovery;
- bound retries with backoff;
- use dead-letter or equivalent recovery for exhausted tasks;
- document cleanup of abandoned temporary files;
- keep operational logs free of sensitive business content.

## 16. Future Improvements

- server-sent events or WebSocket progress;
- notification preferences;
- batch parent/child tasks;
- scheduled workflows;
- visual workflow editor;
- model routing;
- agent and tool-calling workflows;
- distributed tracing and advanced operational dashboards.

## 17. Acceptance Criteria

- [x] Long-running business requests return a durable `task_id` without blocking until completion.
- [x] Task states and transitions use one documented platform model.
- [x] Frontend polling stops at completed, failed, or cancelled states.
- [x] Duplicate delivery or submission does not silently duplicate final business results.
- [x] Retry and cancellation are authorization-aware and state-aware.
- [x] Worker or provider failures produce safe actionable error codes and messages.
- [x] Business records remain the source of truth after task completion.
- [x] Queue payloads and logs contain no secrets or large sensitive content.
- [x] Stuck, exhausted, and abandoned tasks have documented recovery behavior.
- [x] Task UI is accessible and does not announce every polling refresh.
- [x] Available unit, integration, migration, load, and build checks pass.
