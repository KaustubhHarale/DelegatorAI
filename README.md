# DelegatorAI Frontend

React + Vite dashboard prototype for DelegatorAI.

## Run locally

1. Install Node.js 18+ (Node.js 20+ recommended).
2. Open this folder in VS Code terminal.
3. Install dependencies:

   ```bash
   npm install
   ```

4. Start the frontend:

   ```bash
   npm run dev
   ```

5. Open the local URL printed by Vite (usually `http://localhost:5173`).

## Backend connection

The frontend expects the following endpoints on the backend by default at `http://localhost:8000`:

- `GET /tasks`
- `POST /tasks`
- `PATCH /tasks/{id}`
- `GET /tasks/{id}/history` (declared in the API helper for later use)
- `POST /tasks/{id}/follow-up` (declared in the API helper for later use)

Set `VITE_API_BASE_URL` in a `.env` file to point at your backend, for example:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Copy `.env.example` to `.env` if you want a starting point.

## Important

- If the backend is not running or endpoints are not ready, the app remains usable with sample demo data.
- The demo UI does **not** send real Google Chat messages or call Groq directly.
- Keep Google Chat credentials and Groq API keys on the backend. Never place secrets in frontend code or `VITE_*` environment variables.
- API response shape may need small adjustments to match your existing backend schema. The adapter is in `src/App.jsx` (`normalizeTask`) and request helpers are in `src/api.js`.
