from functools import wraps
import logging
import os
import sys
from flask import Flask, jsonify, request
import requests
from sqlalchemy.exc import SQLAlchemyError

from database import Track, get_session_factory, utc_now_iso


def create_node_app(
    node_name: str,
    port: int,
    peer_url: str,
    db_url: str,
    log_file: str,
    api_token: str,
) -> Flask:
    app = Flask(node_name)

    logger = logging.getLogger(node_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s [" + node_name + "] [%(levelname)s] %(message)s")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    SessionLocal = get_session_factory(db_url)

    def require_bearer_token(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            expected = f"Bearer {api_token}"
            if auth_header != expected:
                logger.warning("Відхилено запит до %s: невалідний або відсутній Bearer токен.", request.path)
                return jsonify({"error": "Unauthorized: invalid or missing Bearer token"}), 401
            return fn(*args, **kwargs)
        return wrapper

    def push_to_peer(track_dict: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(
                f"{peer_url}/internal/sync-track",
                json=track_dict,
                headers=headers,
                timeout=4,
            )
            if resp.status_code in (200, 201):
                logger.info("Синхронізовано трек id=%s з peer (%s) -> HTTP %s", track_dict["id"], peer_url, resp.status_code)
                return {"status": "synced", "peer_status": resp.status_code, "peer_body": resp.json()}
            logger.warning("Peer (%s) повернув статус %s при синхронізації id=%s", peer_url, resp.status_code, track_dict["id"])
            return {"status": "peer_rejected", "peer_status": resp.status_code, "peer_body": resp.text}
        except requests.RequestException as exc:
            logger.error("Помилка мережі при зверненні до peer (%s): %s", peer_url, exc)
            return {"status": "network_error", "error": str(exc)}

    @app.get("/health")
    def health():
        return jsonify({"node": node_name, "port": port, "status": "ok"})

    @app.get("/tracks")
    @require_bearer_token
    def list_tracks():
        try:
            with SessionLocal() as session:
                tracks = session.query(Track).order_by(Track.id.asc()).all()
                return jsonify([t.to_dict() for t in tracks])
        except SQLAlchemyError as exc:
            logger.error("Помилка БД при читанні треків: %s", exc)
            return jsonify({"error": "Database error"}), 500

    @app.post("/tracks")
    @require_bearer_token
    def create_or_update_track():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body"}), 400

        try:
            track_id = int(payload["id"])
            title = str(payload["title"]).strip()
            artist = str(payload["artist"]).strip()
            album = str(payload.get("album", "Single")).strip() or "Single"
            duration_sec = int(payload.get("duration_sec", 180))
            rating = int(payload.get("rating", 3))
            if not title or not artist or not (1 <= rating <= 5) or duration_sec <= 0:
                raise ValueError("Invalid field values")
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Помилка валідації вхідних даних: %s", exc)
            return jsonify({"error": f"Validation error: {exc}"}), 400

        now_iso = utc_now_iso()
        try:
            with SessionLocal() as session:
                track = session.get(Track, track_id)
                if track is None:
                    track = Track(
                        id=track_id,
                        title=title,
                        artist=artist,
                        album=album,
                        duration_sec=duration_sec,
                        rating=rating,
                        version=1,
                        updated_at=now_iso,
                    )
                    session.add(track)
                    logger.info("Створено трек id=%s ('%s') у %s", track_id, title, node_name)
                else:
                    track.title = title
                    track.artist = artist
                    track.album = album
                    track.duration_sec = duration_sec
                    track.rating = rating
                    track.version = (track.version or 1) + 1
                    track.updated_at = now_iso
                    logger.info("Оновлено трек id=%s до v%s у %s", track_id, track.version, node_name)

                session.commit()
                track_dict = track.to_dict()
        except SQLAlchemyError as exc:
            logger.error("Помилка БД при збереженні треку: %s", exc)
            return jsonify({"error": "Database error"}), 500

        sync_result = push_to_peer(track_dict)
        return jsonify({"track": track_dict, "sync": sync_result}), 200

    @app.put("/tracks/<int:track_id>")
    @require_bearer_token
    def update_track(track_id: int):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body"}), 400

        try:
            with SessionLocal() as session:
                track = session.get(Track, track_id)
                if track is None:
                    return jsonify({"error": f"Track {track_id} not found"}), 404

                if "title" in payload:
                    title = str(payload["title"]).strip()
                    if not title:
                        return jsonify({"error": "title cannot be empty"}), 400
                    track.title = title
                if "artist" in payload:
                    artist = str(payload["artist"]).strip()
                    if not artist:
                        return jsonify({"error": "artist cannot be empty"}), 400
                    track.artist = artist
                if "album" in payload:
                    track.album = str(payload["album"]).strip() or "Single"
                if "duration_sec" in payload:
                    dur = int(payload["duration_sec"])
                    if dur <= 0:
                        return jsonify({"error": "duration_sec must be > 0"}), 400
                    track.duration_sec = dur
                if "rating" in payload:
                    rating = int(payload["rating"])
                    if not (1 <= rating <= 5):
                        return jsonify({"error": "rating must be between 1 and 5"}), 400
                    track.rating = rating

                track.version = (track.version or 1) + 1
                track.updated_at = utc_now_iso()
                session.commit()
                track_dict = track.to_dict()
                logger.info("Локальне оновлення треку id=%s (v%s) у %s", track_id, track.version, node_name)
        except (ValueError, TypeError) as exc:
            return jsonify({"error": f"Invalid field value: {exc}"}), 400
        except SQLAlchemyError as exc:
            logger.error("Помилка БД при оновленні треку: %s", exc)
            return jsonify({"error": "Database error"}), 500

        sync_result = push_to_peer(track_dict)
        return jsonify({"track": track_dict, "sync": sync_result}), 200

    @app.post("/internal/sync-track")
    @require_bearer_token
    def receive_peer_sync():
        incoming = request.get_json(silent=True)
        if not isinstance(incoming, dict) or "id" not in incoming:
            return jsonify({"error": "Invalid sync payload"}), 400

        try:
            track_id = int(incoming["id"])
            incoming_version = int(incoming.get("version", 1))
            incoming_updated = str(incoming.get("updated_at") or utc_now_iso())

            with SessionLocal() as session:
                local = session.get(Track, track_id)
                if local is None:
                    session.add(
                        Track(
                            id=track_id,
                            title=str(incoming["title"]),
                            artist=str(incoming["artist"]),
                            album=str(incoming.get("album", "Single")),
                            duration_sec=int(incoming.get("duration_sec", 180)),
                            rating=int(incoming.get("rating", 3)),
                            version=incoming_version,
                            updated_at=incoming_updated,
                        )
                    )
                    session.commit()
                    logger.info("Отримано та створено трек id=%s (v%s) від peer", track_id, incoming_version)
                    return jsonify({"status": "created", "id": track_id}), 201

                # Детекція конфлікту: якщо локальна версія новіша або час оновлення пізніший
                if (local.version or 1) > incoming_version or (
                    (local.version or 1) == incoming_version and local.updated_at > incoming_updated
                ):
                    logger.warning(
                        "КОНФЛІКТ при синхронізації id=%s: локальна v%s (%s) новіша за вхідну v%s (%s). Збережено локальну версію.",
                        track_id,
                        local.version,
                        local.updated_at,
                        incoming_version,
                        incoming_updated,
                    )
                    return jsonify({"status": "conflict_kept_local", "local_track": local.to_dict()}), 200

                local.title = str(incoming["title"])
                local.artist = str(incoming["artist"])
                local.album = str(incoming.get("album", "Single"))
                local.duration_sec = int(incoming.get("duration_sec", 180))
                local.rating = int(incoming.get("rating", 3))
                local.version = incoming_version
                local.updated_at = incoming_updated
                session.commit()
                logger.info("Застосовано синхронізацію треку id=%s (v%s) від peer", track_id, incoming_version)
                return jsonify({"status": "updated", "track": local.to_dict()}), 200
        except (KeyError, ValueError, TypeError) as exc:
            logger.error("Некоректні дані під час синхронізації: %s", exc)
            return jsonify({"error": f"Bad payload: {exc}"}), 400
        except SQLAlchemyError as exc:
            logger.error("Помилка БД під час прийому синхронізації: %s", exc)
            return jsonify({"error": "Database error"}), 500

    return app