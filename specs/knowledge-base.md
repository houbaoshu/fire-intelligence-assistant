# Knowledge Base Management

## 1. Purpose

The Knowledge Base feature lets authorized users manage source documents used by RAG. It must make parsing and indexing status visible, prevent silent duplication, and keep relational metadata, object storage, and the vector index synchronized.

## 2. Status and Scope

**Status:** Planned. No application code exists in the current repository, so implementation is not verified.

Current scope:

- list authorized knowledge documents;
- upload one supported document at a time;
- track parsing and indexing status;
- show document metadata and failures;
- delete a document with confirmation;
- trigger a full index rebuild;
- refresh the list after mutations.

Out of scope for the first version:

- in-browser document editing;
- folder hierarchies;
- collaborative annotation;
- automatic web crawling;
- spreadsheet indexing;
- document-level sharing workflows;
- manual chunk editing.

## 3. Users and Permissions

- **Administrator**: uploads, deletes, and rebuilds knowledge content when authorized.
- **Supervisor**: may view status and manage content when explicitly permitted.
- **Inspector**: normally consumes indexed content through QA and may have read-only status access.
- **Viewer**: no management permission by default.

Upload, deletion, rebuild, and source-document access must be enforced by backend permissions.

## 4. Goals

Authorized users must be able to:

- understand which documents are available to RAG;
- add supported source material;
- see whether parsing and indexing succeeded;
- diagnose a failed document without reading backend logs;
- remove obsolete documents from both business metadata and retrieval;
- rebuild the index without creating duplicate active chunks.

## 5. User Workflow

```text
Open Knowledge Base
  ↓
Load Document List
  ├─ Upload Document
  │      ↓
  │   Store Source
  │      ↓
  │   Parse → Chunk → Embed → Index
  │      ↓
  │   Show Indexed / Failed Status
  │
  ├─ Delete Document → Confirm → Remove Index Entries
  │
  └─ Rebuild Index → Confirm → Track Task → Refresh
```

## 6. Functional Requirements

### Document List

The list must show available metadata:

- title;
- document type;
- version;
- issuing authority;
- effective and expiration dates;
- indexing status;
- chunk count;
- last updated time;
- safe failure summary when applicable.

The list must support a useful empty state, refresh, and status filtering when the backend supports it.

### Upload

- Users must select a supported document.
- Filename and size must be displayed before upload.
- Upload progress and indexing progress must be separate.
- Metadata required by backend schemas must be collected or extracted.
- The UI must not show `indexed` until the backend confirms index completion.

### Index Status

Supported document states from `DATABASE.md`:

```text
uploaded
parsing
indexing
indexed
failed
outdated
```

- Status must be readable without relying on color.
- Failed documents must show a safe actionable message.
- Long-running indexing should use the shared task pattern once its response contract is defined.

### Delete

- Deletion requires explicit confirmation with the document title.
- The backend must coordinate relational metadata, source-file lifecycle, and vector-index removal.
- The UI must not remove the row permanently until the backend confirms the operation.
- A partial deletion failure must remain visible for recovery.

### Rebuild

- Full rebuild requires confirmation because it may be expensive and temporarily affect retrieval.
- Only one equivalent rebuild should run at a time unless the backend supports concurrency safely.
- Progress and failure details must be visible.
- Rebuild must not create duplicate active chunks.

## 7. Business Rules

- Original source documents remain the authoritative input for rebuilding retrieval data.
- The vector store contains derived chunks and embeddings, not primary business records.
- Duplicate content should be detected by checksum where practical.
- A new version must not silently replace a current version without explicit version rules.
- Effective, expired, superseded, and outdated documents must remain distinguishable.
- Deleted or unauthorized documents must no longer be retrievable.
- Indexing success requires all required metadata and vector entries to be committed consistently.
- Rebuild must be recoverable; a failed rebuild must not silently destroy the last usable index.
- RAG answers must retain traceable references to document metadata.

## 8. UI Requirements

Recommended layout:

```text
Page Header and Knowledge Status
  ↓
Upload and Rebuild Actions
  ↓
Filters
  ↓
Document Table / Cards
  ↓
Status and Error Details
```

The UI must provide:

- accessible file picker or drop zone;
- selected-file metadata;
- upload and indexing progress;
- responsive document list;
- status filters when useful;
- confirmation dialogs for delete and rebuild;
- disabled duplicate actions while requests are active;
- empty, loading, partial-failure, and full-error states;
- Chinese user-facing labels and actionable errors.

Document status and destructive actions must remain usable by keyboard.

## 9. API Requirements

Approved contracts from `API.md`:

```text
GET    /api/knowledge/documents
POST   /api/knowledge/documents
DELETE /api/knowledge/documents/{id}
POST   /api/knowledge/rebuild
GET    /api/tasks/{task_id}
```

Upload uses `FormData` with:

```text
file
```

Before implementation, `API.md` and backend schemas must define:

- list response and pagination behavior;
- upload metadata fields;
- whether upload returns a document, a `task_id`, or both;
- deletion completion and partial-failure semantics;
- rebuild response and task tracking;
- safe error-code values;
- status filtering and ordering.

No detail, retry, or per-document reindex endpoint is currently approved. Add such contracts to `API.md` before implementation.

## 10. Data Impact

Relevant target tables:

- `knowledge_documents` for source metadata and current index status;
- `knowledge_index_jobs` for index operations and outcomes;
- `uploaded_files` for original source-file metadata;
- `ai_tasks` for asynchronous indexing and rebuild tasks;
- `audit_logs` for upload, deletion, and rebuild actions.

The configured vector store holds chunks, embeddings, and source references. Object storage holds the original document.

## 11. AI and RAG Workflow

Indexing pipeline:

```text
Source Document
  ↓
Validate and Store
  ↓
Parse
  ↓
Normalize
  ↓
Semantic Chunking
  ↓
Metadata Enrichment
  ↓
Embedding
  ↓
Vector Index
  ↓
Mark Document Indexed
```

Required metadata should preserve available values such as:

- document ID and title;
- document type and version;
- page number;
- chapter, section, or article;
- effective date and issuing authority;
- source reference.

AI/RAG constraints:

- Parsing, chunking, embedding, storage, retrieval, and reranking remain separate responsibilities.
- Model and provider selection comes from configuration.
- Re-indexing must remove or replace stale chunks deterministically.
- A document must not be marked indexed when required stages fail.
- Full document contents, embeddings, prompts, and provider details must not be sent to the frontend.

## 12. Validation

Current upload types approved by `API.md`:

- `.pdf`;
- `.doc`;
- `.docx`;
- `.ppt`;
- `.pptx`.

`PROJECT.md` also lists text and Markdown as target formats, but they are not part of the current API upload rules. Add them to `API.md` before implementation.

Additional validation:

- file-size limits come from backend configuration;
- backend validates extension, MIME type, file signature where practical, and size;
- checksum is computed for duplicate detection;
- required title and metadata are validated;
- effective date must not be after expiration date;
- unsupported encrypted or corrupted files return a specific error.

## 13. Error Handling

- Upload failure: retain safe metadata and allow retry.
- Duplicate document: identify the existing document or require an explicit version action.
- Parser failure: mark the document failed with a safe reason.
- Partial indexing failure: do not mark the document indexed.
- Embedding or vector-store failure: preserve the source document and allow retry.
- Delete cleanup failure: show partial state and schedule or expose recovery.
- Rebuild failure: preserve the last usable index when architecture permits.
- Backend unavailable: keep current list visible and mark it stale.

## 14. Security and Privacy

- Management endpoints require explicit backend authorization.
- Source files and previews require protected access.
- Uploaded documents are untrusted and must be parsed in a constrained environment.
- Reject or sanitize active content and dangerous file behavior.
- Never expose storage paths, vector identifiers, credentials, or raw parser traces.
- Logs must not contain full document contents by default.
- Deletion and rebuild actions must be audited.
- Retrieval must enforce document permissions before content reaches an AI model.

## 15. Non-Functional Requirements

- Parsing and indexing must run asynchronously for large documents.
- Upload and indexing retries should be idempotent where practical.
- Index rebuild must expose progress and remain recoverable.
- The document list must support future pagination without breaking its contract.
- Status refresh must avoid duplicate polling.
- Indexing metrics may record durations and counts without storing sensitive content.

## 16. Future Improvements

- text, Markdown, and XLSX support after API approval;
- per-document reindex and retry;
- source preview;
- version comparison and supersession workflows;
- metadata extraction review;
- document-level access control;
- chunk diagnostics for administrators;
- scheduled synchronization from approved repositories.

## 17. Acceptance Criteria

- [ ] Authorized users can list knowledge documents and see accurate status.
- [ ] A valid supported document can be uploaded without being marked indexed prematurely.
- [ ] Parsing, chunking, embedding, and indexing produce traceable source metadata.
- [ ] Duplicate content is detected or handled through explicit version rules.
- [ ] Failed indexing shows an actionable error and does not create an active partial index silently.
- [ ] Deleting a document removes it from future retrieval and handles storage cleanup safely.
- [ ] Full rebuild reports progress and does not create duplicate active chunks.
- [ ] Unauthorized users cannot manage or retrieve restricted source content.
- [ ] Empty, loading, indexing, indexed, outdated, failed, and backend-error states are distinct.
- [ ] Available lint, type, test, migration, and build checks pass.
