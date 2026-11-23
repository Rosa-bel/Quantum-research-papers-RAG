# Quantum Papers RAG Frontend

The chat interface is a small React app in `frontend/`. It sends `{ "prompt": "..." }` to FastAPI's `/chat` endpoint and checks `/health` for backend status.

## Development

Start the API from the repository root:

```powershell
uvicorn fastAPI.main:app --reload --port 8000
```

In another terminal, start the React development server:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (usually `http://127.0.0.1:5173`). Vite proxies `/chat` and `/health` to FastAPI.

## Serve through FastAPI

To make the backend serve the production frontend at `http://127.0.0.1:8000`:

```powershell
cd frontend
npm install
npm run build
cd ..
uvicorn fastAPI.main:app --reload --port 8000
```

The build output goes to `frontend/dist`; FastAPI serves that output and its assets. Rebuild after changing the React app.
