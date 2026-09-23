# Hello World FastAPI

A minimal FastAPI REST API with Swagger UI integration.

## Run Locally

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Start the server:

   ```powershell
   uvicorn main:app --reload
   ```

4. Open Swagger UI:

   ```text
   http://127.0.0.1:8000/docs
   ```

## Endpoints

- `GET /` - Health check
- `GET /hello` - Returns a hello world message
