"""Analyses. All inputs come from SQLite (via sql/queries/*.sql) and config/assumptions.yaml.

Tags used everywhere: observed (read from data), derived (calculated from observed data),
estimate / scenario (depends on an assumption; never a fact).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

import numpy as np
import pandas as pd

from . import config, planner
from .db import connect, run_query
from .paths import PROCESSED

TOL = 0.005


# ----------------------------------------------------------------------------- verification
EXPECTED = {
    "S26 orders": 29, "S26 units": 104, "S26 revenue": 375.0,
    "F24 costs": 261.46, "S25 costs": 190.00, "S25 units": 108,
    "F24 revenue": 496.0, "S25 revenue": 372.0,
}


def verify_totals(con: sqlite3.Connection) -> pd.DataFrame:
    pnl = run_query("event_pnl", con).set_index("event_id")
    orders = run_query("orders_all", con)
    actual = {
        "S26 orders": len(orders), "S26 units": int(orders.quantity.sum()),
        "S26 revenue": float(orders.amount_usd.sum()),
        "F24 costs": float(pnl.loc["F24", "cost_usd"]), "S25 costs": float(pnl.loc["S25", "cost_usd"]),
        "S25 units": int(pnl.loc["S25", "units_purchased"]),
        "F24 revenue": float(pnl.loc["F24", "revenue_usd"]), "S25 revenue": float(pnl.loc["S25", "revenue_usd"]),
    }
    df = pd.DataFrame({"expected": EXPECTED, "actual": actual})
    df["match"] = (df.expected - df.actual).abs() < TOL
    return df


# ----------------------------------------------------------------------------- 1. event P&L
def event_pnl(con) -> pd.DataFrame:
    df = run_query("event_pnl", con)
    df["net_usd"] = (df.revenue_usd - df.cost_usd).round(2)
    df["margin"] = np.where(df.revenue_usd > 0, df.net_usd / df.revenue_usd.replace(0, np.nan), np.nan)
    df["net_incl_unplanned_usd"] = (df.net_usd - df.unplanned_usd).round(2)
    df["tag"] = np.where(df.status == "observed", "observed (net = derived)", "no cost data")
    return df


def f24_reconciliation(con) -> dict:
    r = event_pnl(con).set_index("event_id").loc["F24"]
    computed = float(r.net_usd)
    memo = float(r.ledger_memo_net_usd)
    return {
        "revenue": float(r.revenue_usd), "fundraiser_expenses": float(r.cost_usd),
        "computed_net": computed, "ledger_memo_net": memo,
        "unexplained_difference": round(memo - computed, 2),
        "parking_fine": float(r.unplanned_usd),
        "net_with_parking_fine": round(computed - float(r.unplanned_usd), 2),
        "memo_net_vs_expenses_gap": round(memo - float(r.cost_usd), 2),
    }


# ----------------------------------------------------------------------------- 2. cost structure
def cost_structure(con) -> pd.DataFrame:
    """Share of planned fundraiser cost by category (parking fine excluded; shown separately)."""
    df = run_query("cost_structure", con)
    planned = df[df.category != "unplanned"].copy()
    planned["share"] = planned.cost_usd / planned.groupby("event_id").cost_usd.transform("sum")
    return planned


# ----------------------------------------------------------------------------- 3. unit economics
def cost_scenarios(a: dict | None = None) -> pd.DataFrame:
    """S26 cost-per-item scenarios. Each row has its source and confidence."""
    a = a or config.values()
    allow = a["supplies_allowance_per_item_usd"]
    rows = [
        ("A", "S25 all-in cost per item", a["s25_all_in_unit_cost_usd"], "assumed",
         "S25 $190.00 / 108 items purchased (ingredients + supplies, ramen menu); applying it to S26 is assumed"),
        ("B", "Memo low: ingredients + supplies allowance",
         a["memo_ingredient_cost_low_usd"] + allow, "assumed",
         "Memo Maxim coffee $0.39 + supplies allowance (allowance is an assumption)"),
        ("C", "Memo high: ingredients + supplies allowance",
         a["memo_ingredient_cost_high_usd"] + allow, "assumed",
         "Memo brookie $0.60 + supplies allowance (allowance is an assumption)"),
        ("D", "Conservative high-cost stress test",
         a["s25_all_in_unit_cost_usd"] * a["conservative_cost_multiplier"], "assumed",
         "S25 all-in x multiplier (multiplier is a judgment call)"),
    ]
    return pd.DataFrame(rows, columns=["scenario", "name", "unit_cost_usd", "confidence", "source"])


def unit_economics(con, a: dict | None = None) -> dict:
    a = a or config.values()
    tx = run_query("cost_structure", con)
    s25 = tx[tx.event_id == "S25"].set_index("category").cost_usd
    pnl = event_pnl(con).set_index("event_id")
    units = int(pnl.loc["S25", "units_purchased"])
    s25_cost = float(pnl.loc["S25", "cost_usd"])
    s25_rev = float(pnl.loc["S25", "revenue_usd"])
    orders = run_query("orders_all", con)
    avg_price = orders.amount_usd.sum() / orders.quantity.sum()
    cs = cost_scenarios(a)
    cs["contribution_per_item_at_avg_price"] = avg_price - cs.unit_cost_usd
    cs["contribution_per_item_at_pair_price"] = 3.50 - cs.unit_cost_usd
    cs["contribution_margin_pct"] = cs.contribution_per_item_at_avg_price / avg_price
    return {
        "s25_units_purchased": units,
        "s25_all_in_cost_per_item": s25_cost / units,
        "s25_ingredients_per_item": float(s25["ingredients"]) / units,
        "s25_supplies_per_item": float(s25["supplies"]) / units,
        "s25_revenue_per_item_purchased": s25_rev / units,
        "s25_net_per_item_purchased": (s25_rev - s25_cost) / units,
        "s26_avg_price_per_item": avg_price,
        "s26_cost_scenarios": cs,
        "buffer_breakeven_sellthrough": {
            r.scenario: r.unit_cost_usd / a["walkup_price_usd"] for r in cs.itertuples()},
    }


# ----------------------------------------------------------------------------- price schedule
def price_schedule(con) -> pd.DataFrame:
    """Observed S26 schedule: modal amount per quantity, plus flags. Intent is NOT inferred."""
    obs = run_query("price_schedule_observed", con)
    rows = []
    for q, g in obs.groupby("quantity"):
        modal = g.sort_values("n_orders", ascending=False).iloc[0]
        flag = ""
        if len(g) > 1:
            others = ", ".join(f"${r.amount_usd:.0f} x{r.n_orders}" for r in g.itertuples() if r.amount_usd != modal.amount_usd)
            flag = f"inconsistent: also seen {others}"
        elif q == 1:
            flag = "1 item costs the same as 2 (minimum order or bundle price? intent unknown)"
        elif q == 28:
            flag = "single order; $3.57/item vs $3.50/item for 2, 4, 6 items"
        elif q == 3:
            flag = "$3.67/item; not a multiple of $3.50"
        rows.append({"quantity": int(q), "modal_amount_usd": float(modal.amount_usd),
                     "n_orders": int(g.n_orders.sum()), "price_per_item_usd": round(modal.amount_usd / q, 4),
                     "flag": flag})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- 4. demand
def hhi(values) -> float:
    """Herfindahl index on shares, 0..1 (1/n = perfectly equal orders, 1 = one order)."""
    v = np.asarray(values, dtype=float)
    s = v / v.sum()
    return float((s ** 2).sum())


def concentration(orders: pd.DataFrame) -> pd.DataFrame:
    rows = []
    big = orders.loc[orders.quantity.idxmax()]
    for label, d in [("all orders", orders), ("without largest order", orders.drop(big.name))]:
        rows.append({
            "view": label, "n_orders": len(d), "units": int(d.quantity.sum()),
            "revenue_usd": float(d.amount_usd.sum()),
            "hhi_units": hhi(d.quantity), "hhi_revenue": hhi(d.amount_usd),
            "equal_orders_hhi": 1 / len(d),
            "mean_order_units": float(d.quantity.mean()), "median_order_units": float(d.quantity.median()),
            "avg_price_per_item_usd": float(d.amount_usd.sum() / d.quantity.sum()),
        })
    out = pd.DataFrame(rows)
    out["largest_order_id"] = big.order_id
    return out


def demand(con) -> dict:
    orders = run_query("orders_all", con)
    orders["ts"] = pd.to_datetime(orders.timestamp)
    total_units, total_rev = orders.quantity.sum(), orders.amount_usd.sum()
    big = orders.loc[orders.quantity.idxmax()]
    by_day = run_query("demand_by_day", con)
    all_days = pd.date_range(by_day.day.min(), by_day.day.max()).strftime("%Y-%m-%d")
    by_day = by_day.set_index("day").reindex(all_days, fill_value=0).rename_axis("day").reset_index()
    by_day["cum_orders"] = by_day.n_orders.cumsum()
    by_day["cum_units"] = by_day.units.cumsum()
    by_day["cum_orders_share"] = by_day.cum_orders / by_day.n_orders.sum()
    by_day["cum_units_share"] = by_day.cum_units / by_day.units.sum()
    by_hour = run_query("demand_by_hour", con).set_index("hour").reindex(range(24), fill_value=0).rename_axis("hour").reset_index()
    day1 = by_day.iloc[0]
    wave2 = by_day[by_day.day >= "2026-03-02"]
    timeline = orders[["order_id", "ts", "quantity"]].copy()
    timeline["cum_orders"] = np.arange(1, len(timeline) + 1)
    timeline["cum_units"] = timeline.quantity.cumsum()
    return {
        "orders": orders,
        "n_orders": len(orders), "units": int(total_units), "revenue_usd": float(total_rev),
        "size_distribution": run_query("order_size_distribution", con),
        "largest_order_id": big.order_id, "largest_order_units": int(big.quantity),
        "largest_units_share": float(big.quantity / total_units),
        "largest_revenue_share": float(big.amount_usd / total_rev),
        "concentration": concentration(orders),
        "by_day": by_day, "by_hour": by_hour, "timeline": timeline,
        "day1": str(day1.day), "day1_orders_share": float(day1.n_orders / len(orders)),
        "day1_units_share": float(day1.units / total_units),
        "wave2_orders": int(wave2.n_orders.sum()), "wave2_units": int(wave2.units.sum()),
        "wave2_orders_share": float(wave2.n_orders.sum() / len(orders)),
        "wave2_units_share": float(wave2.units.sum() / total_units),
        "zero_order_days": list(by_day[by_day.n_orders == 0].day),
    }


# ----------------------------------------------------------------------------- 5. S26 scenarios
def default_inputs(a: dict | None = None, **overrides) -> planner.PlannerInputs:
    a = a or config.values()
    kw = dict(preorder_units=int(a["preorder_units"]), preorder_revenue=a["preorder_revenue_usd"],
              walkup_buffer_pct=a["walkup_buffer_pct"], walkup_sellthrough_pct=a["walkup_sellthrough_pct"],
              walkup_price=a["walkup_price_usd"], unit_cost=a["unit_cost_usd"], fixed_costs=a["fixed_costs_usd"])
    kw.update(overrides)
    return planner.PlannerInputs(**kw)


def s26_scenarios(a: dict | None = None) -> pd.DataFrame:
    """S26 net profit ESTIMATES. Revenue = observed pre-order revenue (+ scenario walk-up revenue).
    Production is unknown: 'pre-orders only' cooks exactly 104 items; 'with buffer' adds the assumed buffer."""
    a = a or config.values()
    rows = []
    for c in cost_scenarios(a).itertuples():
        base = default_inputs(a, unit_cost=c.unit_cost_usd, fixed_costs=0.0)
        pre_only = planner.evaluate(planner.PlannerInputs(**{**asdict(base), "walkup_buffer_pct": 0.0}))
        sc = planner.scenarios(base)
        rows.append({
            "scenario": c.scenario, "name": c.name, "unit_cost_usd": c.unit_cost_usd,
            "cost_confidence": c.confidence,
            "cost_pre_orders_only": pre_only.total_cost, "net_pre_orders_only": pre_only.net,
            "margin_pre_orders_only": pre_only.margin,
            "production_with_buffer": sc["expected"].production_qty,
            "net_buffer_worst": sc["worst"].net, "net_buffer_expected": sc["expected"].net,
            "net_buffer_best": sc["best"].net,
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- 6. sensitivity
def sensitivity(a: dict | None = None) -> dict:
    a = a or config.values()
    units = int(a["preorder_units"])
    costs = np.round(np.arange(0.50, 3.01, 0.25), 2)
    prices = np.round(np.arange(2.50, 5.01, 0.50), 2)
    grid_cost_price = pd.DataFrame(
        [[units * (p - c) for p in prices] for c in costs], index=costs, columns=prices)
    grid_cost_price.index.name, grid_cost_price.columns.name = "unit_cost_usd", "avg_price_per_item_usd"

    buffers = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]
    sts = [0.0, 0.25, 0.50, 0.75, 1.0]
    grid_buf = pd.DataFrame(
        [[planner.evaluate(default_inputs(a, walkup_buffer_pct=b, walkup_sellthrough_pct=s)).net for s in sts]
         for b in buffers], index=buffers, columns=sts)
    grid_buf.index.name, grid_buf.columns.name = "walkup_buffer_pct", "walkup_sellthrough_pct"

    base = default_inputs(a)
    base_net = planner.evaluate(base).net
    swings = []

    def net_with(**kw):
        return planner.evaluate(default_inputs(a, **kw)).net

    for name, lo_kw, hi_kw, lo_lab, hi_lab in [
        ("unit cost (+/-20%)", dict(unit_cost=base.unit_cost * 1.2), dict(unit_cost=base.unit_cost * 0.8), "+20%", "-20%"),
        ("pre-order revenue (+/-20%)", dict(preorder_revenue=base.preorder_revenue * 0.8),
         dict(preorder_revenue=base.preorder_revenue * 1.2), "-20%", "+20%"),
        ("walk-up price (+/-20%)", dict(walkup_price=base.walkup_price * 0.8), dict(walkup_price=base.walkup_price * 1.2), "-20%", "+20%"),
        ("walk-up buffer (0% vs 20%)", dict(walkup_buffer_pct=0.20), dict(walkup_buffer_pct=0.0), "20%", "0%"),
        ("walk-up sell-through (0% vs 100%)", dict(walkup_sellthrough_pct=0.0), dict(walkup_sellthrough_pct=1.0), "0%", "100%"),
    ]:
        swings.append({"parameter": name, "adverse_case": lo_lab, "net_adverse": net_with(**lo_kw),
                       "favorable_case": hi_lab, "net_favorable": net_with(**hi_kw),
                       "swing": net_with(**hi_kw) - net_with(**lo_kw)})
    return {"cost_price": grid_cost_price, "buffer_sellthrough": grid_buf,
            "one_at_a_time": pd.DataFrame(swings).sort_values("swing", ascending=False, key=abs),
            "baseline_net": base_net}


# ----------------------------------------------------------------------------- headline numbers
def headline_numbers(con=None) -> pd.DataFrame:
    con = con or connect()
    a = config.values()
    pnl = event_pnl(con).set_index("event_id")
    rec = f24_reconciliation(con)
    ue = unit_economics(con, a)
    d = demand(con)
    sc = s26_scenarios(a)
    conc = d["concentration"].set_index("view")
    rows = [
        ("S26 pre-orders", "29 orders / 104 items / $375", "observed"),
        ("F24 revenue", f"${pnl.loc['F24','revenue_usd']:.2f}", "observed"),
        ("F24 fundraiser costs", f"${pnl.loc['F24','cost_usd']:.2f}", "observed"),
        ("F24 net (computed)", f"${rec['computed_net']:.2f}  ({pnl.loc['F24','margin']:.1%} margin)", "derived"),
        ("F24 net (ledger memo)", f"${rec['ledger_memo_net']:.2f}  (unresolved +${rec['unexplained_difference']:.2f})", "observed (memo)"),
        ("F24 net incl. parking fine", f"${rec['net_with_parking_fine']:.2f}", "derived"),
        ("S25 revenue / cost / net", f"$372.00 / $190.00 / $182.00  ({pnl.loc['S25','margin']:.1%} margin)", "observed / observed / derived"),
        ("S25 all-in cost per item purchased", f"${ue['s25_all_in_cost_per_item']:.2f}", "derived"),
        ("S25 revenue per item purchased", f"${ue['s25_revenue_per_item_purchased']:.2f}", "derived"),
        ("S26 avg price per item (pre-orders)", f"${ue['s26_avg_price_per_item']:.2f}", "derived"),
        ("Largest S26 order share (units / revenue)", f"{d['largest_units_share']:.1%} / {d['largest_revenue_share']:.1%}", "derived"),
        ("S26 HHI units (all / without largest)", f"{conc.loc['all orders','hhi_units']:.3f} / {conc.loc['without largest order','hhi_units']:.3f}", "derived"),
        ("S26 orders placed on day 1 (Feb 26)", f"{d['day1_orders_share']:.1%} of orders, {d['day1_units_share']:.1%} of items", "derived"),
        ("S26 orders on Mar 2-3", f"{d['wave2_orders']} orders ({d['wave2_orders_share']:.1%}), {d['wave2_units']} items ({d['wave2_units_share']:.1%})", "derived"),
        ("S26 net, pre-orders only (range across cost scenarios)",
         f"${sc.net_pre_orders_only.min():.0f} to ${sc.net_pre_orders_only.max():.0f}", "estimate"),
        ("S26 net with assumed 10% buffer (range, worst to best)",
         f"${sc.net_buffer_worst.min():.0f} to ${sc.net_buffer_best.max():.0f}", "estimate"),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "tag"])


def run_all(con=None) -> dict:
    con = con or connect()
    return {
        "verification": verify_totals(con), "event_pnl": event_pnl(con),
        "f24_reconciliation": f24_reconciliation(con), "cost_structure": cost_structure(con),
        "unit_economics": unit_economics(con), "price_schedule": price_schedule(con),
        "demand": demand(con), "s26_scenarios": s26_scenarios(), "sensitivity": sensitivity(),
        "headline": headline_numbers(con),
    }


def export_tables(res: dict) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    res["event_pnl"].to_csv(PROCESSED / "event_pnl.csv", index=False)
    res["cost_structure"].to_csv(PROCESSED / "cost_structure.csv", index=False)
    res["price_schedule"].to_csv(PROCESSED / "price_schedule_observed.csv", index=False)
    res["s26_scenarios"].to_csv(PROCESSED / "s26_scenarios.csv", index=False)
    res["unit_economics"]["s26_cost_scenarios"].to_csv(PROCESSED / "s26_cost_scenarios.csv", index=False)
    res["demand"]["concentration"].to_csv(PROCESSED / "s26_concentration.csv", index=False)
    res["demand"]["by_day"].to_csv(PROCESSED / "s26_demand_by_day.csv", index=False)
    res["demand"]["by_hour"].to_csv(PROCESSED / "s26_demand_by_hour.csv", index=False)
    res["sensitivity"]["cost_price"].to_csv(PROCESSED / "sensitivity_cost_price.csv")
    res["sensitivity"]["buffer_sellthrough"].to_csv(PROCESSED / "sensitivity_buffer_sellthrough.csv")
    res["sensitivity"]["one_at_a_time"].to_csv(PROCESSED / "sensitivity_one_at_a_time.csv", index=False)
    res["headline"].to_csv(PROCESSED / "headline_numbers.csv", index=False)
    with open(PROCESSED / "f24_reconciliation.json", "w") as f:
        json.dump(res["f24_reconciliation"], f, indent=2)
