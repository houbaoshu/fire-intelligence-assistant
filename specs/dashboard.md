# Dashboard

## 1. Purpose

The dashboard provides a trustworthy overview of platform health, recent work, and common actions. It must help inspectors resume work quickly without presenting invented operational data.

## 2. Status and Scope

**Status:** Implemented. Health, authorized statistics, recent tasks, and registered shortcuts are wired through the shared query and API layers.

Current scope:

- backend connection status;
- summary values returned by the backend;
- recent AI or document tasks when a supported API is available;
- knowledge-base status when a supported API is available;
- shortcuts to core modules;
- empty and failure states.

Out of scope:

- configurable BI dashboards;
- predictive risk scoring;
- cross-organization benchmarking;
- exporting dashboard analytics;
- live push updates.

## 3. Users and Permissions

- **Inspector**: sees permitted personal or organizational activity.
- **Supervisor**: sees broader summaries when authorized.
- **Administrator**: sees system and organization summaries when authorized.
- **Viewer**: sees read-only information permitted by the backend.

The backend must filter all statistics and task data by the current user's permissions.

## 4. Goals

Users must be able to:

- determine whether the backend is reachable;
- see useful, real summary data;
- resume recent work;
- navigate to frequently used functions;
- distinguish an empty dataset from a loading or error state.

## 5. User Workflow

```text
Open Dashboard
  ↓
Load Health and Authorized Summaries
  ├─ Success → Show Metrics, Recent Work, Shortcuts
  ├─ Empty   → Show Helpful Empty States
  └─ Failure → Show Partial Results and Retry
```

## 6. Functional Requirements

### Backend Status

- The dashboard must request `GET /health`.
- It must display checking, connected, disconnected, and error states.
- The connected state must never be hardcoded.
- Users must be able to retry a failed check.

### Summary Cards

- Values must come from `GET /api/statistics`.
- Labels must match the meaning and time range returned by the backend.
- Missing values must display as unavailable, not as zero unless zero is confirmed.
- Cards must not imply trends unless comparison data exists.

### Recent Work

- Recent tasks or documents may be shown only after a list endpoint is approved.
- Each item should show type, status, updated time, and a safe navigation action.
- Failed work should show a recoverable state without exposing internal stack traces.

### Shortcuts

Provide shortcuts to permitted core modules:

- fire regulation QA;
- inspection record;
- photo report;
- interview record;
- knowledge base;
- statistics;
- settings.

Unavailable or unauthorized shortcuts must not appear active.

## 7. Business Rules

- Never display fabricated statistics, sample tasks, or placeholder success states as real data.
- Counts and statuses must represent only records visible to the current user.
- A backend outage must not be represented as an empty business dataset.
- The dashboard may render available sections when one request fails; one failed panel should not hide valid data from other panels.
- Dates and time ranges must be explicit enough to avoid misleading users.

## 8. UI Requirements

Recommended layout:

```text
Page Header and Backend Status
  ↓
Summary Cards
  ↓
Recent Work              Quick Actions
  ↓
Knowledge Status / Operational Notices
```

The UI must provide:

- responsive cards for desktop and tablet;
- accessible headings and link names;
- skeletons during initial loading;
- section-level errors with retry;
- empty states with a relevant next action;
- status labels that do not rely on color alone;
- consistent Chinese user-facing copy.

Avoid decorative charts when a simple number or list communicates the information more clearly.

## 9. API Requirements

Approved contracts:

```text
GET /health
GET /api/statistics
```

The exact statistics response is not defined in `API.md`. Before implementation, the backend schema and `API.md` must define:

- metric identifiers and labels;
- values and units;
- time range;
- optional comparison values;
- last-updated time.

Proposed future contracts:

```text
GET /api/tasks?limit={n}&status={status}
GET /api/knowledge/status
```

These are not approved until added to `API.md`.

## 10. Data Impact

The dashboard should aggregate existing authorized records rather than create a separate source of truth.

Potential sources:

- `inspection_records`;
- `photo_reports`;
- `interview_records`;
- `ai_tasks`;
- `knowledge_documents`;
- `generated_documents`.

Do not create a dashboard snapshot table until query performance or reporting requirements justify it.

## 11. AI Workflow

No AI inference is required for the initial dashboard.

Future AI summaries or recommendations must be explicitly specified, evidence-based, permission-aware, and visually distinguished from factual metrics.

## 12. Validation

- Unexpected null values must not break rendering.
- Unknown task statuses must display a neutral fallback.
- Dates must be parsed safely and formatted consistently.
- Negative counts or invalid percentages must be rejected or marked unavailable.
- Navigation targets must correspond to registered routes.

## 13. Error Handling

- Health failure: show disconnected status and retry.
- Statistics failure: show a panel-level error, not fake zeros.
- Partial response: render valid sections and mark missing sections unavailable.
- Unauthorized response: hide restricted data and do not repeatedly retry.
- Malformed response: show a readable data error and log only safe diagnostic metadata.

## 14. Security and Privacy

- The backend must scope dashboard data by user, role, and organization.
- The frontend must not request or display sensitive document content on the dashboard.
- Task previews must avoid sensitive source text and storage paths.
- URLs and identifiers must not bypass backend authorization.

## 15. Non-Functional Requirements

- Independent dashboard requests should not block one another unnecessarily.
- Duplicate requests should be avoided through shared query caching.
- Data should expose its refresh behavior and last-updated time when relevant.
- The page must remain usable when one service is unavailable.
- Keyboard focus order must follow the visual layout.

## 16. Future Improvements

- user-configurable panels;
- server-sent task updates;
- saved filters;
- exportable reports;
- evidence-based operational recommendations;
- authorized organization comparisons.

## 17. Acceptance Criteria

- [x] Backend status is based on `GET /health` and supports retry.
- [x] Summary values come from `GET /api/statistics`.
- [x] No invented or placeholder value is displayed as real data.
- [x] Loading, empty, partial-failure, and complete-failure states are distinct.
- [x] Shortcuts respect authorization and registered routes.
- [x] Missing values are shown as unavailable rather than assumed to be zero.
- [x] Dashboard requests use the centralized API client and shared query layer.
- [x] The layout is usable on desktop and tablet.
- [x] Statuses remain understandable without color.
- [x] Available lint, type, test, and build checks pass.
