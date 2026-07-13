# Authentication

## 1. Purpose

Authentication identifies users before they access protected fire-inspection functions. The feature must provide a clear sign-in experience and establish an authenticated session that backend APIs can verify.

## 2. Status and Scope

**Status:** Planned. No application code exists in the current repository, so implementation is not verified.

Current scope:

- sign in with email and password;
- register a user when registration is enabled;
- load the current authenticated user;
- protect business pages and API requests;
- handle expired or invalid sessions;
- sign out locally by clearing the authenticated session.

Out of scope for the first version:

- social login;
- single sign-on;
- passwordless authentication;
- multi-factor authentication;
- organization invitations;
- password reset until an API contract is added.

## 3. Users and Permissions

- **Inspector**: accesses assigned inspection features.
- **Supervisor**: reviews inspection work according to backend permissions.
- **Administrator**: manages protected administrative functions.
- **Viewer**: has read-only access where permitted.

Authentication proves identity. Authorization decisions must still be enforced by the backend.

## 4. Goals

Users must be able to:

- sign in with valid credentials;
- understand why sign-in failed without seeing sensitive details;
- remain signed in according to the configured session policy;
- reach the originally requested page after successful sign-in;
- sign out and prevent further authenticated requests;
- see a clear session-expired message and sign in again.

## 5. User Workflow

```text
Open Protected Page
  ↓
Check Session
  ├─ Valid → Load Page
  └─ Missing / Expired
          ↓
       Sign In
          ↓
   Validate Credentials
          ├─ Success → Return to Requested Page
          └─ Failure → Show Recoverable Error
```

## 6. Functional Requirements

### Sign In

- The form must collect email and password.
- Submission must be disabled while the request is pending.
- Repeated clicks must not create duplicate requests.
- Successful sign-in must establish the session and load the current user.
- Failed sign-in must preserve the email field and clear or protect the password field.
- The application should return the user to the intended protected route.

### Registration

- Registration is available only when the backend enables it.
- The form must collect the minimum fields required by the approved API contract.
- The UI must not imply that registration succeeded before the backend confirms it.
- Role selection must not be client-controlled unless the backend explicitly authorizes it.

### Session Handling

- Protected API calls must include the bearer token through the centralized API client.
- The application must verify identity with the current-user endpoint.
- Invalid or expired credentials must clear the usable session and redirect to sign-in.
- Concurrent unauthorized responses should result in one coherent session-expired flow.

### Sign Out

- The first version may clear the local session because no logout endpoint is documented.
- A server-side revocation endpoint must be added to `API.md` before it is relied upon.

## 7. Business Rules

- The backend is the source of truth for account status, role, and permissions.
- An inactive or deleted user must not obtain a usable session.
- The frontend must never grant access based only on hidden navigation items.
- Users must not choose privileged roles during ordinary registration.
- Error messages must not reveal whether an unrelated email address exists when doing so would create an account-enumeration risk.

## 8. UI Requirements

The authentication interface must provide:

- email and password inputs with visible labels;
- show/hide password control;
- submit button with pending state;
- field-level validation;
- general error region announced to assistive technology;
- keyboard submission;
- link between sign-in and registration only when registration is enabled;
- professional, restrained styling consistent with the rest of the platform.

Required states:

- initial;
- validating;
- submitting;
- success redirect;
- invalid credentials;
- backend unavailable;
- session expired.

## 9. API Requirements

Approved contracts from `API.md`:

```text
POST /api/auth/login
POST /api/auth/register
GET  /api/auth/me
```

Login request:

```json
{
  "email": "user@example.com",
  "password": "user-provided-password"
}
```

Login response:

```json
{
  "access_token": "...",
  "refresh_token": "..."
}
```

The exact registration and current-user schemas must be added to `API.md` before implementation if they are not already represented in backend schemas.

Proposed future contracts:

```text
POST /api/auth/refresh
POST /api/auth/logout
POST /api/auth/password-reset
```

These proposed endpoints are not part of the current approved API.

## 10. Data Impact

Relevant target tables from `DATABASE.md`:

- `users` for account identity and role;
- `user_profiles` for non-authentication profile data;
- `audit_logs` for important authentication events.

Passwords must be managed by the selected identity provider or stored only as secure password hashes in an authentication system. Plaintext passwords must never be stored.

## 11. Validation

- Email is required and must use a valid normalized format.
- Password is required and must not be trimmed or transformed unexpectedly.
- Registration password policy must come from backend requirements.
- Client validation improves feedback but must be repeated by the backend.

## 12. Error Handling

- Invalid credentials: show a generic readable message.
- Inactive account: show an appropriate access message when safe.
- Backend unavailable: retain the form and offer retry.
- Rate limit: explain that the user should wait before retrying.
- Session expired: preserve the requested destination and require sign-in.
- Malformed response: reject the session and show a recoverable error.

## 13. Security and Privacy

- Never place passwords or tokens in logs, URLs, analytics, or error details.
- Do not hardcode tokens or authentication secrets.
- Prefer secure, HTTP-only cookies when the chosen backend architecture supports them; otherwise document token storage and XSS mitigations explicitly.
- Use HTTPS outside local development.
- Authorization must be checked on every protected backend operation.
- Authentication events should be auditable without recording secrets.

## 14. Non-Functional Requirements

- The sign-in form must be usable by keyboard and screen readers.
- A pending request must provide immediate feedback.
- Auth state initialization must avoid briefly displaying protected content.
- Redirect loops must be prevented.
- Authentication failures must not crash the application shell.

## 15. Future Improvements

- password reset;
- refresh-token rotation and server-side revocation;
- multi-factor authentication;
- enterprise single sign-on;
- organization invitations;
- device and session management.

## 16. Acceptance Criteria

- [ ] Valid credentials establish an authenticated session.
- [ ] Invalid credentials show a safe, readable error.
- [ ] Protected pages redirect unauthenticated users to sign-in.
- [ ] The originally requested route is restored after sign-in.
- [ ] `GET /api/auth/me` determines the authenticated user.
- [ ] Expired credentials produce one coherent re-authentication flow.
- [ ] Signing out prevents subsequent protected requests from using the old local session.
- [ ] Role and permission checks are enforced by the backend.
- [ ] No password or token is logged or committed.
- [ ] Loading, error, and keyboard-access states are verified.
- [ ] Available lint, type, test, and build checks pass.
