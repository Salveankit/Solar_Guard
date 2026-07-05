# SolarGuard React Frontend

React + TypeScript + Vite presentation layer for the SolarGuard POC.

## Architecture

```text
React + TypeScript + Vite
        -> HTTP/JSON
FastAPI
        -> backend services
        -> Neon/PostgreSQL
```

The frontend calls FastAPI only. It does not connect to PostgreSQL, read CSVs, import Python services, or recalculate anomaly, probable-cause, priority, financial-impact, or route logic.

## Configuration

Copy `.env.example` if local overrides are needed:

```env
VITE_SOLARGUARD_API_URL=http://localhost:8000
```

## Development

Backend:

```powershell
uv run uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Quality Commands

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
```

Only the Operations Command Centre route is fully implemented in this sprint. The remaining routes are professional placeholders and show no fake operational values.
