# Settings

## 1. Purpose

The Settings feature gives users a safe place to view connection information and manage non-sensitive personal interface preferences. It must not become a client-side secret store or bypass environment-based deployment configuration.

## 2. Status and Scope

**Status:** Planned. No application code exists in the current repository, so implementation is not verified.

Current scope:

- display backend connection status;
- display the configured backend base URL in a safe diagnostic form;
- retry the health check;
- manage non-sensitive local user preferences;
- display application version information when available;
- explain which settings require an administrator or deployment change.

Out of scope for the first version:

- entering API keys;
- changing model-provider credentials;
- editing database or storage configuration;
- runtime modification of build-time environment variables;
- system-wide prompt or model management;
- user and role administration.

## 3. Users and Permissions

- **All authenticated users**: view connection state and manage their own non-sensitive preferences.
- **Administrator**: may see additional safe system metadata when a backend contract is approved.

The initial settings page must not expose privileged configuration merely because the current user has an administrator label in the frontend.

## 4. Goals

Users must be able to:

- determine whether the application can reach the backend;
- understand which backend environment the frontend targets;
- retry a failed connection check;
- change approved personal interface preferences;
- restore preferences to defaults;
- understand that secrets and infrastructure settings are managed outside the browser.

## 5. User Workflow

```text
Open Settings
  ↓
Load Local Preferences + Backend Health
  ├─ View Connection Information
  ├─ Change Personal Preferences → Save Locally or through Approved API
  └─ Restore Defaults
```

## 6. Functional Requirements

### Connection Information

- Display checking, connected, disconnected, and error states.
- Connection state must be based on `GET /health`.
- Display the configured API origin without query strings, credentials, or sensitive values.
- Provide a retry action.
- Do not allow ordinary users to rewrite `VITE_API_BASE_URL` at runtime.

### Personal Preferences

Initial preferences may include:

- light, dark, or system theme when supported by the existing UI;
- compact or comfortable density when supported consistently;
- reduced motion preference;
- default page-size preference when supported by lists.

Preferences must be non-sensitive. The implementation must reuse an existing preference system if one exists.

### Restore Defaults

- Restore must explain which values will change.
- It must not clear authentication or business data.
- It must not affect other users.

### System Information

- Show application version or build identifier only when supplied safely by the build or backend.
- Show model capability information only through an approved backend endpoint.
- Never infer a provider or model from frontend constants.

## 7. Business Rules

- Deployment configuration remains controlled by environment variables and secure backend configuration.
- `VITE_*` values are public frontend configuration and must never contain secrets.
- Personal preferences must not change business rules or backend authorization.
- A displayed connected state must come from a successful real health request.
- Missing system information must be shown as unavailable, not fabricated.
- Settings changes that affect the entire system require explicit backend contracts, authorization, audit behavior, and separate specifications.

## 8. UI Requirements

Recommended sections:

```text
Connection
Appearance and Accessibility
Application Information
Administrative Information (only when approved and authorized)
```

The UI must provide:

- clear section headings;
- current values and save state;
- accessible controls with visible labels;
- inline validation;
- save success and failure feedback;
- restore-default confirmation;
- status text that does not rely on color alone;
- clear explanation that secrets cannot be configured here.

The page must avoid displaying raw environment dumps or internal diagnostic payloads.

## 9. API Requirements

Approved contract:

```text
GET /health
```

No settings endpoint is currently approved in `API.md`.

Local non-sensitive preferences may be stored in the browser when they do not need cross-device synchronization. Before cross-device preferences or administrative settings are implemented, add explicit contracts to `API.md`, for example:

```text
GET /api/user/preferences
PUT /api/user/preferences
GET /api/system/capabilities
```

These paths are proposed only and are not part of the current API.

## 10. Data Impact

No new database table is required for initial local preferences.

If synchronized preferences are added, define a dedicated schema or an intentional profile field in `DATABASE.md` before implementation. Do not hide arbitrary settings in an undocumented JSON column.

System secrets remain in secure environment or secret-management configuration, not business tables.

## 11. AI Workflow

No AI inference is required.

The settings page must not call model providers directly, test prompts, expose prompts, or display provider credentials. Future model and prompt administration belongs to separate AI-platform specifications.

## 12. Validation

- Preference values must use an approved finite set.
- Unknown stored values must fall back safely to defaults.
- API origin display must be parsed safely and redact user information.
- Numeric preferences such as page size must remain within configured bounds.
- Local storage failures must not prevent the application from loading.

## 13. Error Handling

- Health failure: show disconnected or error status with retry.
- Preference save failure: preserve the current UI where safe and explain that it may not persist.
- Malformed stored preference: reset only the affected setting.
- Unsupported theme or feature: hide or disable it rather than presenting a non-working control.
- Unauthorized administrative metadata: omit the section and do not retry repeatedly.

## 14. Security and Privacy

- Never display or store API keys, passwords, access tokens, database URLs, storage secrets, or provider secrets.
- Do not expose complete environment variables.
- Local preferences must contain no sensitive business data.
- Backend system metadata must be filtered by authorization and safe-response schemas.
- Changing frontend visibility must not grant backend capabilities.

## 15. Non-Functional Requirements

- Preference changes should apply predictably and avoid page reload when practical.
- Settings must work by keyboard and screen reader.
- Theme and density changes must preserve readable contrast and layout.
- Health checks should use shared query caching and avoid request storms.
- The page must work when the backend is unavailable.

## 16. Future Improvements

- synchronized user preferences;
- administrator-managed safe feature flags;
- capability and version diagnostics;
- notification preferences;
- locale selection;
- separate model, prompt, and provider administration modules.

## 17. Acceptance Criteria

- [ ] Connection status is based on `GET /health` and can be retried.
- [ ] The displayed API origin contains no credentials or secret values.
- [ ] Ordinary users cannot change deployment configuration or secrets in the browser.
- [ ] Supported non-sensitive preferences can be changed and restored.
- [ ] Invalid stored preferences fall back safely.
- [ ] Missing system information is shown as unavailable, not invented.
- [ ] The settings page remains usable when the backend is unavailable.
- [ ] Controls are keyboard accessible and status does not rely on color alone.
- [ ] Available lint, type, test, and build checks pass.
