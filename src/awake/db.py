"""Build the SQLite database from data/raw/*.csv and config/assumptions.yaml; run named queries."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from . import config
from .paths import DB_PATH, QUERIES, RAW, SQL

TABLE_FILES = {
    "events": "events.csv",
    "transactions": "transactions.csv",
    "orders": "orders.csv",
    "unit_costs": "unit_costs.csv",
    "ledger_budget": "ledger_budget.csv",
}


def build_db(path: Path = DB_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        con.executescript((SQL / "schema.sql").read_text(encoding="utf-8"))
        for table, fname in TABLE_FILES.items():
            df = pd.read_csv(RAW / fname, dtype={"order_id": str})
            df = df.astype(object).where(df.notna(), None)
            cols = ",".join(df.columns)
            marks = ",".join("?" * len(df.columns))
            con.executemany(f"INSERT INTO {table} ({cols}) VALUES ({marks})",
                            [tuple(r) for r in df.itertuples(index=False)])
        rows = [(k, v["value"], v["source"], v["confidence"], v["note"])
                for k, v in config.scalar_assumptions().items()]
        con.executemany("INSERT INTO assumptions VALUES (?,?,?,?,?)", rows)
        con.commit()
    finally:
        con.close()
    return path


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    if not Path(path).exists():
        build_db(path)
    return sqlite3.connect(path)


def run_query(name: str, con: sqlite3.Connection) -> pd.DataFrame:
    sql = (QUERIES / f"{name}.sql").read_text(encoding="utf-8")
    return pd.read_sql_query(sql, con)
