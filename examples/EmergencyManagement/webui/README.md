# Emergency Management Web UI

This Vite + React + TypeScript project provides a lightweight web interface for
interacting with the Emergency Management FastAPI gateway. The application ships
with sidebar navigation, a mesh status placeholder, React Query data caching,
live update listeners, and centralised API client configuration so the bundle
can connect to different gateway instances.

## Getting started

```bash
npm install
npm run dev
```

The development server runs on [http://localhost:5173](http://localhost:5173) by
default.

## Environment configuration

The UI reads configuration from Vite environment variables. Copy
[`.env.example`](./.env.example) to `.env` and adjust the values for your
deployment target.

| Variable               | Description                                                                 |
| ---------------------- | --------------------------------------------------------------------------- |
| `VITE_API_BASE_URL`    | Base URL of the FastAPI gateway that proxies service operations.           |
| `VITE_UPDATES_URL`     | Optional SSE/WebSocket bridge used for live updates. Defaults to `/stream`. |
| `VITE_SERVER_IDENTITY` | Optional LXMF destination hash forwarded as `X-Server-Identity`.            |

## Available scripts

```bash
npm run dev     # Start the development server
npm run build   # Build the production bundle
npm run preview # Preview the production build locally
npm run lint    # Run ESLint checks
npm run test    # Execute Vitest component and integration suites
```

## Project structure

- `src/router` wires up React Router for the dashboard, message, and event pages.
- `src/components/layout` contains the sidebar and mesh status top bar layout.
- `src/components/toast` implements optimistic success and error toast notifications.
- `src/lib/apiClient.ts` exposes an Axios instance, typed helpers for emergency
  message/event endpoints, and utilities for the live update stream.
- `src/lib/liveUpdates.ts` provides a shared SSE event bus and hooks for React Query.
- `src/pages/EmergencyActionMessages` renders CRUD forms, tables, and toast-driven
  workflows for EAMs.
- `src/pages/Events` mirrors the message experience with event-specific inputs,
  geolocation helpers, and real-time updates.
