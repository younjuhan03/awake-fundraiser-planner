"""AWAKE Fundraiser Planner (Streamlit).   streamlit run app.py

Decision-support tool, not a forecast. Anything not directly observed is labeled ESTIMATE or SCENARIO.
Uses Streamlit's native widgets/charts only, so it follows the viewer's light/dark theme.
"""
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from awake import analysis as an, config, db, planner  # noqa: E402
from awake.paths import ROOT as PROJECT_ROOT  # noqa: E402

st.set_page_config(page_title="AWAKE Fundraiser Planner", page_icon="🍪", layout="wide")

TAG_COLOR = {"observed": "blue", "derived": "green", "assumed": "orange", "estimate": "orange", "scenario": "orange"}


def tag(kind: str):
    st.badge(kind.upper(), color=TAG_COLOR[kind.split()[0].lower()])


def usd(x, d=2):
    return f"-${abs(x):,.{d}f}" if x < 0 else f"${x:,.{d}f}"


@st.cache_data(show_spinner=False)
def load():
    con = db.connect()
    try:
        return an.run_all(con)
    finally:
        con.close()


res = load()
A = config.values()
RAW = config.scalar_assumptions()

PAGES = ["Project Overview", "Past Events", "Demand", "Planner", "Assumptions & Data Notes"]
_qp = st.query_params.get("page")  # e.g. ?page=Demand (used for README screenshots)
page = st.sidebar.radio("Page", PAGES, index=PAGES.index(_qp) if _qp in PAGES else 0)
st.sidebar.markdown(
    "**How to read the labels**\n\n"
    ":blue-badge[OBSERVED] read from the data  \n"
    ":green-badge[DERIVED] calculated from observed data  \n"
    ":orange-badge[ESTIMATE] depends on an assumption: **not a fact**"
)
st.sidebar.caption("Participant names and contact details are omitted. Records retain order IDs and timestamps; this app displays aggregates.")

# ===================================================================== Past Events
if page == "Project Overview":
    st.caption("JUHAN YOUN / APPLIED ANALYTICS CASE STUDY")
    st.title("From pre-orders to a defensible production plan")
    st.markdown("A student fundraiser has limited cash, volunteer time, and incomplete records. "
                "This project makes the cost of producing extra food visible before leaders commit to it.")
    k1, k2, k3 = st.columns(3)
    k1.metric("S26 pre-orders (observed)", "29 orders")
    k2.metric("Pre-ordered quantity (observed)", "104 items")
    k3.metric("Pre-order revenue (observed)", "$375")
    st.subheader("My role and the project's scope")
    st.markdown("As AWAKE's Finance/Social Leader, I introduced an online pre-order form with day-of pickup. "
                "Subsequent leaders continued the pre-order process after I left. "
                "I use the available records to develop a reusable planning tool; "
                "adoption of the pre-order process does not establish adoption or impact of this app.")
    st.subheader("The decision: how much extra food should we make?")
    st.markdown("At a proxy cost of **$190 / 108 = $1.76 per item** and an assumed walk-up price of "
                "**$3.50**, an extra item needs about **50.3% sell-through** to cover its cost. "
                "A 10% buffer rounds 104 pre-orders up to **115 items**, so 11 extra items are at risk.")
    st.info("At 50% assumed sell-through, the 11-item buffer changes net by about -$0.10 versus "
            "making only the 104 pre-orders. With zero walk-up sales it loses about $19.35; "
            "if all 11 sell it adds about $19.15. These are conditional calculations, not forecasts.")
    st.markdown("**Planning implication:** start from confirmed pre-orders; choose an extra buffer only after "
                "checking current receipts, preparation capacity, and the downside leaders can accept. "
                "The tool evaluates a chosen buffer; it does not optimize production or price.")
    st.subheader("What the evidence supports")
    st.dataframe(pd.DataFrame([
        ["Historical P&L", "F24 net $234.54; S25 net $182.00", "Derived from ledger transactions"],
        ["Demand concentration", "One order accounts for 26.9% of S26 items", "Derived; confirm large orders before shopping"],
        ["S26 profitability", "Unknown; costs and production were not recorded", "The $101-$294 scenario range is not realized profit"],
        ["Operational improvement", "Pre-order process introduced", "No recorded baseline or post-change waste rate"],
    ], columns=["Question", "Finding", "Evidence / limitation"]), hide_index=True)
    st.subheader("Method and next validation")
    st.markdown("Anonymized CSV records → SQLite reconciliation → scenario calculations → sensitivity checks → "
                "Streamlit and spreadsheet handoff. Two costed events are insufficient for a credible demand model. "
                "For the next event, record production, walk-up sales, leftovers, receipts, and preparation hours; "
                "compare the planned and realized outcomes before claiming impact.")
    st.caption("My calculations, assumptions and development notes are documented in the repository README.")
    workbook = PROJECT_ROOT / "exports/fundraiser_planner.xlsx"
    if workbook.exists():
        st.download_button("Download the spreadsheet planner", workbook.read_bytes(),
                           file_name="fundraiser_planner.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Use the sidebar to inspect Past Events, Demand, Planner, or Assumptions & Data Notes.")

elif page == "Past Events":
    st.title("Past events")
    st.caption("F24 and S25 come from the account book. S26 has only pre-order form data; its costs were not recorded.")
    pnl = res["event_pnl"].set_index("event_id")
    rec = res["f24_reconciliation"]
    ue = res["unit_economics"]

    st.subheader("Event P&L")
    tag("observed")
    for e, label in [("F24", "Fall 2024"), ("S25", "Spring 2025")]:
        r = pnl.loc[e]
        st.markdown(f"**{e} ({label})**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Revenue (observed)", usd(r.revenue_usd))
        m2.metric("Cost (observed)", usd(r.cost_usd))
        m3.metric("Net (derived)", usd(r.net_usd))
        m4.metric("Margin (derived)", f"{r.margin:.1%}")
    st.bar_chart(pnl.loc[["F24", "S25"], ["revenue_usd", "cost_usd", "net_usd"]]
                 .rename(columns={"revenue_usd": "Revenue", "cost_usd": "Cost", "net_usd": "Net"}),
                 y_label="USD (observed / derived)", x_label="Event", stack=False)

    st.subheader("F24: ledger memo vs transactions")
    st.warning(
        f"The ledger memo says F24 net profit was **{usd(rec['ledger_memo_net'])}**, but revenue "
        f"{usd(rec['revenue'])} minus fundraiser expenses {usd(rec['fundraiser_expenses'])} is "
        f"**{usd(rec['computed_net'])}**. The {usd(rec['unexplained_difference'])} difference is unresolved. "
        "This tool uses the computed figure.")
    d1, d2, d3 = st.columns(3)
    d1.metric("Computed net (primary, derived)", usd(rec["computed_net"]))
    d2.metric("Ledger memo net (observed)", usd(rec["ledger_memo_net"]), delta=f"{usd(rec['unexplained_difference'])} vs computed", delta_color="off")
    d3.metric("Net incl. $75 parking fine (derived)", usd(rec["net_with_parking_fine"]),
              help="The ledger classes the fine as 'unplanned', not a fundraiser expense.")

    st.subheader("Cost structure")
    tag("observed")
    cs = res["cost_structure"]
    share = cs.pivot(index="event_id", columns="category", values="share").fillna(0)
    st.bar_chart(share, y_label="Share of planned cost (parking fine excluded)", x_label="Event", stack="normalize")
    st.dataframe(cs.assign(share=cs.share.map("{:.1%}".format), cost_usd=cs.cost_usd.map(usd)), hide_index=True)
    st.caption("F24 HEB 'supplies' purchases were categorized as ingredients in the ledger, so F24's ingredient share may be overstated (data_issues.md #3).")

    st.subheader("Unit economics (S25, per item purchased)")
    tag("derived")
    u1, u2, u3, u4 = st.columns(4)
    u1.metric("All-in cost / item", usd(ue["s25_all_in_cost_per_item"]))
    u2.metric("Ingredients / item", usd(ue["s25_ingredients_per_item"]))
    u3.metric("Supplies / item", usd(ue["s25_supplies_per_item"]))
    u4.metric("Revenue / item purchased", usd(ue["s25_revenue_per_item_purchased"]))
    st.caption("Items sold were not recorded; these use the 108 items purchased.")

    st.subheader("S26 net profit")
    tag("estimate")
    st.info("S26 costs and items cooked were never recorded. Revenue below is the observed $375 of pre-orders; "
            "cost per item comes from four labeled scenarios. These are ESTIMATES, not results.")
    sc = res["s26_scenarios"]
    show = sc[["scenario", "name", "unit_cost_usd", "cost_confidence", "net_pre_orders_only",
               "net_buffer_worst", "net_buffer_expected", "net_buffer_best"]].copy()
    show.columns = ["Case", "Cost scenario", "Cost / item", "Cost type", "Net: cook exactly pre-orders (ESTIMATE)",
                    "Net with 10% buffer, 0% sell-through (ESTIMATE)", "chosen sell-through (ESTIMATE)", "100% sell-through (ESTIMATE)"]
    for c in show.columns[[2, 4, 5, 6, 7]]:
        show[c] = show[c].map(usd)
    st.dataframe(show, hide_index=True)
    lo, hi = sc.net_pre_orders_only.min(), sc.net_pre_orders_only.max()
    st.metric("S26 net range, cooking exactly the pre-orders (ESTIMATE)", f"{usd(lo, 0)} to {usd(hi, 0)}")
    st.image(str(PROJECT_ROOT / "docs/figures/s26_net_scenarios.png"), caption="Hatched = estimate")

# ===================================================================== Demand
elif page == "Demand":
    st.title("Demand: S26 pre-orders")
    tag("observed")
    d = res["demand"]
    c = d["concentration"].set_index("view")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Orders (observed)", d["n_orders"])
    k2.metric("Items (observed)", d["units"])
    k3.metric("Revenue (observed)", usd(d["revenue_usd"], 0))
    k4.metric("Avg price / item (derived)", usd(d["revenue_usd"] / d["units"]))

    st.subheader("Order-size distribution")
    sd = d["size_distribution"].set_index("quantity")
    st.bar_chart(sd.n_orders, x_label="Items per order", y_label="Number of orders")
    st.caption(f"Median order = {c.loc['all orders','median_order_units']:.0f} items; mean = {c.loc['all orders','mean_order_units']:.2f}.")

    st.subheader("Concentration")
    tag("derived")
    x1, x2 = st.columns(2)
    x1.metric(f"Largest order (#{d['largest_order_id']}): share of items", f"{d['largest_units_share']:.1%}", help="28 of 104 items")
    x2.metric("Largest order: share of revenue", f"{d['largest_revenue_share']:.1%}", help="$100 of $375")
    ct = c[["n_orders", "units", "revenue_usd", "hhi_units", "hhi_revenue", "equal_orders_hhi", "avg_price_per_item_usd"]].copy()
    ct.columns = ["Orders", "Items", "Revenue ($)", "HHI (items)", "HHI (revenue)", "HHI if all orders equal (1/n)", "Avg $/item"]
    st.dataframe(ct.round(4))
    st.caption("Herfindahl index = sum of squared shares (0 to 1). Higher means demand rests on fewer orders.")

    st.subheader("Timing")
    tag("observed")
    st.line_chart(d["by_day"].set_index("day")[["cum_orders", "cum_units"]]
                  .rename(columns={"cum_orders": "Cumulative orders", "cum_units": "Cumulative items"}),
                  x_label="Day", y_label="Count")
    t1, t2, t3 = st.columns(3)
    t1.metric("Orders placed on day 1 (Feb 26)", f"{d['day1_orders_share']:.1%}", help=f"{d['day1_units_share']:.1%} of items")
    t2.metric("Orders on Mar 2–3", f"{d['wave2_orders']} of {d['n_orders']}", help=f"{d['wave2_units']} of {d['units']} items")
    t3.metric("Days with zero orders", ", ".join(x[5:] for x in d["zero_order_days"]))
    st.caption("Mar 2–3 shows a second burst of orders after two quiet days. This is a pattern only: "
               "the data does not say why (form close date and any reminders were not recorded).")
    st.bar_chart(d["by_hour"].set_index("hour").n_orders, x_label="Hour of day (as recorded)", y_label="Orders")

    st.subheader("Observed price schedule")
    st.dataframe(res["price_schedule"].rename(columns={"modal_amount_usd": "Amount ($)", "price_per_item_usd": "$/item"}), hide_index=True)
    st.caption("Flags are observations, not explanations. Why 1 item = \\$7 or one 4-item order = \\$15 is unknown.")

# ===================================================================== Planner
elif page == "Planner":
    st.title("Planner")
    st.caption("What production and profit follow from the assumptions we choose? Walk-up numbers are assumptions: change them.")
    cs = an.cost_scenarios(A)
    presets = {f"{r.scenario}: {r.name} ({r.confidence})": round(float(r.unit_cost_usd), 4) for r in cs.itertuples()}
    presets["Custom"] = None

    left, right = st.columns([1, 1.6])
    with left:
        st.subheader("Inputs")
        units = st.number_input("Pre-order items (observed, S26 default)", 0, 10000, int(A["preorder_units"]), 1)
        rev = st.number_input("Pre-order revenue, $ (observed, S26 default)", 0.0, 100000.0, float(A["preorder_revenue_usd"]), 1.0)
        buf = st.slider("Walk-up buffer, % extra items cooked (ASSUMED)", 0, 100, int(A["walkup_buffer_pct"] * 100), 1) / 100
        st_ = st.slider("Walk-up sell-through, % of buffer items sold (ASSUMED)", 0, 100, int(A["walkup_sellthrough_pct"] * 100), 5) / 100
        wprice = st.number_input("Walk-up price per item, $ (ASSUMED)", 0.0, 100.0, float(A["walkup_price_usd"]), 0.25)
        choice = st.selectbox("Cost per item: preset", list(presets))
        default_cost = presets[choice] if presets[choice] is not None else float(A["unit_cost_usd"])
        cost = st.number_input("Cost per item, $", 0.0, 100.0, float(round(default_cost, 4)), 0.05, key=f"cost_{choice}",
                               help="Preset values are derived or assumed; see Assumptions & Data Notes.")
        fixed = st.number_input("Fixed costs, $ (printing, supplies; ASSUMED)", 0.0, 10000.0, float(A["fixed_costs_usd"]), 5.0,
                                help="Default 0 because the S25 all-in cost already includes supplies. Add fixed costs if you use an ingredients-only cost.")
        if st.checkbox(f"Add unplanned-cost reserve (F24 parking fine: {usd(A['unplanned_reserve_usd'], 0)})"):
            fixed += A["unplanned_reserve_usd"]

    inputs = planner.PlannerInputs(units, rev, buf, st_, wprice, cost, fixed)
    try:
        r = planner.evaluate(inputs)
        sc = planner.scenarios(inputs)
        err = None
    except ValueError as e:
        err = str(e)

    with right:
        st.subheader("Results")
        if err:
            st.error(err)
        else:
            tag("estimate")
            m1, m2, m3 = st.columns(3)
            m1.metric("Production under chosen buffer", f"{r.production_qty} items", help="pre-orders x (1 + buffer), rounded up")
            m2.metric("Revenue at chosen sell-through (ESTIMATE)", usd(r.revenue))
            m3.metric("Total cost", usd(r.total_cost))
            m4, m5, m6 = st.columns(3)
            m4.metric("Net at chosen sell-through (ESTIMATE)", usd(r.net))
            m5.metric("Margin (ESTIMATE)", "n/a" if r.margin is None else f"{r.margin:.1%}")
            if r.breakeven_units_sold is None:
                m6.metric("Break-even items sold", "not reachable")
            else:
                m6.metric("Break-even items sold", r.breakeven_units_sold,
                          help="Pre-orders count first at their average price, then walk-ups at the walk-up price.")
            if r.breakeven_units_sold is not None and not r.breakeven_reachable:
                st.warning("Break-even needs more items sold than you plan to cook.")
            if r.walkup_capacity == 0:
                st.info("No buffer: you cook exactly the pre-orders, so there is nothing to sell to walk-ups.")
            elif r.buffer_expected_to_pay:
                st.success(f"With these assumptions each buffer item is expected to earn more than it costs "
                           f"(sell-through {st_:.0%} > break-even {cost / wprice:.1%}).")
            else:
                st.warning(f"With these assumptions a buffer item does not earn more than its cost: "
                           f"it would need a sell-through above {cost / wprice:.1%}." if wprice > 0 else
                           "Walk-up price is $0, so buffer items cannot pay back.")

            base = planner.evaluate(planner.PlannerInputs(units, rev, 0.0, st_, wprice, cost, fixed))
            st.metric("Net change versus producing only pre-orders (SCENARIO)", usd(r.net - base.net))
            st.caption(f"Additional production: {r.walkup_capacity} items; leftover quantity under this "
                       f"scenario: {r.leftover_units:.1f}. Fractional sales are scenario averages, not literal item counts. "
                       "The 0% and 100% cases vary walk-up sales only, holding costs and pre-order payment fixed.")

            st.markdown("**0% / chosen / 100% sell-through** (walk-up sell-through 0% / your input / 100%; scenarios, not forecasts)")
            tbl = pd.DataFrame({
                "Case": ["0% sold", "Chosen input", "100% sold"],
                "Walk-up sell-through": [sc[k].walkup_units_sold / sc[k].walkup_capacity if sc[k].walkup_capacity else 0 for k in ("worst", "expected", "best")],
                "Walk-up items sold": [sc[k].walkup_units_sold for k in ("worst", "expected", "best")],
                "Revenue (ESTIMATE)": [sc[k].revenue for k in ("worst", "expected", "best")],
                "Net profit (ESTIMATE)": [sc[k].net for k in ("worst", "expected", "best")],
            })
            st.caption(f"Total cost is the same in all three cases: {usd(r.total_cost)} (every item cooked is paid for).")
            st.dataframe(tbl.style.format({"Walk-up sell-through": "{:.0%}", "Walk-up items sold": "{:.1f}",
                                           "Revenue (ESTIMATE)": "${:,.2f}", "Net profit (ESTIMATE)": "${:,.2f}"}),
                         hide_index=True)
            chart = tbl.assign(Case=["1 No walk-ups", "2 Chosen input", "3 All buffer sold"]).set_index("Case")[["Net profit (ESTIMATE)"]]
            st.bar_chart(chart, y_label="Net profit, USD (ESTIMATE)", x_label="Walk-up sell-through case")

            with st.expander("Sensitivity: expected net profit (ESTIMATE) vs buffer and sell-through"):
                buffers = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]
                sts = [0.0, 0.25, 0.5, 0.75, 1.0]
                grid = pd.DataFrame(
                    [[planner.evaluate(planner.PlannerInputs(units, rev, b, s, wprice, cost, fixed)).net for s in sts] for b in buffers],
                    index=[f"{b:.0%} buffer" for b in buffers], columns=[f"{s:.0%} sold" for s in sts])
                st.dataframe(grid.style.format("${:,.0f}"))

    st.divider()
    st.subheader("Quote an order")
    qcol1, qcol2 = st.columns(2)
    qty = qcol1.number_input("Items in the order", 1, 500, 4, 1)
    sched = config.price_schedule()
    q = planner.price_for_quantity(int(qty), sched, A["price_fallback_per_item_usd"])
    qcol2.metric("Quote", usd(q))
    if qty in sched:
        qcol2.caption("Observed on the S26 form" + (" (one 4-item order was $15)" if qty == 4 else ""))
    else:
        qcol2.caption("ESTIMATE: this order size was not seen; uses the assumed per-item price.")
    st.caption("A separate quote for very large orders is a suggestion to test, not a finding: only one 28-item order exists in the data.")

# ===================================================================== Assumptions & Data Notes
else:
    st.title("Assumptions & data notes")
    st.subheader("Assumptions")
    st.caption("Defaults in config/assumptions.yaml. Confidence: observed (read from data), derived (calculated from data), assumed (judgment call).")
    rows = [{"key": k, "value": v["value"], "confidence": v["confidence"], "source": v["source"], "note": v["note"]} for k, v in RAW.items()]
    df = pd.DataFrame(rows)
    sel = st.multiselect("Filter by confidence", ["observed", "derived", "assumed"], default=["observed", "derived", "assumed"])
    st.dataframe(df[df.confidence.isin(sel)], hide_index=True)

    st.subheader("Verification of source totals")
    ver = res["verification"].reset_index(names="check")
    st.dataframe(ver, hide_index=True)

    st.subheader("Data issues")
    st.markdown((PROJECT_ROOT / "data_issues.md").read_text(encoding="utf-8"))

    st.subheader("Open questions for current AWAKE leaders")
    st.markdown(
        "- What were the S26 receipts in total, and what did the menu consist of?\n"
        "- How many items were cooked, and how many were left over (if any)?\n"
        "- How many walk-up sales were there, and at what price?\n"
        "- Was a reminder sent around Mar 2? When did the form close?\n"
        "- Why did a 1-item order cost $7, and why was one 4-item order $15?\n"
        "- Which source explains the F24 ledger memo net of $261.13?")

