# ChatAgent Frontend

This React + Vite frontend sends chat messages and image uploads to the ChatAgent backend.

## Setup
```powershell
cd ChatAgent-Frontend
npm install
npm run dev
```

## Notes
- Frontend runs on `http://localhost:3001`
- It proxies `/api` requests to `http://localhost:8001`
- The backend expects the existing MilkInventory API to be available at `http://localhost:8000`
