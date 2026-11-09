from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "awake.db"
SQL = ROOT / "sql"
QUERIES = SQL / "queries"
CONFIG = ROOT / "config" / "assumptions.yaml"
FIGURES = ROOT / "docs" / "figures"
EXPORTS = ROOT / "exports"
