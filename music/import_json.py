import argparse
import json
import logging
import os
import sys
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

from database import Track, get_session_factory, utc_now_iso

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("musicsync.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("MusicSyncImport")

REQUIRED_FIELDS = {"id", "title", "artist"}


def validate_track(raw: dict, index: int) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"Елемент #{index} у JSON не є об'єктом.")

    missing = REQUIRED_FIELDS - set(raw.keys())
    if missing:
        raise ValueError(f"Елемент #{index} не містить обов'язкових полів: {sorted(missing)}")

    track_id = int(raw["id"])
    title = str(raw["title"]).strip()
    artist = str(raw["artist"]).strip()
    album = str(raw.get("album", "Single")).strip() or "Single"
    duration_sec = int(raw.get("duration_sec", 180))
    rating = int(raw.get("rating", 3))
    version = int(raw.get("version", 1))
    updated_at = str(raw.get("updated_at") or utc_now_iso())

    if not title or not artist:
        raise ValueError(f"Порожні поля title або artist у треку id={track_id}.")
    if duration_sec <= 0:
        raise ValueError(f"Некоректна тривалість треку id={track_id}: {duration_sec}")
    if not (1 <= rating <= 5):
        raise ValueError(f"Оцінка треку id={track_id} має бути в межах 1..5: {rating}")

    return {
        "id": track_id,
        "title": title,
        "artist": artist,
        "album": album,
        "duration_sec": duration_sec,
        "rating": rating,
        "version": max(1, version),
        "updated_at": updated_at,
    }


def import_tracks(json_path: str, db_url: str | None = None) -> int:
    logger.info("Початок імпорту треків з файлу: %s", json_path)

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Файл не знайдено: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Кореневий елемент JSON повинен бути масивом треків.")

    SessionLocal = get_session_factory(db_url)
    imported_count = 0

    try:
        with SessionLocal() as session:
            for idx, item in enumerate(data):
                payload = validate_track(item, idx)
                existing = session.get(Track, payload["id"])
                if existing is None:
                    session.add(Track(**payload))
                    logger.info("Додано новий трек id=%s ('%s' — %s)", payload["id"], payload["title"], payload["artist"])
                else:
                    for key, val in payload.items():
                        setattr(existing, key, val)
                    logger.info("Оновлено існуючий трек id=%s ('%s')", payload["id"], payload["title"])
                imported_count += 1
            session.commit()
    except SQLAlchemyError as exc:
        logger.error("Помилка бази даних під час імпорту: %s", exc)
        raise

    logger.info("Імпорт завершено успішно. Оброблено треків: %d", imported_count)
    return imported_count


def main():
    parser = argparse.ArgumentParser(description="Односторонній імпорт музичних треків з JSON у БД.")
    parser.add_argument("--file", default="tracks.json", help="Шлях до JSON-файлу з треками")
    parser.add_argument("--db", default=None, help="URL бази даних (перевизначає DATABASE_URL)")
    args = parser.parse_args()

    try:
        import_tracks(args.file, args.db)
    except (FileNotFoundError, json.JSONDecodeError, ValueError, SQLAlchemyError) as exc:
        logger.error("Імпорт перервано через помилку: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()