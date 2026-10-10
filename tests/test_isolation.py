"""The replica must never read BLACKBOX_* or call the original service (set would be worth 0)."""
from pathlib import Path

REPLICA = Path(__file__).resolve().parent.parent / "replica"
FORBIDDEN = ["BLACKBOX", "caja-negra", "railway.app", "urllib", "requests", "httpx", "socket", "http.client", "aiohttp"]


def test_replica_never_references_the_original():
    for path in REPLICA.rglob("*.py"):
        text = path.read_text()
        for word in FORBIDDEN:
            assert word not in text, f"{path.name} contains forbidden reference: {word}"
