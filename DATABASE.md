# DATABASE.md

# Database Design

This document describes the database structure, relationships, constraints, and data ownership of the Fire Intelligence Platform.

It should remain synchronized with the actual database models and migrations.

The database is the source of truth for business data.

AI-generated intermediate files and vector embeddings should not replace structured business records.

---

# Database Technology

Primary relational database:

- PostgreSQL

ORM:

- SQLAlchemy

Schema validation:

- Pydantic

Migration tool:

- Alembic

File storage:

- Supabase Storage
- S3-compatible object storage
- Local storage for development only

Vector database:

- Chroma or another configured vector store

The vector database stores retrieval data only.

Business data must remain in PostgreSQL.

---

# Design Principles

- Use UUID primary keys.
- Store timestamps in UTC.
- Use foreign keys for relationships.
- Avoid storing duplicated business data.
- Use soft deletion when records may need recovery or audit.
- Keep AI task records separate from final business documents.
- Store large files in object storage, not directly in database columns.
- Store file metadata and storage paths in the database.
- Use migrations for every schema change.
- Never modify production tables manually without a migration.

---

# Naming Conventions

Table names use plural snake_case.

Examples:

```text
users
inspection_records
photo_reports
knowledge_documents
ai_tasks
```

Column names use snake_case.

Examples:

```text
created_at
updated_at
storage_path
task_status
```

Foreign keys use the referenced entity name followed by `_id`.

Examples:

```text
user_id
inspection_record_id
task_id
```

---

# Common Fields

Most business tables should include:

```text
id
created_at
updated_at
created_by
deleted_at
```

Recommended definitions:

```text
id          UUID        Primary key
created_at  TIMESTAMP   Creation time
updated_at  TIMESTAMP   Last update time
created_by  UUID        User who created the record
deleted_at  TIMESTAMP   Soft deletion time
```

`deleted_at` is nullable.

A non-null `deleted_at` means the record has been soft deleted.

---

# Core Entities

The target initial database design contains the following core entities:

- users
- user_profiles
- inspection_records
- inspection_record_items
- photo_reports
- photo_report_images
- interview_records
- uploaded_files
- generated_documents
- ai_tasks
- knowledge_documents
- knowledge_index_jobs
- audit_logs

---

# Entity Relationships

```text
users
  |
  +-- user_profiles
  |
  +-- inspection_records
  |     |
  |     +-- inspection_record_items
  |     +-- uploaded_files
  |     +-- generated_documents
  |
  +-- photo_reports
  |     |
  |     +-- photo_report_images
  |     +-- uploaded_files
  |     +-- generated_documents
  |
  +-- interview_records
  |     |
  |     +-- uploaded_files
  |     +-- generated_documents
  |
  +-- knowledge_documents
  |
  +-- ai_tasks
  |
  +-- audit_logs
```

---

# Table: users

Stores authentication-related user information.

If authentication is managed by Supabase Auth or another identity provider, this table may reference the external authentication user ID.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| auth_provider_id | VARCHAR | No | External authentication user ID |
| email | VARCHAR | Yes | User email |
| username | VARCHAR | No | Display username |
| role | VARCHAR | Yes | User role |
| is_active | BOOLEAN | Yes | Whether the account is active |
| last_login_at | TIMESTAMP | No | Last login time |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |
| deleted_at | TIMESTAMP | No | Soft deletion time |

## Role Values

```text
admin
supervisor
inspector
viewer
```

## Constraints

- `email` must be unique.
- `role` must use an approved value.
- Deleted users should not be returned by normal queries.

---

# Table: user_profiles

Stores user profile information separate from authentication data.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| user_id | UUID | Yes | References users.id |
| full_name | VARCHAR | No | Full name |
| department | VARCHAR | No | Department |
| position | VARCHAR | No | Position |
| phone | VARCHAR | No | Phone number |
| avatar_path | VARCHAR | No | Avatar storage path |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |

## Constraints

- `user_id` must be unique.
- One user has at most one profile.

---

# Table: inspection_records

Stores fire inspection record documents.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| record_number | VARCHAR | No | Business record number |
| title | VARCHAR | No | Record title |
| inspection_unit | VARCHAR | No | Inspected organization |
| inspection_address | VARCHAR | No | Inspection address |
| inspection_date | TIMESTAMP | No | Inspection date |
| inspector_names | JSONB | No | Inspector name list |
| contact_person | VARCHAR | No | Contact person |
| contact_phone | VARCHAR | No | Contact phone |
| summary | TEXT | No | Inspection summary |
| conclusion | TEXT | No | Inspection conclusion |
| status | VARCHAR | Yes | Record status |
| source_task_id | UUID | No | AI task that generated the record |
| created_by | UUID | Yes | References users.id |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |
| deleted_at | TIMESTAMP | No | Soft deletion time |

## Status Values

```text
draft
processing
generated
reviewed
finalized
archived
failed
```

## Constraints

- `record_number` should be unique when present.
- Finalized records should not be silently overwritten.
- AI-generated content must remain editable before finalization.

---

# Table: inspection_record_items

Stores individual inspection findings or violations.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| inspection_record_id | UUID | Yes | References inspection_records.id |
| item_type | VARCHAR | Yes | Finding type |
| location | VARCHAR | No | Finding location |
| description | TEXT | Yes | Finding description |
| legal_basis | TEXT | No | Relevant legal basis |
| correction_requirement | TEXT | No | Required correction |
| severity | VARCHAR | No | Severity level |
| sort_order | INTEGER | Yes | Display order |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |

## Item Type Values

```text
compliant
violation
hazard
observation
recommendation
```

## Severity Values

```text
low
medium
high
critical
```

---

# Table: photo_reports

Stores photo report documents.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| title | VARCHAR | No | Report title |
| inspection_unit | VARCHAR | No | Inspected organization |
| inspection_address | VARCHAR | No | Inspection address |
| violation_summary | TEXT | No | Summary of violations |
| status | VARCHAR | Yes | Report status |
| source_task_id | UUID | No | AI generation task |
| created_by | UUID | Yes | References users.id |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |
| deleted_at | TIMESTAMP | No | Soft deletion time |

---

# Table: photo_report_images

Stores images and captions included in a photo report.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| photo_report_id | UUID | Yes | References photo_reports.id |
| uploaded_file_id | UUID | Yes | References uploaded_files.id |
| frame_timestamp | FLOAT | No | Source video timestamp in seconds |
| caption | TEXT | No | Editable image caption |
| detected_address | VARCHAR | No | Address recognized from image |
| detected_violation | TEXT | No | Violation recognized from image |
| is_selected | BOOLEAN | Yes | Whether included in final document |
| sort_order | INTEGER | Yes | Display order |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |

## Constraints

- Image captions must remain editable.
- Multiple images may belong to one photo report.
- Removing an image from a report should not necessarily delete the original file.

---

# Table: interview_records

Stores interview or inquiry record documents.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| title | VARCHAR | No | Record title |
| interviewee_name | VARCHAR | No | Interviewed person |
| interviewer_names | JSONB | No | Interviewer list |
| location | VARCHAR | No | Interview location |
| started_at | TIMESTAMP | No | Start time |
| ended_at | TIMESTAMP | No | End time |
| transcript | TEXT | No | Speech transcript |
| structured_content | JSONB | No | Structured interview content |
| status | VARCHAR | Yes | Record status |
| source_task_id | UUID | No | AI task |
| created_by | UUID | Yes | References users.id |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |
| deleted_at | TIMESTAMP | No | Soft deletion time |

---

# Table: uploaded_files

Stores metadata for uploaded files.

The actual file should be stored in object storage.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| original_name | VARCHAR | Yes | Original filename |
| storage_path | VARCHAR | Yes | Object storage path |
| storage_provider | VARCHAR | Yes | Storage provider |
| mime_type | VARCHAR | No | MIME type |
| file_extension | VARCHAR | No | File extension |
| size_bytes | BIGINT | Yes | File size |
| checksum | VARCHAR | No | File checksum |
| category | VARCHAR | Yes | File category |
| uploaded_by | UUID | Yes | References users.id |
| created_at | TIMESTAMP | Yes | Upload time |
| deleted_at | TIMESTAMP | No | Soft deletion time |

## Category Values

```text
video
image
audio
document
template
generated_document
knowledge_source
```

## Constraints

- Do not store file binary data directly in this table.
- Storage paths should be unique where practical.
- Validate file type and size before processing.

---

# Table: generated_documents

Stores generated Word, PDF, or other output documents.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| document_type | VARCHAR | Yes | Document type |
| source_entity_type | VARCHAR | Yes | Source business entity |
| source_entity_id | UUID | Yes | Source business entity ID |
| uploaded_file_id | UUID | Yes | References uploaded_files.id |
| version | INTEGER | Yes | Document version |
| generated_by_task_id | UUID | No | References ai_tasks.id |
| created_by | UUID | Yes | References users.id |
| created_at | TIMESTAMP | Yes | Creation time |

## Document Type Values

```text
inspection_record_docx
photo_report_docx
interview_record_docx
inspection_record_pdf
photo_report_pdf
interview_record_pdf
```

## Constraints

- Do not overwrite previous finalized document versions.
- Increment `version` when regenerating a finalized document.
- Preserve download history where required.

---

# Table: ai_tasks

Stores asynchronous AI processing tasks.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| task_type | VARCHAR | Yes | Task category |
| status | VARCHAR | Yes | Task status |
| progress | INTEGER | Yes | Progress from 0 to 100 |
| current_stage | VARCHAR | No | Current processing stage |
| input_data | JSONB | No | Non-sensitive task input metadata |
| result_data | JSONB | No | Structured AI result |
| error_code | VARCHAR | No | Machine-readable error code |
| error_message | TEXT | No | Readable error message |
| started_at | TIMESTAMP | No | Task start time |
| completed_at | TIMESTAMP | No | Task completion time |
| created_by | UUID | Yes | References users.id |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |

## Status Values

```text
pending
queued
processing
completed
failed
cancelled
```

## Task Type Values

```text
inspection_record_generation
photo_report_generation
interview_record_generation
speech_transcription
video_analysis
document_generation
knowledge_indexing
knowledge_reindexing
```

## Constraints

- `progress` must be between 0 and 100.
- Completed tasks should have `completed_at`.
- Failed tasks should have `error_message`.
- Sensitive file content should not be copied into `input_data`.

---

# Table: knowledge_documents

Stores source documents used by the knowledge base.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| title | VARCHAR | Yes | Document title |
| document_type | VARCHAR | No | Source document type |
| uploaded_file_id | UUID | Yes | References uploaded_files.id |
| status | VARCHAR | Yes | Indexing status |
| version | VARCHAR | No | Document version |
| issuing_authority | VARCHAR | No | Issuing authority |
| effective_date | DATE | No | Effective date |
| expiration_date | DATE | No | Expiration date |
| chunk_count | INTEGER | No | Indexed chunk count |
| checksum | VARCHAR | No | Content checksum |
| metadata | JSONB | No | Additional document metadata |
| created_by | UUID | Yes | References users.id |
| created_at | TIMESTAMP | Yes | Creation time |
| updated_at | TIMESTAMP | Yes | Last update time |
| deleted_at | TIMESTAMP | No | Soft deletion time |

## Status Values

```text
uploaded
parsing
indexing
indexed
failed
outdated
```

## Constraints

- Duplicate documents should be detected using checksum where possible.
- Re-indexing must not silently create duplicate active versions.
- Deleted knowledge documents should also be removed from the vector index.

---

# Table: knowledge_index_jobs

Stores knowledge base indexing jobs.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| knowledge_document_id | UUID | No | References knowledge_documents.id |
| ai_task_id | UUID | No | References ai_tasks.id |
| action | VARCHAR | Yes | Index operation |
| status | VARCHAR | Yes | Job status |
| indexed_chunks | INTEGER | No | Number of indexed chunks |
| error_message | TEXT | No | Error message |
| created_at | TIMESTAMP | Yes | Creation time |
| completed_at | TIMESTAMP | No | Completion time |

## Action Values

```text
index
reindex
delete_index
full_rebuild
```

---

# Table: audit_logs

Stores important user and system actions.

## Columns

| Column | Type | Required | Description |
|---|---|---:|---|
| id | UUID | Yes | Primary key |
| user_id | UUID | No | References users.id |
| action | VARCHAR | Yes | Action name |
| entity_type | VARCHAR | No | Target entity type |
| entity_id | UUID | No | Target entity ID |
| request_id | VARCHAR | No | Request trace ID |
| ip_address | VARCHAR | No | Request IP |
| details | JSONB | No | Safe action metadata |
| created_at | TIMESTAMP | Yes | Creation time |

## Example Actions

```text
user.login
inspection_record.create
inspection_record.finalize
photo_report.generate
knowledge_document.upload
knowledge_document.delete
document.download
```

## Constraints

- Audit logs should normally be append-only.
- Do not store passwords, tokens, or full sensitive document content.
- Access to audit logs should be restricted.

---

# Optional Tables

The following tables may be added when needed:

- roles
- permissions
- role_permissions
- user_roles
- organizations
- departments
- inspection_units
- model_configurations
- prompt_versions
- evaluation_results
- notifications

Do not create these tables before the corresponding feature is required.

---

# Indexes

Recommended indexes:

```text
users.email
inspection_records.created_by
inspection_records.status
inspection_records.inspection_date
photo_reports.created_by
interview_records.created_by
uploaded_files.uploaded_by
uploaded_files.checksum
ai_tasks.status
ai_tasks.task_type
knowledge_documents.status
knowledge_documents.checksum
audit_logs.user_id
audit_logs.created_at
```

Use composite indexes only when query patterns justify them.

Example:

```text
ai_tasks(created_by, status, created_at)
inspection_records(created_by, status, created_at)
```

---

# Data Ownership

Users may normally access records they created or records belonging to their organization.

Administrators may access all records according to permission rules.

Authorization must be enforced by the backend.

Frontend visibility is not a security boundary.

---

# File Deletion Rules

Deleting a business record should not immediately remove shared source files.

Recommended flow:

```text
Business record soft deleted
        ↓
Check file references
        ↓
Mark unused files for cleanup
        ↓
Delete storage object asynchronously
```

Do not delete a storage file while it is still referenced by another record.

---

# AI Data Rules

AI outputs should be stored as structured data whenever practical.

Examples:

```text
result_data
structured_content
detected_violation
legal_basis
```

Do not rely only on generated Word files as the business record.

Generated files are outputs.

Structured database records are the source of truth.

---

# Transaction Rules

Use database transactions for operations involving multiple related writes.

Examples:

- Create inspection record and its items.
- Create photo report and report images.
- Finalize a record and create a generated document.
- Delete a knowledge document and schedule vector index cleanup.

Rollback the complete operation when a required step fails.

---

# Migration Rules

Every schema change must include an Alembic migration.

Migration process:

```text
Update SQLAlchemy models
        ↓
Create Alembic migration
        ↓
Review generated migration
        ↓
Test upgrade
        ↓
Test downgrade where practical
        ↓
Apply migration
```

Never edit old migrations that have already been applied to shared environments.

Create a new corrective migration instead.

---

# Backup and Recovery

Production databases should have:

- Automated backups
- Point-in-time recovery where supported
- Object storage versioning where supported
- Tested restoration procedures

Vector indexes may be rebuilt from source documents.

Business records must be backed up.

---

# Security Rules

- Never store plaintext passwords.
- Never store API keys in database business tables.
- Encrypt sensitive data when required.
- Restrict database credentials by environment.
- Use least-privilege database accounts.
- Validate all client input.
- Enforce authorization in backend services.
- Avoid exposing internal database IDs when unnecessary.

---

# Data Retention

Retention rules should be defined before production deployment.

Suggested categories:

```text
Business records
Generated documents
Uploaded source files
AI task logs
Audit logs
Temporary processing files
Knowledge base documents
```

Temporary processing files should be cleaned automatically.

Finalized legal or inspection documents may require long-term retention.

---

# Current Implementation Status

Update this section as the project evolves.

## Implemented Tables

- [ ] users
- [ ] user_profiles
- [ ] inspection_records
- [ ] inspection_record_items
- [ ] photo_reports
- [ ] photo_report_images
- [ ] interview_records
- [ ] uploaded_files
- [ ] generated_documents
- [ ] ai_tasks
- [ ] knowledge_documents
- [ ] knowledge_index_jobs
- [ ] audit_logs

## Current Database

```text
Database: Not configured
ORM: Not installed
Migration tool: Not initialized
Storage provider: Not configured
Vector database: Not configured
```

## Notes

Record unresolved database decisions here.

- The repository currently contains the target schema design only.
- No SQLAlchemy models or Alembic migrations have been created.
