# app_a.py
import os
from dotenv import load_dotenv
from sync_node import create_node_app

load_dotenv()

app = create_node_app(
    node_name="MusicSync-A",
    port=int(os.getenv("PORT_A", "5001")),
    peer_url=os.getenv("PEER_B_URL", "http://127.0.0.1:5002"),
    db_url=os.getenv("DB_A_URL", "sqlite:///./music_a.db"),
    log_file=os.getenv("LOG_A_FILE", "musicsync_a.log"),
    api_token=os.getenv("API_TOKEN", "musicsync-secret-token-2026"),
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT_A", "5001")), debug=False)