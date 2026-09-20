# Data Ingestion & Processing REST API - Backend

Backend for the Data Ingestion & Processing REST API project.

## Stack

- Python
- Flask
- SQL Server
- PyODBC
- Flask-CORS
- Swagger / Flasgger
- Gunicorn

## Database

SQL Server:
`DESKTOP-CIRBMT0\\MRSQL2025`

Database:
`DataIngestionDB`

Tables:

- `IngestionData`
- `ProcessedData`
- `ApiLogs`

## Run locally

From this backend folder:

```powershell
& "C:\Program Files\Python313\python.exe" -m pip install -r requirements.txt
& "C:\Program Files\Python313\python.exe" app.py
```

API:
`http://127.0.0.1:5000`

Swagger:
`http://127.0.0.1:5000/apidocs/`

## API key

Protected endpoints use:

Header:
`X-API-Key: demo-api-key`

For production, set `API_KEY` as an environment variable instead of relying on the fallback value.

## Main endpoints

- GET `/`
- GET `/api`
- GET `/api/health`
- POST `/api/ingest`
- GET `/api/data`
- POST `/api/batch-ingest`
- POST `/api/upload-csv`
- POST `/api/clean-file`
- GET `/api/download-cleaned/<filename>`
- POST `/api/process`
- GET `/api/processed-data`
- GET `/api/logs`

## Data flow

Frontend -> REST API -> Flask -> SQL Server

ETL:

IngestionData -> validation -> transformation -> ProcessedData
