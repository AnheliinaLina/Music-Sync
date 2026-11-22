# app_b.py
import os
from dotenv import load_dotenv
from sync_node import create_node_app

load_dotenv()

app = create_node_app(
    node_name="MusicSync-B",
    port=int(os.getenv("PORT_B", "5002")),
    peer_url=os.getenv("PEER_A_URL", "http://127.0.0.1:5001"),
    db_url=os.getenv("DB_B_URL", "sqlite:///./music_b.db"),
    log_file=os.getenv("LOG_B_FILE", "musicsync_b.log"),
    api_token=os.getenv("API_TOKEN", "musicsync-secret-token-2026"),
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_B", "5002")), debug=False)