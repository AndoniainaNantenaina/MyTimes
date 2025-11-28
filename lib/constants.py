# Store the SQLite DB file in the current user's home directory
# This works across Linux and Windows (Path.home() resolves appropriately).
from pathlib import Path

DB_PATH = str(Path.home() / ".mytimes" / "timesheets.db")
