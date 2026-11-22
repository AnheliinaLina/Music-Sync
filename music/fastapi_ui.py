import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN", "musicsync-secret-token-2026")
NODE_A_URL = os.getenv("NODE_A_URL", "http://127.0.0.1:5001")
NODE_B_URL = os.getenv("NODE_B_URL", "http://127.0.0.1:5002")


class TrackPayload(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 101,
                "title": "Neon Horizon",
                "artist": "Synth Wave",
                "album": "Night Drive",
                "rating": 5,
            }
        }
    )

    id: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)
    artist: str = Field(..., min_length=1)
    album: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class TrackUpdatePayload(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Neon Horizon (Remastered)",
                "rating": 5,
            }
        }
    )

    title: Optional[str] = Field(default=None, min_length=1)
    artist: Optional[str] = Field(default=None, min_length=1)
    album: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)


def _auth_headers(
    x_api_key: Optional[str] = None,
    authorization: Optional[str] = None,
) -> Dict[str, str]:
    if authorization:
        auth_val = authorization.strip()
    elif x_api_key:
        raw = x_api_key.strip()
        auth_val = raw if raw.lower().startswith("bearer ") else f"Bearer {raw}"
    else:
        auth_val = f"Bearer {API_TOKEN}"

    return {
        "Authorization": auth_val,
        "x-api-key": x_api_key or API_TOKEN,
        "Content-Type": "application/json",
    }


def _forward_json(resp: requests.Response) -> Any:
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=data)
    return data


def _create_node_app(title: str, base_url: str, peer_url: str) -> FastAPI:
    node_app = FastAPI(title=title, version="0.1.0")
    src = base_url.rstrip("/")
    peer = peer_url.rstrip("/")

    @node_app.get("/tracks", summary="Get Tracks")
    def get_tracks(
        x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
        authorization: Optional[str] = Header(default=None),
    ):
        try:
            resp = requests.get(f"{src}/tracks", headers=_auth_headers(x_api_key, authorization), timeout=5)
            return _forward_json(resp)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Node unreachable: {exc}")

    @node_app.post("/tracks", summary="Add Track")
    def add_track(
        payload: TrackPayload,
        x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
        authorization: Optional[str] = Header(default=None),
    ):
        try:
            resp = requests.post(
                f"{src}/tracks",
                json=payload.model_dump(exclude_none=True),
                headers=_auth_headers(x_api_key, authorization),
                timeout=5,
            )
            return _forward_json(resp)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Node unreachable: {exc}")

    @node_app.post("/receive", summary="Receive Track")
    def receive_track(
        payload: TrackPayload,
        x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
        authorization: Optional[str] = Header(default=None),
    ):
        headers = _auth_headers(x_api_key, authorization)
        body = payload.model_dump(exclude_none=True)
        try:
            resp = requests.post(f"{src}/receive", json=body, headers=headers, timeout=5)
            if resp.status_code == 404:
                resp = requests.post(f"{src}/tracks", json=body, headers=headers, timeout=5)
            return _forward_json(resp)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Node unreachable: {exc}")

    @node_app.post("/sync", summary="Sync Tracks")
    def sync_tracks(
        x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
        authorization: Optional[str] = Header(default=None),
    ):
        headers = _auth_headers(x_api_key, authorization)
        try:
            sync_resp = requests.post(f"{src}/sync", headers=headers, timeout=5)
            if sync_resp.status_code != 404:
                return _forward_json(sync_resp)

            src_data = requests.get(f"{src}/tracks", headers=headers, timeout=5).json()
            tracks = src_data if isinstance(src_data, list) else src_data.get("tracks", [])
            synced = []
            for item in tracks:
                r = requests.post(f"{peer}/tracks", json=item, headers=headers, timeout=5)
                synced.append({"id": item.get("id"), "status": r.status_code})
            return {"status": "synced", "synced_items": synced}
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Node unreachable: {exc}")

    @node_app.put("/tracks/{track_id}", summary="Update Track")
    def update_track(
        track_id: int,
        payload: TrackUpdatePayload,
        x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
        authorization: Optional[str] = Header(default=None),
    ):
        try:
            resp = requests.put(
                f"{src}/tracks/{track_id}",
                json=payload.model_dump(exclude_none=True),
                headers=_auth_headers(x_api_key, authorization),
                timeout=5,
            )
            return _forward_json(resp)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Node unreachable: {exc}")

    return node_app


app = FastAPI(title="MusicSync FastAPI & UI", version="1.0.0")

node_a_app = _create_node_app("MusicSync A", NODE_A_URL, NODE_B_URL)
node_b_app = _create_node_app("MusicSync B", NODE_B_URL, NODE_A_URL)

app.mount("/node-a", node_a_app)
app.mount("/node-b", node_b_app)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    html_path = Path(__file__).with_name("index.html")
    return html_path.read_text(encoding="utf-8")


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "service": "fastapi-ui"}


def _register_grouped_routes(target_app: FastAPI, prefix: str, tag: str, base_url: str, peer_url: str) -> None:
    sub = _create_node_app(tag, base_url, peer_url)
    for route in sub.routes:
        if isinstance(route, APIRoute):
            target_app.add_api_route(
                f"{prefix}{route.path}",
                route.endpoint,
                methods=list(route.methods),
                summary=route.summary,
                tags=[tag],
            )


_register_grouped_routes(app, "/api/a", "Node A", NODE_A_URL, NODE_B_URL)
_register_grouped_routes(app, "/api/b", "Node B", NODE_B_URL, NODE_A_URL)