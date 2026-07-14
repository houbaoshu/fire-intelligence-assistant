# Statistics

## 1. Purpose

The Statistics feature presents accurate, permission-scoped summaries of inspection work, generated documents, AI tasks, and knowledge-base operations. It supports operational awareness without inventing metrics or treating AI estimates as verified business facts.

## 2. Status and Scope

**Status:** Implemented. Permission-scoped backend aggregation and accessible frontend summary and status tables are implemented.

Current scope:

- read-only authorized statistics from the backend;
- summary cards;
- simple trends or distributions only when the API supplies the necessary dimensions;
- clear date range and last-updated context;
- loading, empty, partial, and error states.

Out of scope for the first version:

- custom report builder;
- arbitrary database queries;
- predictive risk scores;
- cross-organization ranking;
- downloadable analytics;
- real-time streaming dashboards.

## 3. Users and Permissions

- **Inspector**: views authorized personal or assigned-work summaries.
- **Supervisor**: views authorized team or organization summaries.
- **Administrator**: views broader operational summaries when permitted.
- **Viewer**: read-only access to explicitly allowed statistics.

The backend must enforce scope. Frontend filters cannot expand a user's access.

## 4. Goals

Users must be able to:

- understand the reporting period and scope;
- see counts and statuses backed by real records;
- identify incomplete or failed workloads;
- distinguish zero from missing or unavailable data;
- navigate from a supported summary to the related module without bypassing permissions.

## 5. User Workflow

```text
Open Statistics
  ↓
Load Authorized Statistics
  ├─ Success → Show Period, Summaries, and Supported Visuals
  ├─ Empty   → Explain No Data for Current Scope
  └─ Failure → Preserve Valid Sections and Offer Retry
```

If filters are supported later:

```text
Choose Approved Date Range / Scope
  ↓
Backend Validates Permission and Filter
  ↓
Refresh Statistics
```

## 6. Functional Requirements

### Summary

The page may display backend-provided metrics for:

- inspection records;
- photo reports;
- interview records;
- generated documents;
- AI task statuses;
- knowledge documents and indexing statuses.

The UI must not assume all metrics are always present.

### Time and Scope

- Every time-based value must show or inherit an explicit reporting period.
- The page must state whether data is personal, team, organization, or system scope when returned.
- The last-updated time should be shown when provided.
- Timezone handling must be consistent and documented by the backend.

### Trends and Distributions

- A chart may be used only when the API returns a valid series or category distribution.
- Labels, units, and interval boundaries must come from the contract.
- Missing intervals must not be silently converted to zero unless the backend defines them as zero.
- Tables or lists should be preferred when they communicate values more clearly.

### Drill-Down

- Summary links may navigate to existing filtered modules only when the target route and filter contract exist.
- The statistics page must not expose raw document content.

## 7. Business Rules

- All values must originate from backend data.
- Placeholder values must be visibly identified as design-only and must not ship as operational data.
- Zero, null, omitted, and unavailable are different states.
- Counts must be based on the backend's documented status and soft-deletion rules.
- A task failure count must not be presented as a business violation count.
- Generated-document counts must not be treated as unique business-record counts unless defined that way.
- Cross-organization comparisons require explicit permission and data-governance rules.
- AI-generated assessments must not be mixed with factual statistics without clear labeling and a separate specification.

## 8. UI Requirements

Recommended layout:

```text
Page Header and Reporting Context
  ↓
Summary Cards
  ↓
Status Distribution / Time Series when Supported
  ↓
Operational Detail Tables or Links
```

The UI must provide:

- skeletons during initial load;
- explicit reporting period and scope;
- readable metric labels and units;
- empty states for valid zero-data results;
- section-level errors for partial failure;
- accessible chart alternatives or data tables;
- status indicators that do not rely on color alone;
- responsive desktop and tablet layout.

Decorative animations and unsupported trend arrows must not be used.

## 9. API Requirements

Approved contract from `API.md`:

```text
GET /api/statistics
```

The response schema and query parameters are not yet defined. Before implementation, `API.md` and backend schemas must define:

- metric identifiers, labels, values, and units;
- reporting period and timezone;
- permission scope;
- optional time-series points;
- optional distributions;
- last-updated time;
- filters and allowed ranges;
- partial-result behavior.

The frontend must render the approved contract rather than hardcode response data.

## 10. Data Impact

Statistics should initially be derived from authorized existing tables:

- `inspection_records`;
- `photo_reports`;
- `interview_records`;
- `generated_documents`;
- `ai_tasks`;
- `knowledge_documents`;
- `knowledge_index_jobs`.

No separate statistics table is required until query performance, historical snapshots, or reporting policy justify it. Any materialized view, aggregation table, or warehouse must be documented in `DATABASE.md`.

## 11. AI Workflow

No AI inference is required for initial statistics.

Future narrative summaries, anomaly explanations, or recommendations must have a separate evidence and evaluation design. They must be labeled as AI-generated and must not alter the factual metrics.

## 12. Validation

- Counts must be non-negative integers unless a metric explicitly uses another type.
- Percentages must include a defined denominator and valid range.
- Dates and intervals must be ordered and parseable.
- Unknown metric types must not crash the page.
- Missing labels or units must result in an unavailable state.
- User-supplied date ranges must be validated by the backend.

## 13. Error Handling

- Backend unavailable: show a page-level error with retry.
- Partial response: render valid metrics and identify unavailable sections.
- Unauthorized scope: fall back only to a backend-approved narrower scope.
- Invalid metric: omit or mark the affected metric and report safe diagnostics.
- Stale data: show last-updated context when available.
- Empty period: show a valid no-data state, not an error.

## 14. Security and Privacy

- Statistics must be aggregated and scoped by backend authorization.
- Small-group or personally identifiable breakdowns require explicit privacy review.
- The frontend must not request raw sensitive documents to calculate counts.
- Export and drill-down must not bypass record-level permissions.
- Logs may record metric identifiers and request timing but not sensitive record content.

## 15. Non-Functional Requirements

- Expensive aggregation must not block normal business requests indefinitely.
- The backend should use appropriate indexes and bounded date ranges.
- Shared query caching should avoid duplicate requests.
- Charts and tables must remain readable with large values and empty series.
- Accessible data alternatives are required for visual charts.
- The page must degrade gracefully when one metric family fails.

## 16. Future Improvements

- approved filters and drill-downs;
- exportable statistical reports;
- scheduled snapshots;
- organization comparisons with governance controls;
- operational alerts;
- AI-generated narrative explanations with evidence and evaluation.

## 17. Acceptance Criteria

- [x] All displayed operational values come from `GET /api/statistics`.
- [x] Reporting period, scope, and units are clear.
- [x] Zero, missing, unavailable, and error states remain distinct.
- [x] Statistics respect backend authorization and soft-deletion rules.
- [x] Charts are used only for valid series and have accessible alternatives.
- [x] Partial failures do not hide unrelated valid metrics.
- [x] No invented trend, comparison, or placeholder value appears as real data.
- [x] The page works on desktop and tablet.
- [x] Available lint, type, test, and build checks pass.
