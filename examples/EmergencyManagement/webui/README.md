# Emergency Management Web UI

This Vite + React + TypeScript project provides a lightweight web interface for
interacting with the Emergency Management FastAPI gateway. The application ships
with sidebar navigation, a mesh status placeholder, and centralised API client
configuration so the bundle can connect to different gateway instances.

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

| Variable             | Description                                                       |
| -------------------- | ----------------------------------------------------------------- |
| `VITE_API_BASE_URL`  | Base URL of the FastAPI gateway that proxies service operations. |

## Available scripts

```bash
npm run dev     # Start the development server
npm run build   # Build the production bundle
npm run preview # Preview the production build locally
npm run lint    # Run ESLint checks
```

## Project structure

- `src/router` wires up React Router for the dashboard, message, and event pages.
- `src/components/layout` contains the sidebar and mesh status top bar layout.
- `src/lib/apiClient.ts` exposes an Axios instance that normalises the gateway URL.
- `src/pages` contains feature placeholders that can be expanded with real data.
