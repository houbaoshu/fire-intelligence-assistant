# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Added

- Complete Milestones 2–4 business workflows for inspection records, photo reports, and interview records with validated media uploads, durable generation tasks, structured human review, optimistic revisions, protected previews, and versioned DOCX downloads.
- Regulation knowledge management with checksum duplicate detection, PDF/DOC/DOCX/PPT/PPTX parsing, semantic-boundary chunking, optional embeddings, organization-scoped retrieval, grounded QA citations, safe no-evidence behavior, deletion, and rebuild.
- Durable task dispatcher with startup recovery, monotonic progress, terminal polling, bounded retry, cancellation, idempotency keys, safe error codes, recent-task APIs, and a frontend task center.
- Accurate permission-scoped statistics APIs and responsive dashboard/statistics interfaces with explicit scope, timezone, last-update, empty, and error states.
- Organizations, departments, memberships, configurable role permissions, organization-derived data scope, and protected audit-log access.
- Configurable OpenAI-compatible language, vision, speech, and embedding services; FFmpeg media extraction; evidence-frame quality and duplicate filtering; provider-neutral agent, MCP/tool, model-routing, workflow, plugin, prompt, and evaluation contracts.
- AI-platform administrator registries for model configurations, prompt versions, workflow definitions, plugins, and evaluation runs without storing deployment secrets.
- Docker images, a health-aware PostgreSQL Compose topology, CI checks, authenticated operational counters, and documented backup, restore, and single-replica task scaling procedures.
- Alembic roadmap schema migration and integration coverage for task failure safety, authorization, validation, statistics, and existing foundation behavior.

- Project governance and architecture documentation.
- Target API, database, AI, and roadmap documentation.
- Planned feature specifications for authentication, dashboard, regulation QA, inspection records, photo reports, interview records, knowledge base, settings, statistics, and workflow management.
- FastAPI backend foundation with centralized environment configuration, structured request logging, standard error envelopes, CORS, and a database-aware health endpoint.
- SQLAlchemy identity and audit models with an Alembic migration and PostgreSQL-compatible configuration using SQLite for local development.
- Protected local object-storage abstraction with safe generated paths.
- Registration, login, current-user, and public auth-configuration APIs with scrypt password hashing and signed bearer tokens.
- Frontend authentication provider, session-expiry handling, protected business routes, login and registration pages, and sign-out controls.
- Backend unit/integration tests for authentication, token/password security, health, storage path safety, and migration round trips.

### Changed

- Replaced all business UI scaffolds with real backend data, generation progress recovery, editable review flows, protected image/download handling, role-aware knowledge controls, safe capability diagnostics, and working local accessibility preferences.
- Marked Roadmap Milestones 2–8 and their current feature specifications implemented after backend lint, strict typing, tests, migration round trips, frontend type checks, lint, and production build verification.
- Kept inspector notes separate from AI output and removed them from task queue payloads.

- Updated project, architecture, database, API, authentication, and roadmap status to reflect completion of Foundation Platform Milestone 1.
- Unified documented API resource paths, error responses, task states, and knowledge-document format scope.

### Fixed

- Formatted pre-existing frontend files so the configured lint check completes without formatting errors.

### Removed

None.

## Version Format

```text
MAJOR.MINOR.PATCH
