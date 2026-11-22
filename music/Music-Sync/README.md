# Music-Sync
Music catalogue import and bidirectional synchronization system using Python, Flask, SQLAlchemy, PostgreSQL, and FastAPI.

## About the Project

MusicSync is an integration project that demonstrates how two applications can import, exchange, and synchronize music catalogue data through APIs, with conflict resolution, error handling, fault tolerance, and logging.

The project consists of two service nodes (`Node A` on port `5001` and `Node B` on port `5002`) connected to separate PostgreSQL databases (`music_a` and `music_b`), along with a FastAPI service (`:5003`) that serves a simple web interface (`index.html`) and interactive Swagger UI documentation (`/docs`).

## Features

- JSON catalogue import into PostgreSQL with data validation (`import_json.py`)
- Two independent service nodes (`app_a.py` and `app_b.py`) with separate PostgreSQL databases (`music_a`, `music_b`)
- REST API endpoints (`GET /tracks`, `POST /tracks`, `PUT /tracks/<id>`) for working with track data
- Bidirectional synchronization of track catalogues between applications
- Last-write-wins conflict resolution using versioning and timestamps
- Bearer token authentication (`401` on missing/invalid token), input/ID validation (`400`/`404`), network fault handling (`network_error`), and log files (`musicsync.log`, `musicsync_a.log`, `musicsync_b.log`)
- FastAPI integration layer with a simple web interface (`index.html`) and Swagger UI documentation (`/docs`)

## Technologies

- Python
- Flask
- SQLAlchemy
- FastAPI
- Uvicorn
- PostgreSQL
- psycopg
- Requests
- python-dotenv
- HTML / JavaScript

## Requirements

- Python 3
- PostgreSQL
- Git

## Setup

1. Clone the repository:
   git clone (https://github.com/YOUR_USERNAME/MusicSync.git) (https://github.com/YOUR_USERNAME/MusicSync.git)
   cd MusicSync
2. Create and activate a virtual environment (PowerShell example):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install the dependencies:
   ```
   pip install flask sqlalchemy requests python-dotenv "psycopg[binary]" fastapi uvicorn
   ```
4. Create a .env file in the project directory and configure your environment variables:
   ```
   API_TOKEN=musicsync-secret-token-2026
   PORT_A=5001
   PORT_B=5002
   PEER_A_URL=[http://127.0.0.1:5002](http://127.0.0.1:5002)
   PEER_B_URL=[http://127.0.0.1:5001](http://127.0.0.1:5001)
   DB_A_URL=postgresql+psycopg://postgres:your_database_password@localhost:5432/music_a
   DB_B_URL=postgresql+psycopg://postgres:your_database_password@localhost:5432/music_b
   LOG_A_FILE=musicsync_a.log
   LOG_B_FILE=musicsync_b.log
   NODE_A_URL=[http://127.0.0.1:5001](http://127.0.0.1:5001)
   NODE_B_URL=[http://127.0.0.1:5002](http://127.0.0.1:5002)
   ```
5. Create PostgreSQL databases named music_a and music_b and optionally import initial data:
   ```
   python import_json.py --file tracks.json --db "postgresql+psycopg://postgres:your_database_password@localhost:5432/music_a"
   python import_json.py --file tracks.json --db "postgresql+psycopg://postgres:your_database_password@localhost:5432/music_b"
   ```
## Running the Applications
Open separate terminals in the project directory.

**Terminal 1 — Application A (:5001)**
   ```
   python app_a.py
   ```
**Terminal 2 — Application B (:5002)**
   ```
   python app_b.py
   ```
**Terminal 3 — FastAPI & Web Interface (:5003)**
   ```
   uvicorn fastapi_ui:app --reload --port 5003
   ```
Open the following addresses in your browser:
   -Web interface: (http://127.0.0.1:5003/)
   -FastAPI API docs: (http://127.0.0.1:5003/docs)
   
## API & PowerShell Verification Examples
   Get tracks from Node A:
   ```
   curl.exe -H "Authorization: Bearer musicsync-secret-token-2026" [http://127.0.0.1:5001/tracks](http://127.0.0.1:5001/tracks)
   ```
   Create a new track (POST) in Node A:
   ```
   \$body = @{ id = 101; title = "New Track"; artist = "Artist Name"; album = "Album Name"; rating = 5 } | ConvertTo-Json; Invoke-RestMethod -Method Post -Uri "[http://127.0.0.1:5001/tracks](http://127.0.0.1:5001/tracks)" -Headers @{ Authorization = "Bearer musicsync-secret-token-2026" } -ContentType "application/json" -Body \$body
   ```
   Update a track (PUT) in Node B:
   ```
   \$body = @{ rating = 5 } | ConvertTo-Json; Invoke-RestMethod -Method Put -Uri "[http://127.0.0.1:5002/tracks/2](http://127.0.0.1:5002/tracks/2)" -Headers @{ Authorization = "Bearer musicsync-secret-token-2026" } -ContentType "application/json" -Body \$body
   ```
  ## Purpose
   This project was created as an educational assignment to demonstrate API integration, data exchange, bidirectional synchronization, conflict handling, error logging, and multi-service    integration.

   ## Authors
   ***Anhelina Poimanova, Olha Panchyshyna***
