"""Leader-friendly spreadsheet (works in Excel and Google Sheets): exports/fundraiser_planner.xlsx

Every output is a live formula. Same logic as src/awake/planner.py (tests compare the two).
Colors: BLUE input = observed/derived from data; YELLOW input = assumption you should change; GREY = formula.
"""
from __future__ import annotations

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

from . import analysis, config
from .db import connect
from .paths import EXPORTS

BLUE = PatternFill("solid", fgColor="DCE9F7")
YELLOW = PatternFill("solid", fgColor="FFF2CC")
GREY = PatternFill("solid", fgColor="F0F0F0")
HEAD = PatternFill("solid", fgColor="2A6FB0")
EST = PatternFill("solid", fgColor="FCE4C4")
WHITE_BOLD = Font(bold=True, color="FFFFFF")
BOLD = Font(bold=True)
THIN = Side(style="thin", color="BBBBBB")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
USD = '"$"#,##0.00'
PCT = "0.0%"

# Planner cell map (kept in one place so tests and docs agree)
CELLS = dict(units="B5", revenue="B6", buffer="B7", sellthrough="B8", price="B9", cost="B10", fixed="B11",
             production="B15", net="B23", breakeven="B25")


def _header(ws, row, labels, widths=None):
    for i, text in enumerate(labels, start=1):
        c = ws.cell(row=row, column=i, value=text)
        c.fill, c.font, c.border, c.alignment = HEAD, WHITE_BOLD, BOX, Alignment(wrap_text=True, vertical="center")


def _planner(wb, a):
    ws = wb.active
    ws.title = "Planner"
    ws["A1"] = "AWAKE Fundraiser Planner"
    ws["A1"].font = Font(bold=True, size=16)
    ws["A2"] = ("Change the YELLOW and BLUE cells. Everything else is a formula. "
                "Anything marked ESTIMATE depends on an assumption, not on recorded data.")
    ws["A2"].alignment = WRAP
    ws.merge_cells("A2:D2")
    ws.row_dimensions[2].height = 32
    _header(ws, 4, ["Input", "Value", "Type", "Where the default comes from"])
    inputs = [
        ("Pre-order items (from the form)", int(a["preorder_units"]), "observed", "S26 form total: 29 orders, 104 items. Replace with this semester's form total.", None, BLUE, "0"),
        ("Pre-order revenue ($, from the form)", a["preorder_revenue_usd"], "observed", "S26 form total $375. Replace with this semester's form total.", None, BLUE, USD),
        ("Walk-up buffer (% extra items cooked)", a["walkup_buffer_pct"], "ASSUMED", "No data on items cooked or leftovers. 0% = cook exactly the pre-orders.", None, YELLOW, PCT),
        ("Walk-up sell-through (% of buffer items sold)", a["walkup_sellthrough_pct"], "ASSUMED", "No walk-up data. Placeholder midpoint; the table below also shows 0% and 100%.", None, YELLOW, PCT),
        ("Walk-up price per item ($)", a["walkup_price_usd"], "ASSUMED", "Never recorded. Based on $7 for 2 items on the pre-order form.", None, YELLOW, USD),
        ("Cost per item ($)", "=190/108", "ASSUMED", "S25 proxy: $190.00 / 108 items purchased. Applying it to a new menu is assumed; see Past Events for other cost cases.", None, YELLOW, USD),
        ("Fixed costs ($: printing, supplies)", a["fixed_costs_usd"], "ASSUMED", "0 because the S25 cost per item already includes supplies. Add printing etc. if you use an ingredients-only cost.", None, YELLOW, USD),
    ]
    for i, (label, val, typ, note, _, fill, fmt) in enumerate(inputs):
        r = 5 + i
        ws.cell(r, 1, label).border = BOX
        c = ws.cell(r, 2, val)
        c.fill, c.number_format, c.border = fill, fmt, BOX
        t = ws.cell(r, 3, typ)
        t.border = BOX
        if typ == "ASSUMED":
            t.font = Font(bold=True, color="B45F06")
        n = ws.cell(r, 4, note)
        n.alignment, n.border = WRAP, BOX
        ws.row_dimensions[r].height = 30

    ws["A13"], ws["A13"].font = "Results (SCENARIOS: current-event unit cost is unrecorded)", BOLD
    _header(ws, 14, ["Output", "Value", "How it is calculated", ""])
    out = [
        (15, "Production under chosen buffer (items)", "=ROUNDUP(ROUND(B5*(1+B7),9),0)", "0", "pre-orders x (1 + buffer), rounded up"),
        (16, "Buffer items (extra for walk-ups)", "=B15-B5", "0", "production - pre-orders"),
        (17, "Scenario walk-up items sold  [ESTIMATE]", "=B16*B8", "0.0", "buffer items x sell-through"),
        (18, "Scenario leftover items  [ESTIMATE]", "=B16-B17", "0.0", "buffer items - walk-up items sold"),
        (19, "Pre-order revenue", "=B6", USD, "from the form"),
        (20, "Scenario walk-up revenue  [ESTIMATE]", "=B17*B9", USD, "walk-up items sold x walk-up price"),
        (21, "Scenario revenue  [ESTIMATE]", "=B19+B20", USD, "pre-order + walk-up revenue"),
        (22, "Total cost", "=B15*B10+B11", USD, "every item cooked x cost per item + fixed costs"),
        (23, "Scenario net profit  [ESTIMATE]", "=B21-B22", USD, "revenue - cost"),
        (24, "Margin  [ESTIMATE]", '=IF(B21=0,"n/a",B23/B21)', PCT, "net profit / revenue"),
        (25, "Break-even: items that must be sold",
         '=IF(B22<=0,0,IF(B6>=B22,ROUNDUP(ROUND(B22/(B6/B5),9),0),IF(B9<=0,"not reachable",B5+ROUNDUP(ROUND((B22-B6)/B9,9),0))))', "0",
         "pre-orders count first (at their average price), then walk-ups at the walk-up price"),
        (26, "Break-even: walk-up items needed", '=IF(ISNUMBER(B25),MAX(0,B25-B5),"not reachable")', "0", "break-even items - pre-order items"),
        (27, "Is break-even reachable with this production?",
         '=IF(ISNUMBER(B25),IF(B25<=B15,"Yes","No: you would need to sell more items than you cook"),"No")', "@", "break-even items <= items cooked"),
        (28, "Does the buffer add profit at this sell-through?  [ESTIMATE]",
         '=IF(B8*B9>B10,"Yes: scenario walk-up revenue per buffer item exceeds its cost","No: scenario revenue does not exceed cost")', "@",
         "sell-through x walk-up price vs cost per item"),
        (29, "Sell-through at which a buffer item breaks even", '=IF(B9>0,B10/B9,"n/a")', PCT, "cost per item / walk-up price"),
    ]
    # NOTE: production sits at row 15, net at 23, break-even at 25 (see CELLS).
    for r, label, f, fmt, how in out:
        ws.cell(r, 1, label).border = BOX
        c = ws.cell(r, 2, f)
        c.fill, c.number_format, c.border = (EST if "ESTIMATE" in label else GREY), fmt, BOX
        c.alignment = Alignment(wrap_text=True, horizontal="right")
        h = ws.cell(r, 3, how)
        h.alignment, h.border = WRAP, BOX
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
    ws.row_dimensions[28].height = 45
    ws.row_dimensions[27].height = 30

    ws["A31"], ws["A31"].font = "0% / chosen / 100% sell-through (conditional scenarios)", BOLD
    _header(ws, 32, ["Case", "Walk-up sell-through", "Walk-up items sold", "Revenue", "Total cost", "Net profit"])
    for r, (label, st) in enumerate([("0%: no walk-up sales", 0), ("Expected: sell-through from B8", "=B8"), ("100%: every buffer item sold", 1)], start=33):
        ws.cell(r, 1, label)
        ws.cell(r, 2, st).number_format = PCT
        ws.cell(r, 3, f"=$B$16*B{r}").number_format = "0.0"
        ws.cell(r, 4, f"=$B$6+C{r}*$B$9").number_format = USD
        ws.cell(r, 5, "=$B$22").number_format = USD
        ws.cell(r, 6, f"=D{r}-E{r}").number_format = USD
        for col in range(1, 7):
            ws.cell(r, col).border = BOX
            ws.cell(r, col).fill = EST if col > 1 else GREY
    ws.conditional_formatting.add("F33:F35", FormulaRule(formula=["F33<0"], font=Font(color="C00000", bold=True)))
    ws.conditional_formatting.add("B23", FormulaRule(formula=["B23<0"], font=Font(color="C00000", bold=True)))

    dv_pct = DataValidation(type="decimal", operator="between", formula1="0", formula2="1", showErrorMessage=True,
                            errorTitle="Percent", error="Enter a value between 0% and 100%.")
    dv_pos = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", showErrorMessage=True,
                            errorTitle="Number", error="Enter a number that is 0 or more.")
    dv_buf = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", showErrorMessage=True,
                            errorTitle="Buffer", error="Enter 0% or more (for example 10%).")
    for dv in (dv_pct, dv_pos, dv_buf):
        dv.errorStyle = "stop"
        ws.add_data_validation(dv)
    dv_pct.add("B8")
    dv_buf.add("B7")
    dv_units = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", showErrorMessage=True,
                              errorStyle="stop", errorTitle="Whole items", error="Enter a non-negative whole number.")
    ws.add_data_validation(dv_units)
    dv_units.add("B5")
    dv_pos.add("B6")
    dv_pos.add("B9:B11")
    for col, w in zip("ABCDEF", (50, 18, 20, 44, 14, 14)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"


def _quote(wb, a):
    ws = wb.create_sheet("Price Quote")
    ws["A1"], ws["A1"].font = "Quote a pre-order", Font(bold=True, size=14)
    ws["A2"] = "Type the number of items in an order. The price comes from the S26 form if that order size was seen, otherwise it is an ESTIMATE."
    ws["A2"].alignment = WRAP
    ws.merge_cells("A2:D2")
    ws.row_dimensions[2].height = 32
    ws["A4"], ws["B4"] = "Items in order", 4
    ws["B4"].fill, ws["B4"].border = YELLOW, BOX
    ws["A5"], ws["B5"] = "Price", '=IFERROR(VLOOKUP(B4,$F$5:$G$10,2,FALSE),ROUND(B4*$B$7,2))'
    ws["B5"].number_format, ws["B5"].fill = USD, GREY
    ws["A6"], ws["B6"] = "Source", '=IF(ISNUMBER(MATCH(B4,$F$5:$F$10,0)),"observed on the S26 form","ESTIMATE: this order size was never seen")'
    ws["A7"], ws["B7"] = "Per-item price for unseen sizes ($, assumed)", a["price_fallback_per_item_usd"]
    ws["B7"].fill, ws["B7"].number_format = YELLOW, USD
    for r in (4, 5, 6, 7):
        ws.cell(r, 1).border = ws.cell(r, 2).border = BOX
    ws["F3"], ws["F3"].font = "Observed S26 schedule (modal amount)", BOLD
    for i, h in enumerate(["Items", "Amount ($)", "Seen on form"]):
        c = ws.cell(4, 6 + i, h)
        c.fill, c.font, c.border = HEAD, WHITE_BOLD, BOX
    ps = analysis.price_schedule(connect()).sort_values("quantity")
    for i, r in enumerate(ps.itertuples(), start=5):
        for j, v in enumerate([r.quantity, r.modal_amount_usd, f"{r.n_orders} order(s)" + (f"; {r.flag}" if r.flag else "")]):
            c = ws.cell(i, 6 + j, v)
            c.border = BOX
            if j == 1:
                c.number_format, c.fill = USD, BLUE
    ws["F12"] = "Flags are notes, not explanations: the reason for 1 item costing $7, or one 4-item order costing $15, is unknown."
    ws["F12"].alignment = WRAP
    ws.merge_cells("F12:H13")
    for col, w in zip("ABCDEFGH", (42, 38, 3, 3, 3, 8, 12, 60)):
        ws.column_dimensions[col].width = w


def _past(wb, a, res):
    ws = wb.create_sheet("Past Events")
    ws["A1"], ws["A1"].font = "Past events", Font(bold=True, size=14)
    _header(ws, 3, ["Event", "Revenue", "Fundraiser cost", "Net (formula)", "Margin (formula)", "Status"])
    pnl = res["event_pnl"].set_index("event_id")
    rows = [("F24 (Fall 2024)", pnl.loc["F24", "revenue_usd"], pnl.loc["F24", "cost_usd"], "observed; net is derived"),
            ("S25 (Spring 2025)", pnl.loc["S25", "revenue_usd"], pnl.loc["S25", "cost_usd"], "observed; net is derived")]
    for i, (e, rev, cost, st) in enumerate(rows, start=4):
        ws.cell(i, 1, e)
        ws.cell(i, 2, float(rev)).number_format = USD
        ws.cell(i, 3, float(cost)).number_format = USD
        ws.cell(i, 4, f"=B{i}-C{i}").number_format = USD
        ws.cell(i, 5, f"=D{i}/B{i}").number_format = PCT
        ws.cell(i, 6, st)
        for col in range(1, 7):
            ws.cell(i, col).border = BOX
        ws.cell(i, 2).fill = ws.cell(i, 3).fill = BLUE
    ws["A7"], ws["A7"].font = "F24 notes", BOLD
    notes = [("Net as written in the ledger memo", 261.13, "observed (memo)", None),
             ("Unexplained difference (memo - computed)", "=B8-D4", "derived", None),
             ("Parking fine on the day (ledger: 'unplanned')", 75.0, "observed", None),
             ("F24 net including the parking fine", "=D4-B10", "derived", None)]
    for i, (lab, v, tag, _) in enumerate(notes, start=8):
        ws.cell(i, 1, lab)
        ws.cell(i, 2, v).number_format = USD
        ws.cell(i, 3, tag)
        for col in range(1, 4):
            ws.cell(i, col).border = BOX
    ws["A13"], ws["A13"].font = "S25 per item (items PURCHASED: 108; items sold were not recorded)", BOLD
    ws["A14"], ws["B14"] = "Items purchased", 108
    ws["A15"], ws["B15"] = "All-in cost per item", "=C5/B14"
    ws["A16"], ws["B16"] = "Revenue per item purchased", "=B5/B14"
    ws["B15"].number_format = ws["B16"].number_format = USD
    ws["A18"], ws["A18"].font = "S26 pre-orders (observed): costs and walk-up sales were NOT recorded", BOLD
    ws["A19"], ws["B19"] = "Orders", 29
    ws["A20"], ws["B20"] = "Items", int(a["preorder_units"])
    ws["A21"], ws["B21"] = "Revenue", a["preorder_revenue_usd"]
    ws["A22"], ws["B22"] = "Average price per item (formula)", "=B21/B20"
    ws["B21"].number_format = ws["B22"].number_format = USD
    ws["A24"], ws["A24"].font = "S26 net profit ESTIMATES if you cook exactly the pre-orders (cost cases are scenarios)", BOLD
    _header(ws, 25, ["Cost case", "Cost per item", "Cost type", "Total cost (formula)", "Net profit ESTIMATE (formula)", "Source"])
    cs = res["unit_economics"]["s26_cost_scenarios"]
    for i, r in enumerate(cs.itertuples(), start=26):
        ws.cell(i, 1, f"{r.scenario}: {r.name}")
        ws.cell(i, 2, round(float(r.unit_cost_usd), 4)).number_format = USD
        ws.cell(i, 3, r.confidence)
        ws.cell(i, 4, f"=B{i}*$B$20").number_format = USD
        ws.cell(i, 5, f"=$B$21-D{i}").number_format = USD
        ws.cell(i, 6, r.source)
        for col in range(1, 7):
            ws.cell(i, col).border = BOX
        ws.cell(i, 5).fill = EST
        ws.cell(i, 2).fill = YELLOW if r.confidence == "assumed" else BLUE
    for col, w in zip("ABCDEF", (52, 16, 16, 20, 24, 70)):
        ws.column_dimensions[col].width = w


def _notes(wb):
    ws = wb.create_sheet("Data Notes")
    ws["A1"], ws["A1"].font = "Data notes (full list: data_issues.md in the repository)", Font(bold=True, size=14)
    lines = [
        "Observed = copied from the account book, planning memo or pre-order form. Derived = calculated from observed numbers. Assumed/ESTIMATE = a guess you can change.",
        "Units cooked and units left over were never recorded, so leftover rates are unknown. The buffer and sell-through inputs are assumptions.",
        "F24: the ledger memo says net profit $261.13, but the transactions give $234.54. Unresolved. This tool uses $234.54.",
        "F24: a $75 parking fine is excluded from fundraiser cost (the ledger calls it 'unplanned'). The net including it is $159.54.",
        "S25 per-item figures use items purchased (108), not items sold.",
        "S26 costs, menu, items cooked and walk-up sales are unknown. Everything about S26 profit is a scenario.",
        "S26 price schedule: 1 item = $7, 2 = $7, 3 = $11, 4 = $14 (once $15), 6 = $21, 28 = $100. Why is not known.",
        "One S26 order (28 items, $100) is about 27% of items and revenue. Plan for it separately next time.",
        "Participant names and contact details are omitted. Order IDs and timestamps remain; public pages display aggregates.",
    ]
    for i, t in enumerate(lines, start=3):
        c = ws.cell(i, 1, f"{i - 2}. {t}")
        c.alignment = WRAP
        ws.row_dimensions[i].height = 34
    ws.column_dimensions["A"].width = 120


def _instructions(wb):
    ws = wb.create_sheet("Instructions", 0)
    ws["A1"], ws["A1"].font = "AWAKE Fundraiser Planner: instructions", Font(bold=True, size=16)
    rows = [
        ("Purpose", "Evaluate a chosen production buffer and pricing assumptions. This workbook does not optimize quantity, forecast demand, or establish realized S26 profit."),
        ("Step 1", "Open Planner. Replace pre-order items and revenue with the current event's confirmed totals."),
        ("Step 2", "Update assumptions: buffer, sell-through, walk-up price, current unit cost, and fixed costs. S25 cost is only a proxy for another menu."),
        ("Step 3", "Read conditional revenue, cost, net and break-even. All cooked items incur cost. Fractional walk-up sales represent scenario averages."),
        ("Step 4", "Compare 0%, chosen and 100% walk-up sell-through. These vary sales only; cost overruns, cancellations and spoilage are outside the bounds."),
        ("Price reference", "Price Quote reproduces historical observed order amounts or a labeled fallback. It is not a validated current price list or price optimization."),
        ("After the event", "Record receipts, actual production, walk-up items sold, leftovers and volunteer hours. Compare plan with actuals before claiming improvement."),
        ("Colors", "BLUE: recorded or historically derived input. YELLOW: assumption. ORANGE: estimate. GREY: formula. Do not overwrite formulas."),
        ("Compatibility", "Open in Excel or import into Google Sheets and recalculate. Formula parity is tested in Python; native application behavior still needs a check."),
        ("Privacy", "Use order IDs only. Do not paste participants' names or contact details. Documentation contains the project author's name only."),
    ]
    for i, (k, v) in enumerate(rows, start=3):
        a = ws.cell(i, 1, k)
        a.font, a.alignment = BOLD, WRAP
        b = ws.cell(i, 2, v)
        b.alignment = WRAP
        ws.row_dimensions[i].height = 48
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 110
    # colour key cells
    for r, fill in ((10, BLUE),):
        ws.cell(r, 1).fill = fill


def build(path=None):
    a = config.values()
    res = analysis.run_all()
    wb = Workbook()
    _planner(wb, a)
    _quote(wb, a)
    _past(wb, a, res)
    _notes(wb)
    _instructions(wb)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    path = path or EXPORTS / "fundraiser_planner.xlsx"
    wb.save(path)
    return path


if __name__ == "__main__":
    print(build())
