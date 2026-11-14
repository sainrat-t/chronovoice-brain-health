"""Put the database back in the state of the demo: the three personas only.

Run from backend/ (the database is CHRONOVOICE_DB, by default data/chronovoice.sqlite3):

    uv run --env-file .env python -m scripts.reset_demo
"""

from __future__ import annotations

from app.demo import reset_demo
from app.main import config_from_env
from app.store import Store


def main() -> None:
    config = config_from_env()
    store = Store(config.db_path)
    reset_demo(store)
    print(f"Demo database reset: {config.db_path}")


if __name__ == "__main__":
    main()
