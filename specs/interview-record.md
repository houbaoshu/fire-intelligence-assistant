# Interview Record Generation

## 1. Purpose

The Interview Record feature transforms an authorized audio or video recording into a preserved transcript, a structured interview draft, and a backend-generated document. It reduces transcription effort while requiring users to verify speakers, wording, and structured content.

## 2. Status and Scope

**Status:** Implemented. Exactly-one-media validation, transcription, separate evidence and structured review, persistence, and versioned DOCX output are implemented.

Current scope:

- upload one audio or video recording;
- start and monitor asynchronous transcription and structuring;
- display the original transcript separately from the structured record;
- edit interview metadata and structured content;
- save reviewed changes;
- generate and download a Word document.

Out of scope for the first version:

- live recording in the browser;
- real-time transcription;
- automatic identity verification;
- voiceprint recognition;
- electronic signatures;
- translation;
- automatic submission to external case systems.

## 3. Users and Permissions

- **Inspector**: creates and edits interview records permitted by the backend.
- **Supervisor**: reviews or finalizes records when authorized.
- **Administrator**: manages access and templates, not interview content by default.
- **Viewer**: views finalized records only when authorized.

Recordings, transcripts, structured records, and generated documents must share consistent backend authorization.

## 4. Goals

Users must be able to:

- submit a supported recording;
- understand transcription and generation progress;
- compare transcript evidence with structured content;
- correct speaker, wording, time, and metadata errors;
- preserve reviewed structured data;
- download a document that matches the reviewed content.

## 5. User Workflow

```text
Open Interview Record
  ↓
Upload Audio or Video
  ↓
Submit
  ↓
Receive task_id
  ↓
Extract Audio if Required
  ↓
Speech Recognition
  ↓
Transcript Normalization and Speaker Segmentation
  ↓
LLM Structured Extraction
  ↓
Load Transcript and Record Draft
  ↓
Review and Edit
  ↓
Save
  ↓
Generate Word Document
  ↓
Download
```

## 6. Functional Requirements

### Upload

- The page must accept exactly one source recording in the initial version.
- A user may select an audio file or a video file, not both for one request unless the backend contract explicitly supports it.
- The selected filename, size, and media type must be displayed.
- Users must be able to replace or remove the recording before submission.
- Upload and processing progress must be shown separately.

### Task Progress

- The generation request must return a `task_id`.
- The frontend must poll the shared task endpoint.
- Status, stage, and progress must be displayed when returned.
- Polling must stop after completion, failure, or cancellation.
- A known active task should be recoverable after a page refresh.

### Transcript

- The transcript must be displayed separately from the structured record.
- Speaker labels and timestamps should be shown when returned by the backend.
- Uncertain words or segments must be marked rather than silently guessed.
- The initial transcript should remain available even after structured content is edited.
- If transcript editing is allowed, the UI must distinguish original machine output from the reviewed version.

### Structured Record

The record should support these fields when provided:

- title;
- interviewee name;
- interviewer names;
- location;
- start and end time;
- question-and-answer content or equivalent structured sections;
- status.

Users must be able to review, edit, and save all generated fields before finalization.

### Document Generation

- The document must be rendered from saved structured data.
- The original or reviewed transcript must not be silently substituted for the structured record.
- The document must use the backend template.
- Regeneration of finalized records must preserve prior versions as defined in `DATABASE.md`.

## 7. Business Rules

- The system must never invent a speaker, statement, time, location, identity, or admission.
- Unintelligible speech must be marked as uncertain or inaudible.
- Speaker attribution is a draft unless confirmed by a user.
- The source recording, transcript, and structured interview record are distinct artifacts.
- Cleaning punctuation or filler words must not change substantive meaning.
- AI must not convert an ambiguous statement into a more certain statement.
- Structured question-and-answer content must remain traceable to transcript evidence where practical.
- No AI-generated interview record may be finalized without explicit authorized review.
- A finalized record must not be silently overwritten.

## 8. UI Requirements

Recommended layout:

```text
Upload Area
  ↓
Task Progress
  ↓
Recording / Transcript Panel
  ↓
Structured Interview Editor
  ↓
Save / Generate / Download Actions
```

The UI must provide:

- drag-and-drop and file-picker upload;
- separate upload and processing indicators;
- media metadata and optional protected playback when supported;
- readable transcript with speaker and timestamp structure;
- clear uncertain-segment markers;
- editable structured fields;
- unsaved-change warning;
- validation summary;
- confirmation before discarding edits;
- keyboard-accessible controls and error announcements.

The transcript and structured record must not be visually presented as identical content.

## 9. API Requirements

Approved contracts from `API.md`:

```text
POST /api/interview-record/generate
GET  /api/tasks/{task_id}
GET  /api/interview-record/{id}
PUT  /api/interview-record/{id}
GET  /api/interview-record/{id}/download
```

The current API document lists `audio` and `video` form fields. Before implementation, `API.md` and backend schemas must clarify that the request accepts exactly one source field in the initial version.

Generation response must contain:

```json
{
  "task_id": "uuid"
}
```

The contracts must also define:

- how task completion identifies the generated record;
- transcript representation, speaker labels, timestamps, and uncertainty;
- structured record detail and update payloads;
- save-conflict behavior;
- download content type and filename.

Do not switch to plural paths without an intentional API revision.

## 10. Data Impact

Relevant target tables:

- `interview_records` for transcript, structured content, metadata, and status;
- `uploaded_files` for source recording and generated file metadata;
- `ai_tasks` for transcription and generation progress;
- `generated_documents` for versioned output files;
- `audit_logs` for significant access, edit, finalize, and download actions.

If segment-level transcript editing or provenance is required, a dedicated transcript-segment table must be designed and added to `DATABASE.md` before implementation rather than hidden in an undocumented schema.

## 11. AI Workflow and Rules

```text
Audio or Video
  ↓
Extract / Normalize Audio
  ↓
Speech Recognition
  ↓
Speaker Segmentation when Supported
  ↓
Transcript with Confidence Metadata
  ↓
LLM Structured Extraction
  ↓
Validate Structured Output
  ↓
Interview Record Draft
```

AI responsibilities:

- Speech recognition transcribes audible content.
- Speaker segmentation separates speakers when technically supported.
- The LLM organizes supplied transcript content into the required record structure.

AI constraints:

- The LLM must not reconstruct missing speech as fact.
- Uncertain segments must remain visible to the review workflow.
- Speaker labels must not be converted to identities without user-confirmed evidence.
- The structured result must use validated JSON or equivalent typed output.
- Provider and model names come from configuration.
- Prompts, credentials, and internal model diagnostics must not be exposed.

## 12. Validation

- Current documented audio types: `.wav`, `.mp3`, and `.m4a`.
- Current documented video types: `.mp4` and `.mov`.
- File-size and duration limits must come from backend configuration.
- The backend must verify extension, MIME type, file signature where practical, and size.
- Exactly one source media field is required.
- Start time must not be after end time.
- Required fields for finalization must be defined by backend business rules.
- Structured content must match the approved schema.

## 13. Error Handling

- Upload failure: retain safe selection and allow retry.
- Unsupported or oversized media: show exact permitted rules.
- No audible speech: return a specific result and do not fabricate a transcript.
- Transcription partial failure: preserve usable segments and mark gaps.
- Speaker segmentation failure: allow a transcript with neutral speaker labels.
- LLM structure failure: preserve the transcript and allow regeneration.
- Save conflict: preserve edits and offer reload/compare behavior.
- Template or download failure: preserve the reviewed record and allow retry.

## 14. Security and Privacy

- Recordings and transcripts are sensitive and require backend authorization.
- Use protected object storage and safe or signed download URLs.
- Do not expose storage paths or public permanent links.
- Do not log full recordings, transcripts, structured content, tokens, or prompts.
- Apply explicit retention and temporary-file cleanup policies.
- Send only required content to external AI providers and document provider data handling before production use.
- Client-provided identities and record ownership must be verified by the backend.

## 15. Non-Functional Requirements

- Transcription and generation must run asynchronously.
- Task retries should be idempotent where practical.
- Long transcripts must remain navigable and editable without freezing the page.
- Temporary network loss must not discard saved work.
- The interface must be usable on desktop and tablet.
- Significant access and finalization actions must be auditable.

## 16. Future Improvements

- real-time recording and transcription;
- transcript search and synchronized playback;
- user-confirmed speaker mapping;
- multiple recordings;
- translation;
- electronic signatures;
- transcript diff and record version comparison;
- external case-system integration.

## 17. Acceptance Criteria

- [x] Exactly one valid audio or video source creates one task.
- [x] Task polling stops at completed, failed, or cancelled status.
- [x] The transcript is preserved separately from the structured record.
- [x] Uncertain or inaudible speech is visible and not invented.
- [x] Users can review and edit interview metadata and structured content.
- [x] Saved changes persist through the backend.
- [x] The generated document matches saved reviewed structured data.
- [x] Finalized document versions are not silently overwritten.
- [x] Protected media, transcript, record, and document access requires authorization.
- [x] Available lint, type, test, migration, and build checks pass.
