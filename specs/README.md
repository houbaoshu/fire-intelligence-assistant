# Feature Specifications Guide

This directory contains feature specifications for the Fire Intelligence Platform.

Each file describes one product capability. A specification defines required behavior and acceptance criteria; it does not claim that the feature is already implemented.

## Source-of-Truth Order

When documents overlap, use this order:

1. `AGENTS.md` for repository-wide development rules.
2. `PROJECT.md` for product scope and project facts.
3. `ARCHITECTURE.md` for system boundaries and component responsibilities.
4. `AI_CONTEXT.md` for AI responsibilities and workflows.
5. `API.md` for approved HTTP contracts.
6. `DATABASE.md` for target data design.
7. `ROADMAP.md` for milestone order.
8. The relevant file in `specs/` for feature behavior.

If a specification conflicts with an implemented API or database migration, inspect the implementation and resolve the conflict before changing code. Do not silently create a second contract.

## Directory

```text
specs/
├── README.md
├── authentication.md
├── dashboard.md
├── regulation-qa.md
├── inspection-record.md
├── photo-report.md
├── interview-record.md
├── knowledge-base.md
├── settings.md
├── statistics.md
└── workflow.md
```

## Status Language

Every specification must identify its status:

- **Planned**: target behavior only; implementation has not been verified.
- **In Progress**: some acceptance criteria are implemented.
- **Implemented**: all current acceptance criteria have been verified.
- **Deferred**: intentionally postponed.

Do not change a specification to **Implemented** until the code, tests, and required checks have been inspected.

## Standard Structure

Use the following sections when relevant:

1. **Purpose** — the problem the feature solves.
2. **Status and Scope** — current status, included behavior, and exclusions.
3. **Users and Permissions** — who uses the feature and what access is required.
4. **Goals** — outcomes users must be able to achieve.
5. **User Workflow** — the end-to-end user journey.
6. **Functional Requirements** — observable product behavior.
7. **Business Rules** — domain constraints and review requirements.
8. **UI Requirements** — inputs, actions, states, and accessibility.
9. **API Requirements** — approved contracts from `API.md`.
10. **Data Impact** — relevant entities from `DATABASE.md`.
11. **AI Workflow and Rules** — only when AI is involved.
12. **Validation** — required values, limits, and allowed inputs.
13. **Error Handling** — failures and user-visible recovery.
14. **Security and Privacy** — authorization and sensitive-data rules.
15. **Non-Functional Requirements** — reliability, performance, and accessibility.
16. **Future Improvements** — explicitly excluded later work.
17. **Acceptance Criteria** — testable completion conditions.

Sections may be omitted when they do not apply, but acceptance criteria are always required.

## Writing Rules

- Describe behavior, not source-code implementation.
- Use normative language: **must**, **should**, and **may**.
- Keep one feature per file.
- Separate current requirements from future ideas.
- Reference shared documents instead of duplicating global rules.
- Never invent a backend response merely to complete a UI specification.
- Mark proposed endpoints clearly and update `API.md` before implementation.
- Keep user-facing text in Chinese unless the existing interface establishes another convention.
- Treat AI output as a draft until a user reviews it when legal or inspection content is involved.

Good:

> The page must display upload progress and a recoverable error when an upload fails.

Avoid:

> Store upload progress in a state variable named `uploadProgress`.

## API Contract Rules

Paths and payloads in `API.md` are authoritative. The current documented business paths use singular resource names, for example:

```text
/api/inspection-record/{id}
/api/photo-report/{id}
/api/interview-record/{id}
```

Specifications must not switch these to plural paths without an intentional API revision.

When a required endpoint is missing:

1. Mark it as proposed in the specification.
2. Define only the minimum behavior needed.
3. Update `API.md` before implementation.
4. Preserve backward compatibility where possible.

## Long-Running Task Rules

AI processing, indexing, transcription, and document generation may be asynchronous.

```text
Submit
  ↓
Receive task_id
  ↓
Poll task status
  ↓
Completed / Failed / Cancelled
```

The frontend must stop polling after a terminal state and must show the backend error message when safe to do so.

## AI Rules

When AI is involved:

- AI processing belongs to the backend.
- Intermediate results should be structured whenever practical.
- Evidence and AI interpretation must remain distinguishable.
- The system must not fabricate regulations, addresses, violations, people, or equipment.
- Low-confidence or missing evidence must trigger uncertainty or manual review.
- Prompts and provider details must not be exposed to the frontend.

## Acceptance Criteria Rules

Acceptance criteria must be observable and testable. Include, as relevant:

- the primary user journey succeeds;
- empty, loading, success, failure, and retry states work;
- authorization is enforced by the backend;
- API requests use the centralized client;
- AI results remain reviewable and editable;
- the frontend does not contain backend business or AI logic;
- lint, type checks, tests, and production build pass when those tools exist.

## Implementation Workflow

Before implementing a specification, an AI coding assistant should:

1. Read the repository instructions and shared project documents.
2. Inspect the actual source code, models, migrations, and tests.
3. Compare current behavior with the selected specification.
4. Implement only the requested scope.
5. Add or update API documentation and migrations when required.
6. Verify the relevant user journey and failure states.
7. Run the available quality checks.
8. Update the specification status only when evidence supports it.

Do not implement all specifications at once merely because they exist in this directory.
