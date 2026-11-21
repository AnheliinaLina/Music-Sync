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
   ```bash
   git clone (https://github.com/YOUR_USERNAME/MusicSync.git) (https://github.com/YOUR_USERNAME/MusicSync.git)
   cd MusicSync
2. Create and activate a virtual environment (PowerShell example):
   '''
   python -m venv .venv
.\.venv\Scripts\Activate.ps1
  '''
