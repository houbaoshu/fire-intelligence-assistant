# Photo Report Generation

## 1. Purpose

The Photo Report feature converts an inspection video into a structured, reviewable set of evidence images with concise captions, then produces a backend-generated Word document. It reduces manual frame selection while preserving human review of every included image and statement.

## 2. Status and Scope

**Status:** Implemented. FFmpeg extraction, quality and duplicate filtering, vision drafts, protected review, ordering, persistence, and DOCX output are implemented.

Current scope:

- upload one inspection video;
- submit an asynchronous generation task;
- extract and analyze candidate key frames in the backend;
- display selected images, timestamps, addresses, and violation drafts;
- edit captions and recognized report information;
- select, remove, and reorder report images;
- save the structured report;
- generate and download a Word document.

Out of scope for the first version:

- multiple source videos;
- direct image uploads;
- manual frame extraction in the browser;
- PDF export;
- automatic legal finalization;
- public sharing links.

## 3. Users and Permissions

- **Inspector**: creates, reviews, edits, and downloads permitted photo reports.
- **Supervisor**: reviews or finalizes reports when authorized.
- **Administrator**: manages system access and templates, not report content by default.
- **Viewer**: views finalized reports only when authorized.

The backend must enforce permissions for report, image, source video, and generated-document access.

## 4. Goals

Users must be able to:

- submit inspection video without manually capturing every frame;
- see representative, clear evidence images;
- verify the recognized inspection address and violation descriptions;
- exclude redundant or incorrect images;
- control image order and captions;
- download a document that matches the reviewed selection.

## 5. User Workflow

```text
Open Photo Report
  ↓
Upload Inspection Video
  ↓
Submit Generation Request
  ↓
Receive task_id
  ↓
Extract and Score Candidate Frames
  ↓
Vision + OCR + LLM Analysis
  ↓
Load Structured Draft and Image Gallery
  ↓
Review Address, Images, Violations, and Captions
  ↓
Select / Remove / Reorder / Edit
  ↓
Save
  ↓
Generate Word Document
  ↓
Download
```

## 6. Functional Requirements

### Upload and Submission

- The page must accept one supported inspection video.
- Filename, size, and validation result must be visible before submission.
- Users must be able to replace or remove the video before submitting.
- Upload progress and processing progress must be separate states.
- Duplicate concurrent generation requests must be prevented.

### Task Progress

- Generation must return a `task_id`.
- The UI must show backend-provided status, progress, and current stage.
- Polling must stop after completion, failure, or cancellation.
- A recoverable page refresh should resume the known active task.

### Photo Gallery

Each candidate or selected image should display available information:

- image preview;
- source-video timestamp;
- selected state;
- caption draft;
- detected address;
- detected violation;
- manual-review indicator.

Users must be able to:

- open a larger preview;
- include or exclude an image;
- change the order of selected images;
- edit captions;
- correct address and violation text;
- save changes.

### Document Generation

- Only selected images may be rendered into the final document.
- Document image order must match the saved user order.
- Captions must match the saved reviewed text.
- Download must use the backend-generated file.
- Regeneration must preserve prior finalized versions as required by `DATABASE.md`.

## 7. Business Rules

### Photo Selection

- Selected frames must clearly show relevant inspection evidence.
- Blurred, dark, transitional, obstructed, duplicate, or highly similar frames should be excluded.
- The report must contain enough evidence to support its content without unnecessary repetition.
- Removing a frame from the report must not automatically delete the source file if another record references it.

### Violation Description

- Each photo should describe at most one primary violation.
- If one frame shows several unrelated issues, select the most relevant issue or use separate frames when evidence permits.
- Captions must not combine unsupported or unrelated violations.
- Captions must be concise, objective, and factual.

### Address Consistency

- The inspection address should remain consistent across the report unless multiple locations are explicitly confirmed.
- Prefer user-confirmed data over OCR inference.
- When user-confirmed data is absent, use reliable OCR and corroborating evidence.
- Conflicting or incomplete address evidence must require manual review.
- The system must never invent an address.

### Human Review

- Every AI-generated caption, violation, and address is a draft.
- Users must be able to edit, replace, exclude, or regenerate drafts before finalization.
- No AI-generated report may become final without an explicit authorized review action.
- The generated document must reflect the saved reviewed state, not an earlier AI response.

## 8. UI Requirements

Recommended layout:

```text
Upload Area
  ↓
Task Progress
  ↓
Report Information
  ↓
Selectable Photo Gallery
  ↓
Caption and Violation Editor
  ↓
Save / Generate / Download Actions
```

The UI must provide:

- drag-and-drop and file-picker upload;
- separate upload and AI-processing indicators;
- responsive image cards;
- large preview dialog;
- accessible selected/unselected controls;
- keyboard-operable reordering or an equivalent accessible alternative;
- visible unsaved-change state;
- confirmation before discarding edits;
- manual-review indicators for uncertain or conflicting results;
- empty and failure states that explain the next action.

Selection must not rely on color alone. Image previews must include meaningful accessible labels derived from reviewed content, not raw filenames alone.

## 9. API Requirements

Approved contracts from `API.md`:

```text
POST /api/photo-report/generate
GET  /api/tasks/{task_id}
GET  /api/photo-report/{id}
PUT  /api/photo-report/{id}
GET  /api/photo-report/{id}/download
```

Generation uses `FormData` with:

```text
video
```

The generation response must contain:

```json
{
  "task_id": "uuid"
}
```

Before implementation, `API.md` and backend schemas must define:

- how task completion identifies the report;
- the report and image response models;
- update semantics for selection and ordering;
- optimistic concurrency or conflict handling;
- document generation timing and download headers;
- protected image-preview delivery.

Do not switch to plural paths without an intentional API revision.

## 10. Data Impact

Relevant target tables:

- `photo_reports` for report-level structured data;
- `photo_report_images` for image selection, order, captions, and detections;
- `uploaded_files` for source video, key frames, and generated file metadata;
- `ai_tasks` for asynchronous processing;
- `generated_documents` for versioned output documents;
- `audit_logs` for significant actions.

Object storage holds binaries. Database rows hold metadata and structured report state.

## 11. AI Workflow and Rules

```text
Inspection Video
  ↓
Extract Candidate Frames
  ↓
Quality and Similarity Filtering
  ↓
Vision Analysis + OCR
  ↓
Normalize Observable Evidence
  ↓
LLM Creates Structured Drafts
  ↓
Validate JSON and Source References
  ↓
Photo Report Draft
```

Component responsibilities:

- Frame extraction selects candidates in the backend.
- Quality filtering rejects unusable frames.
- Vision identifies visible objects, conditions, and scenes.
- OCR extracts signs, addresses, labels, building names, and equipment identifiers.
- The LLM combines supplied evidence into concise structured captions and flags uncertainty.

AI constraints:

- The model must not invent equipment, addresses, violations, legal references, or unseen conditions.
- A caption must be traceable to its source frame and supporting evidence.
- Low-confidence or conflicting results must require manual confirmation.
- Structured JSON must be validated before persistence and document rendering.
- Provider names and thresholds must come from backend configuration.
- Prompts and internal model diagnostics must not be exposed to the frontend.

## 12. Caption Rules

Captions must:

- describe the visible primary issue;
- identify location only when supported;
- use neutral, professional language;
- avoid speculation and unnecessary narrative;
- remain short enough for the document template;
- avoid claiming legal conclusions that are not grounded.

Acceptable style:

> Emergency exit is blocked by stored materials.

> Fire extinguisher access is obstructed.

Unacceptable style:

> The site has many serious problems and clearly violates numerous rules.

User-facing examples should be localized to Chinese in the implemented interface.

## 13. Validation

- Current documented video types: `.mp4` and `.mov`.
- File-size limits must come from backend configuration.
- The backend must validate extension, MIME type, file signature where practical, and size.
- A report must contain at least one selected valid image before document generation.
- Image order values must be unique and normalized.
- Caption and address length limits must be defined by backend schemas.
- IDs in update requests must belong to the same authorized report.

## 14. Error Handling

- Upload failure: show a retryable error and preserve safe local selection.
- Frame extraction failure: stop the task and identify the failed stage.
- No usable frames: show a specific empty result and request another video or manual follow-up.
- Vision, OCR, or LLM partial failure: preserve usable frames and clearly flag missing analysis.
- Task timeout: allow status refresh or safe retry without duplicating finalized reports.
- Save conflict: preserve edits and offer reload/compare behavior.
- Image preview failure: show a placeholder and keep text editing available.
- Template or download failure: preserve the reviewed report and allow retry.

## 15. Security and Privacy

- Source videos, extracted frames, and documents require backend authorization.
- Do not expose permanent public object URLs or storage paths.
- Use safe filenames and protected or signed delivery.
- Do not log image content, full captions, prompts, tokens, or sensitive addresses unnecessarily.
- Temporary frames must follow configured cleanup and retention rules.
- AI providers must receive only the minimum evidence required for the task.
- Client-provided image IDs, order, report ID, and selected state must be verified by the backend.

## 16. Non-Functional Requirements

- Video processing must run asynchronously.
- Frame processing should be bounded to prevent unplanned provider cost and latency.
- The gallery must remain responsive with the configured maximum image count.
- Duplicate task retries should be idempotent where practical.
- The user must be able to recover from temporary network loss without losing saved work.
- The interface must work on desktop and tablet.

## 17. Future Improvements

- multiple videos;
- direct image upload;
- manual timeline frame selection;
- evidence-confidence display backed by calibrated scores;
- automatic before/after grouping;
- PDF export;
- version comparison;
- batch photo-report generation.

## 18. Acceptance Criteria

- [x] A valid video creates one photo-report generation task.
- [x] Task polling stops on completed, failed, or cancelled status.
- [x] The backend extracts multiple representative frames and excludes unusable duplicates.
- [x] Each displayed image remains linked to its source timestamp.
- [x] Users can edit captions, address, and violation text.
- [x] Users can select, exclude, preview, and reorder images accessibly.
- [x] Conflicting or uncertain address and violation results require manual review.
- [x] The system does not fabricate unseen violations, equipment, or locations.
- [x] The generated document includes only selected images in saved order with saved captions.
- [x] Reviewed structured data persists independently from the generated file.
- [x] Protected files cannot be accessed without backend authorization.
- [x] Available lint, type, test, migration, and build checks pass.
