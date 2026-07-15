# Inspection Record Generation

## 1. Purpose

The Inspection Record feature converts inspection video and optional inspector notes into a structured, reviewable fire-inspection record and a backend-generated document. It reduces transcription effort while keeping inspectors responsible for the final content.

## 2. Status and Scope

**Status:** Implemented. The authenticated upload, durable workflow, structured review, revision-safe save, and versioned backend DOCX flow are verified.

Current scope:

- upload one inspection video;
- provide optional supplementary notes;
- start and monitor an asynchronous AI task;
- retrieve the generated structured record;
- review and edit record fields and findings;
- save changes;
- generate and download the approved Word document.

Out of scope for the first version:

- multiple source videos;
- real-time field guidance;
- offline editing;
- electronic signatures;
- automatic submission to external government systems;
- autonomous finalization without user review.

## 3. Users and Permissions

- **Inspector**: creates and edits records permitted by the backend.
- **Supervisor**: reviews or finalizes records when authorized.
- **Administrator**: manages access and system configuration, not record content by default.
- **Viewer**: views finalized records only when authorized.

Only users with explicit permission may finalize, archive, or download a record.

## 4. Goals

Users must be able to:

- submit valid inspection evidence;
- understand each processing stage;
- review extracted basic information and findings;
- correct AI mistakes before finalization;
- preserve structured data independently from the generated file;
- download a document whose content matches the reviewed record.

## 5. User Workflow

```text
Open Inspection Record
  ↓
Upload Video + Optional Notes
  ↓
Submit Generation Request
  ↓
Receive task_id
  ↓
Monitor Video / Vision / OCR / Speech / LLM Stages
  ↓
Load Structured Draft
  ↓
Review and Edit
  ↓
Save
  ↓
Generate Document
  ↓
Download
```

## 6. Functional Requirements

### Upload and Submission

- The page must accept one video using the supported upload component.
- The selected filename and size must be displayed.
- Users must be able to replace or remove the file before submission.
- Supplementary notes must remain optional and visibly separate from extracted evidence.
- Upload and generation requests must not be submitted twice accidentally.

### Task Progress

- The backend must return a `task_id` for the long-running operation.
- The frontend must poll the documented task endpoint.
- Progress must show status, percentage when supplied, and current stage when supplied.
- Polling must stop for `completed`, `failed`, or `cancelled` states.
- A page refresh should recover an active task when a safe task identifier is retained.

### Structured Draft

The draft should support these fields when provided by the backend:

- record number;
- title;
- inspected organization;
- inspection address;
- inspection date;
- inspector names;
- contact person and phone;
- inspection findings;
- legal basis;
- correction requirements;
- summary;
- conclusion;
- status.

### Findings

- Users must be able to add, edit, reorder, and remove findings before finalization.
- Each finding should keep its type, location, description, legal basis, correction requirement, and severity distinct.
- Removing a finding must require confirmation when data would be lost.

### Save, Finalize, and Download

- Saving must persist the structured record through the backend.
- The UI must show whether local edits are saved.
- Document generation must use saved structured data.
- Download must use the backend-generated document.
- Regeneration of a finalized document must preserve prior versions as defined in `DATABASE.md`.

## 7. Business Rules

- AI-generated content is always a draft until reviewed by an authorized user.
- The system must not invent an organization, address, inspector, contact, inspection date, violation, legal basis, or corrective requirement.
- Legal references must be grounded in retrieved authoritative material when RAG is used.
- Visible evidence, OCR text, speech transcript, and supplementary notes must remain distinguishable during processing and audit.
- A finalized record must not be silently overwritten.
- Structured database data is the business source of truth; the Word file is an output.
- Missing fields must remain blank or require confirmation rather than receiving plausible-looking values.
- Any low-confidence conclusion must be marked for manual review.
- The content rendered into the document must match the saved reviewed version.

## 8. UI Requirements

Recommended layout:

```text
Upload and Notes
  ↓
Task Progress
  ↓
Record Header Fields
  ↓
Findings Editor
  ↓
Summary and Conclusion
  ↓
Save / Generate / Download Actions
```

The UI must provide:

- drag-and-drop and file-picker upload;
- upload and processing progress;
- stage-specific status text;
- editable structured fields with labels;
- repeatable finding rows or cards;
- unsaved-change warning;
- clear save success and failure feedback;
- confirmation before destructive actions;
- disabled final actions while required data is invalid or saving;
- accessible keyboard interaction and error summaries.

The UI must not imply AI content is verified merely because generation completed.

## 9. API Requirements

Approved contracts from `API.md`:

```text
POST /api/inspection-record/generate
GET  /api/tasks/{task_id}
GET  /api/inspection-record/{id}
PUT  /api/inspection-record/{id}
GET  /api/inspection-record/{id}/download
```

Generation request uses `FormData`:

```text
video
remarks
```

Generation response:

```json
{
  "task_id": "uuid"
}
```

Before implementation, `API.md` and backend schemas must define:

- how a completed task identifies the generated record;
- record detail and update payloads;
- document generation timing;
- download response headers;
- optimistic concurrency or version-conflict behavior.

Do not change the documented singular paths without an intentional API revision.

## 10. Data Impact

Relevant target tables:

- `inspection_records` for the structured record;
- `inspection_record_items` for findings;
- `uploaded_files` for video metadata;
- `ai_tasks` for generation state and structured result;
- `generated_documents` for versioned output metadata;
- `audit_logs` for significant create, edit, finalize, and download actions.

Required multi-record writes must use transactions. File binaries belong in object storage, not database fields.

## 11. AI Workflow and Rules

```text
Inspection Video
  ↓
Extract Frames and Audio
  ├─ Vision Analysis
  ├─ OCR
  └─ Speech Recognition when Audio Exists
          ↓
Normalize Evidence
          ↓
Retrieve Legal Context when Required
          ↓
LLM Structured Extraction
          ↓
Validate Structured JSON
          ↓
Inspection Record Draft
```

AI responsibilities:

- Vision describes visible objects, locations, and observable conditions.
- OCR extracts visible text without adding interpretation.
- Speech recognition produces a transcript separate from the final record.
- Retrieval provides evidence for legal references.
- The LLM combines supplied evidence into structured fields and identifies uncertainty.

AI constraints:

- Raw video processing remains in the backend.
- Provider and model names come from configuration.
- Intermediate evidence must not be replaced by unsupported model conclusions.
- Invalid structured output must be rejected or repaired safely before persistence.
- Prompts, provider credentials, and internal chain-of-thought must not be returned to the frontend.

## 12. Validation

- Current documented video types: `.mp4` and `.mov`.
- Maximum size must come from backend configuration and be communicated to the frontend.
- The backend must verify extension, MIME type, file signature where practical, and size.
- Supplementary notes must have a configured length limit.
- Record status, finding type, and severity must use approved values from `DATABASE.md`.
- Required fields for finalization must be defined by backend business rules.
- Phone numbers and dates must be validated without destroying valid regional formats.

## 13. Error Handling

- Upload failure: retain selection when safe and allow retry.
- Unsupported or oversized file: show the exact allowed rule.
- Processing timeout: keep the draft/task reference and offer retry or status refresh.
- Vision, OCR, speech, or LLM partial failure: identify the failed stage and preserve usable evidence.
- Task failure: stop polling and show the safe backend error.
- Save conflict: preserve user edits and offer reload/compare behavior.
- Template failure: keep the structured record and allow document regeneration.
- Download failure: keep document metadata and allow retry.

## 14. Security and Privacy

- All operations require backend authentication and authorization.
- Uploaded videos and generated documents may contain sensitive inspection data and must use protected storage.
- Do not expose storage paths or public permanent URLs.
- Use safe filenames and protected or signed downloads.
- Logs must not contain full videos, transcripts, documents, tokens, or prompts.
- Temporary frames and audio must follow cleanup and retention rules.
- User-provided IDs and status transitions must never be trusted without backend verification.

## 15. Non-Functional Requirements

- Long-running processing must not block normal HTTP request workers.
- Task execution should be retryable and idempotent where practical.
- Duplicate submission must not create duplicate finalized records silently.
- Structured edits should remain responsive for large finding sets.
- The page must recover gracefully from temporary network loss.
- Audit records should identify significant user changes without storing complete sensitive content.

## 16. Future Improvements

- multiple videos and images;
- in-browser evidence timeline;
- offline draft mode;
- electronic signatures;
- comparison between generated versions;
- external case-system integration;
- real-time inspection guidance;
- confidence display backed by calibrated evidence.

## 17. Acceptance Criteria

- [x] A valid video and optional notes create one generation task.
- [x] Task status uses `GET /api/tasks/{task_id}` and polling stops at terminal states.
- [x] Completion resolves to a structured inspection record.
- [x] Users can edit and save record fields and findings.
- [x] Unsupported, oversized, and failed uploads show actionable errors.
- [x] Missing or uncertain evidence is not replaced with fabricated facts.
- [x] Final document content matches the saved reviewed record.
- [x] Finalized documents are versioned rather than silently overwritten.
- [x] Files are generated and downloaded by the backend.
- [x] Authorization protects view, update, finalize, and download operations.
- [x] Available lint, type, test, migration, and build checks pass.
