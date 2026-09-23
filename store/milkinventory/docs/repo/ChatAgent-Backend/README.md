# ChatAgent Backend

This FastAPI backend receives user chat input and optional image uploads, uses Google AI Studio for OCR and task classification, then routes the extracted task payload to the existing MilkInventory backend.

## Requirements
- Python 3.11+
- `pip install -r requirements.txt`

## Environment
- `GOOGLE_AI_API_KEY` - required for Google AI Studio calls.
- `GOOGLE_AI_MODEL` - optional, default `models/text-bison-001`.
- `INVENTORY_BACKEND_URL` - optional, default `http://localhost:8000`.

## Run
```powershell
cd ChatAgent-Backend
python -m uvicorn main:app --reload --port 8001
```

## Endpoints
- `GET /api/health`
- `POST /api/chat/submit` - accepts `multipart/form-data` with `message` and optional `image`
