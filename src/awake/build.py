"""Rebuild everything: SQLite DB, processed tables, figures, spreadsheet.   python -m awake.build"""
from __future__ import annotations

from . import analysis, db, figures


def main() -> None:
    db.build_db()
    res = analysis.run_all()
    ver = res["verification"]
    print(ver.to_string())
    if not ver.match.all():
        raise SystemExit("Total verification failed: report mismatch before continuing.")
    analysis.export_tables(res)
    for p in figures.make_all(res):
        print("figure:", p.name)
    from . import xlsx
    print("spreadsheet:", xlsx.build())
    print(res["headline"].to_string(index=False))


if __name__ == "__main__":
    main()
