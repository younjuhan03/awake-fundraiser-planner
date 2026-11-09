"""Data-layer tests: raw totals, SQL queries, privacy, and config integrity."""
import re

import pandas as pd
import pytest

from awake import analysis as an, config, db
from awake.paths import RAW, ROOT


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    path = db.build_db(tmp_path_factory.mktemp("db") / "t.db")
    return db.connect(path)


def test_s26_orders_totals(con):
    o = db.run_query("orders_all", con)
    assert (len(o), o.quantity.sum(), o.amount_usd.sum()) == (29, 104, 375)


def test_event_totals(con):
    pnl = an.event_pnl(con).set_index("event_id")
    assert pnl.loc["F24", "cost_usd"] == pytest.approx(261.46)
    assert pnl.loc["F24", "net_usd"] == pytest.approx(234.54)
    assert pnl.loc["F24", "unplanned_usd"] == pytest.approx(75.0)
    assert pnl.loc["S25", "cost_usd"] == pytest.approx(190.00)
    assert pnl.loc["S25", "net_usd"] == pytest.approx(182.00)
    assert pnl.loc["S25", "units_purchased"] == 108


def test_all_verification_checks_match(con):
    assert an.verify_totals(con).match.all()


def test_f24_ledger_budget_agrees_with_transactions(con):
    b = db.run_query("budget_check", con).set_index("line")
    pnl = an.event_pnl(con).set_index("event_id")
    assert b.loc["Fundraiser Expense", "actual_usd"] == pytest.approx(pnl.loc["F24", "cost_usd"])
    assert b.loc["Fundraiser Income", "actual_usd"] == pytest.approx(pnl.loc["F24", "revenue_usd"])


def test_f24_memo_discrepancy_is_reported_not_hidden(con):
    r = an.f24_reconciliation(con)
    assert r["ledger_memo_net"] == 261.13 and r["computed_net"] == pytest.approx(234.54)
    assert r["unexplained_difference"] == pytest.approx(26.59)
    assert r["net_with_parking_fine"] == pytest.approx(159.54)


def test_cost_shares_sum_to_one(con):
    cs = an.cost_structure(con)
    assert cs.groupby("event_id").share.sum().round(9).eq(1).all()
    assert "unplanned" not in set(cs.category)


def test_unit_economics(con):
    ue = an.unit_economics(con)
    assert ue["s25_all_in_cost_per_item"] == pytest.approx(190 / 108)
    assert ue["s25_ingredients_per_item"] + ue["s25_supplies_per_item"] == pytest.approx(190 / 108)
    assert ue["s26_avg_price_per_item"] == pytest.approx(375 / 104)


def test_concentration(con):
    d = an.demand(con)
    assert d["largest_units_share"] == pytest.approx(28 / 104)
    assert d["largest_revenue_share"] == pytest.approx(100 / 375)
    c = d["concentration"].set_index("view")
    assert c.loc["without largest order", "units"] == 76
    assert c.loc["all orders", "hhi_units"] > c.loc["without largest order", "hhi_units"]
    for v in c.itertuples():
        assert v.equal_orders_hhi <= v.hhi_units <= 1


def test_hhi_known_values():
    assert an.hhi([1, 1, 1, 1]) == pytest.approx(0.25)
    assert an.hhi([5]) == 1.0


def test_timing(con):
    d = an.demand(con)
    assert d["day1_orders_share"] == pytest.approx(13 / 29)
    assert d["by_day"].n_orders.sum() == 29 and d["by_day"].units.sum() == 104
    assert d["by_hour"].n_orders.sum() == 29
    assert d["zero_order_days"] == ["2026-02-28", "2026-03-01"]


def test_price_schedule_matches_config_and_flags_anomalies(con):
    ps = an.price_schedule(con).set_index("quantity")
    cfg = config.price_schedule()
    assert dict(ps.modal_amount_usd.items()) == cfg
    assert "inconsistent" in ps.loc[4, "flag"] and "$15" in ps.loc[4, "flag"]
    assert ps.loc[1, "flag"]  # 1 -> $7 is flagged


def test_config_derived_values_match_data(con):
    a = config.values()
    ue = an.unit_economics(con)
    assert a["s25_all_in_unit_cost_usd"] == pytest.approx(ue["s25_all_in_cost_per_item"], abs=5e-5)
    assert a["unit_cost_usd"] == pytest.approx(ue["s25_all_in_cost_per_item"], abs=5e-5)
    assert a["preorder_avg_price_usd"] == pytest.approx(375 / 104, abs=5e-5)
    assert a["preorder_units"] == 104 and a["preorder_revenue_usd"] == 375


def test_config_entries_complete():
    raw = config.load_raw()
    for key, v in raw.items():
        for field in ("source", "confidence", "note"):
            assert v.get(field), f"{key} missing {field}"
        assert v["confidence"] in config.CONFIDENCE_LEVELS, key
        if key != "price_schedule":
            assert "value" in v, key


def test_s26_scenarios_use_at_least_three_sourced_cost_cases():
    cs = an.cost_scenarios()
    assert len(cs) >= 3 and cs.source.str.len().gt(0).all()
    sc = an.s26_scenarios()
    assert ((sc.net_pre_orders_only - (375 - 104 * sc.unit_cost_usd)).abs() < 1e-9).all()
    assert (sc.net_buffer_worst <= sc.net_buffer_expected).all()
    assert (sc.net_buffer_expected <= sc.net_buffer_best).all()


def test_database_has_required_tables(con):
    names = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert {"events", "transactions", "orders", "unit_costs", "assumptions"} <= names
    assert con.execute("select count(*) from assumptions").fetchone()[0] >= 10


# ------------------------------------------------------------------ privacy
def test_orders_have_no_personal_columns():
    cols = set(pd.read_csv(RAW / "orders.csv").columns)
    assert cols == {"order_id", "timestamp", "quantity", "amount_usd", "event_id"}


def test_no_phone_numbers_or_emails_in_repo_text():
    phone = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")
    email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    for f in ROOT.rglob("*"):
        if f.suffix.lower() in {".csv", ".md", ".yaml", ".yml", ".sql", ".py", ".txt"} and ".git" not in f.parts:
            text = f.read_text(encoding="utf-8", errors="ignore")
            assert not phone.search(text), f"phone-like string in {f}"
            assert not email.search(text), f"email-like string in {f}"
