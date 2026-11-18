# Phase 5 — User Experience Implementation Plan

**Date:** 2026-11-18  
**Phase:** Phase 5 — User Experience  
**Branch:** `feat/phase-5-user-experience`  
**Reference Docs:** `docs/SRS.md` (`FR-DSH-01..08`, `FR-NOT-01..08`, `FR-SET-*`), `docs/API_SPECIFICATION.md` (Sections 3, 14), `docs/DATABASE.md` (Sections 2.1, 2.10), `docs/ROADMAP.md` (Phase 5).

---

## 1. Architecture & File Structure

### Milestone 5.1: Customizable Dashboard (`FR-DSH-01..08`)
- `backend/apps/workspaces/dashboard_registry.py`: Canonical registry of dashboard widgets, default order, and metadata.
- `backend/apps/workspaces/services/dashboard.py`: Assembly service aggregating enabled widgets into a single optimized payload.
- `backend/apps/workspaces/api/serializers.py`: Serializers for dashboard payload, layout representation, and layout update.
- `backend/apps/workspaces/api/dashboard_views.py`: `DashboardView`, `DashboardLayoutView`, `DashboardLayoutResetView`.
- `backend/apps/workspaces/api/urls.py`: URL routing for dashboard and workspace endpoints.
- `backend/tests/integration/workspaces/test_dashboard.py`: Integration tests for dashboard assembly, layout customization, and empty states.
- `frontend/src/features/dashboard/api/dashboard-api.ts`: Client API methods for dashboard and layout.
- `frontend/src/features/dashboard/components/dashboard-layout-dialog.tsx`: Accessible modal with reorder buttons and visibility toggles.
- `frontend/src/features/dashboard/pages/dashboard-page.tsx`: Main dashboard page rendering enabled widgets in order.
- `frontend/src/features/dashboard/pages/dashboard-page.test.tsx`: Vitest tests for dashboard rendering, widgets, and layout customize dialog.

### Milestone 5.2: Notification Center & Reminders (`FR-NOT-01..08`)
- `backend/apps/notifications/models.py`: `Notification`, `NotificationPreference`, `NotificationDelivery`.
- `backend/apps/notifications/services/notifications.py`: Notification creation, mark read, unread count, preference lookup.
- `backend/apps/notifications/services/evaluators.py`: Budget threshold evaluator (80%, 100%), recurring obligation bill reminders, savings milestones.
- `backend/apps/notifications/api/serializers.py`: Serializers for notifications and preferences.
- `backend/apps/notifications/api/views.py`: `NotificationListView`, `NotificationReadView`, `NotificationReadAllView`, `NotificationPreferenceView`, `NotificationUnreadCountView`.
- `backend/apps/notifications/api/urls.py`: Routing for `/api/v1/notifications/` and `/api/v1/notification-preferences/`.
- `backend/tests/integration/notifications/test_notifications.py`: Integration tests for models, evaluators, deduplication, and locked security preferences.
- `backend/tests/integration/notifications/test_notifications_api.py`: API tests for notifications and preferences.
- `frontend/src/features/notifications/api/notifications-api.ts`: Client API methods.
- `frontend/src/features/notifications/components/notification-bell.tsx`: Header bell icon with unread count badge.
- `frontend/src/features/notifications/components/notification-drawer.tsx`: Drawer for viewing and managing in-app notifications.
- `frontend/src/features/notifications/components/notification-bell.test.tsx`: Vitest tests for bell badge and drawer interactions.

### Milestone 5.3: Settings, Theme Toggle & Accessibility Polish (`FR-SET-*`, WCAG 2.2 AA)
- `backend/apps/workspaces/api/settings_views.py`: `MeView`, `WorkspaceView`, `WorkspaceSummaryView`.
- `backend/tests/integration/workspaces/test_settings.py`: Integration tests for profile and workspace settings updates.
- `frontend/src/features/settings/api/settings-api.ts`: Client API methods for `me`, `workspace`, and `workspace/summary`.
- `frontend/src/features/settings/pages/settings-page.tsx`: Profile, workspace, and notification preferences page.
- `frontend/src/components/theme-toggle.tsx`: Light/dark/system theme selector with token audit.
- `frontend/src/app/authenticated-layout.tsx`: Navigation header updated with dashboard link, notification bell, theme toggle, and settings link.

### Milestone 5.4: Verification, Hardening & Phase 5 Report
- `backend/tests/performance/test_phase5_queries.py`: Query count budget tests for dashboard assembly and notifications.
- `docs/openapi.yaml`: Regenerated OpenAPI 3.1 specification.
- `docs/PHASE_5_REPORT.md`: Comprehensive verification report.
- `docs/CHANGELOG.md` and `docs/ROADMAP.md`: Status updates.

---

## 2. Step-by-Step Implementation Tasks

### Task 1: Dashboard Registry & Assembly Service (Backend)
1. Write failing integration tests in `backend/tests/integration/workspaces/test_dashboard.py` testing `assemble_dashboard`, default layout, layout modification, and reset.
2. Implement `backend/apps/workspaces/dashboard_registry.py` with the 9 canonical widgets.
3. Implement `backend/apps/workspaces/services/dashboard.py` gathering balances, net worth, safe-to-spend, daily allowance, budget health, recent transactions, and category spending.
4. Run pytest to verify domain tests pass.

### Task 2: Dashboard REST API Endpoints (Backend)
1. Write API integration tests in `backend/tests/integration/workspaces/test_dashboard_api.py`.
2. Implement serializers in `backend/apps/workspaces/api/serializers.py`.
3. Implement views in `backend/apps/workspaces/api/dashboard_views.py` (`GET /api/v1/dashboard/`, `GET /api/v1/dashboard/layout/`, `PUT /api/v1/dashboard/layout/`, `POST /api/v1/dashboard/layout/reset/`).
4. Wire URLs in `backend/apps/workspaces/api/urls.py` and register in `backend/config/urls.py`.
5. Run pytest to verify API tests pass.
6. Commit: `feat(dashboard): implement dashboard assembly service and layout API`.

### Task 3: Dashboard Frontend View & Layout Dialog (Frontend)
1. Implement `frontend/src/features/dashboard/api/dashboard-api.ts`.
2. Build `frontend/src/features/dashboard/components/dashboard-layout-dialog.tsx` with accessible up/down buttons and visibility toggles.
3. Build `frontend/src/features/dashboard/pages/dashboard-page.tsx` rendering active widgets in specified order.
4. Update `frontend/src/app/router.tsx` to mount `/app/dashboard` and redirect `/app` to `/app/dashboard`.
5. Write Vitest tests in `frontend/src/features/dashboard/pages/dashboard-page.test.tsx`.
6. Run `npm test` and verify all tests pass.
7. Commit: `feat(dashboard): add customizable dashboard view and layout sheet`.

### Task 4: Notifications Models & Migrations (Backend)
1. Define `Notification`, `NotificationPreference`, and `NotificationDelivery` in `backend/apps/notifications/models.py`.
2. Register `apps.notifications` in `backend/config/settings/base.py`.
3. Generate migration `backend/manage.py makemigrations notifications` and apply `migrate`.
4. Write model unit tests in `backend/tests/integration/notifications/test_notifications.py` verifying unique constraints, deduplication key, and locked security preferences.
5. Commit: `feat(notifications): add notification and preference models and migrations`.

### Task 5: Notification Evaluation Services & API (Backend)
1. Implement `evaluators.py` with budget threshold scans (80%, 100%), upcoming bill alerts, and savings milestones.
2. Implement `notifications.py` service with mark-read, mark-all-read, and unread-count.
3. Implement serializers and views in `backend/apps/notifications/api/`.
4. Register URLs `/api/v1/notifications/` and `/api/v1/notification-preferences/`.
5. Write API integration tests in `backend/tests/integration/notifications/test_notifications_api.py`.
6. Run pytest and verify all tests pass.
7. Commit: `feat(notifications): implement notification evaluation services and REST API`.

### Task 6: Notification Bell & Drawer (Frontend)
1. Implement `frontend/src/features/notifications/api/notifications-api.ts`.
2. Build `frontend/src/features/notifications/components/notification-bell.tsx` with unread badge.
3. Build `frontend/src/features/notifications/components/notification-drawer.tsx` with filter, mark read, and clear actions.
4. Mount `NotificationBell` in `frontend/src/app/authenticated-layout.tsx` header.
5. Write Vitest tests in `frontend/src/features/notifications/components/notification-bell.test.tsx`.
6. Run `npm test` and verify tests pass.
7. Commit: `feat(notifications): add notification bell and drawer in frontend header`.

### Task 7: Settings Endpoints & Views (Backend & Frontend)
1. Implement `settings_views.py` in `backend/apps/workspaces/api/` (`/api/v1/me/`, `/api/v1/workspace/`, `/api/v1/workspace/summary/`).
2. Write integration tests in `backend/tests/integration/workspaces/test_settings.py`.
3. Implement `frontend/src/features/settings/pages/settings-page.tsx` with Profile, Workspace, and Notification Preferences tabs.
4. Add `/app/settings` route to `frontend/src/app/router.tsx` and header navigation link.
5. Add `frontend/src/components/theme-toggle.tsx` supporting light, dark, and system themes.
6. Commit: `feat(settings): add profile, workspace settings, and theme toggle`.

### Task 8: Verification, Hardening & Phase 5 Report
1. Write query count budget tests in `backend/tests/performance/test_phase5_queries.py`.
2. Run ledger drift audit: `python manage.py check_ledger --fail-on-drift` (confirm 0 drift).
3. Regenerate and validate OpenAPI 3.1 specification (`docs/openapi.yaml`).
4. Run full test suites: Pytest and Vitest.
5. Run code quality checks: Ruff, Mypy, and Vite production build.
6. Create `docs/PHASE_5_REPORT.md` and update `docs/CHANGELOG.md` and `docs/ROADMAP.md`.
7. Commit: `docs(phase5): add OpenAPI 3.1 specification, Phase 5 report, changelog, and roadmap update`.
