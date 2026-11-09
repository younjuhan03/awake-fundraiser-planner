"""The spreadsheet must agree with the Python planner. Uses the `formulas` package to evaluate cells
(skipped if it is not installed); structure checks run regardless."""
import pytest
from openpyxl import load_workbook

from awake import analysis as an, planner, xlsx


@pytest.fixture(scope="module")
def path(tmp_path_factory):
    return xlsx.build(tmp_path_factory.mktemp("x") / "planner.xlsx")


def test_structure(path):
    wb = load_workbook(path)
    assert wb.sheetnames[0] == "Instructions"
    assert {"Planner", "Price Quote", "Past Events", "Data Notes"} <= set(wb.sheetnames)
    ws = wb["Planner"]
    formulas = [c for row in ws["B15:B29"] for c in row if isinstance(c.value, str) and c.value.startswith("=")]
    assert len(formulas) == 15            # every output is a live formula
    assert ws["B5"].value == 104 and ws["B6"].value == 375


def _calc(path, overrides):
    formulas = pytest.importorskip("formulas")
    wb = load_workbook(path)
    for cell, v in overrides.items():
        wb["Planner"][cell] = v
    tmp = path.with_name("calc_input.xlsx")
    wb.save(tmp)
    model = formulas.ExcelModel().loads(str(tmp)).finish()
    sol = model.calculate()
    out = {}
    for key, val in sol.items():
        k = str(key).upper()
        if "PLANNER'!" in k and ":" not in k.split("!")[-1]:
            cell = k.split("!")[-1]
            v = val.value[0, 0]
            out[cell] = v
    return out


@pytest.mark.parametrize("case", [
    {},                                                         # defaults: S26 pre-orders + S25 cost
    {"B7": 0.0},                                                # zero buffer
    {"B7": 0.2, "B8": 1.0, "B10": 0.78, "B11": 25},             # memo-like cost + fixed costs
    {"B10": 4.0, "B7": 0.5},                                    # break-even needs walk-ups
    {"B9": 0},                                                  # no walk-up price
])
def test_spreadsheet_matches_python(path, case):
    cells = _calc(path, case)
    inp = dict(B5=104, B6=375.0, B7=0.10, B8=0.50, B9=3.50, B10=190 / 108, B11=0.0)
    inp.update(case)
    r = planner.evaluate(planner.PlannerInputs(
        preorder_units=inp["B5"], preorder_revenue=inp["B6"], walkup_buffer_pct=inp["B7"],
        walkup_sellthrough_pct=inp["B8"], walkup_price=inp["B9"], unit_cost=inp["B10"], fixed_costs=inp["B11"]))
    g = lambda c: cells[c]  # noqa: E731
    assert g("B15") == r.production_qty
    assert g("B21") == pytest.approx(r.revenue)
    assert g("B22") == pytest.approx(r.total_cost)
    assert g("B23") == pytest.approx(r.net)
    if r.breakeven_units_sold is None:
        assert g("B25") == "not reachable"
    else:
        assert g("B25") == r.breakeven_units_sold
        assert g("B26") == r.breakeven_walkup_units
    assert str(g("B27")).startswith("Yes") == r.breakeven_reachable
    assert str(g("B28")).startswith("Yes") == r.buffer_expected_to_pay
    sc = planner.scenarios(planner.PlannerInputs(inp["B5"], inp["B6"], inp["B7"], inp["B8"], inp["B9"], inp["B10"], inp["B11"]))
    assert g("F33") == pytest.approx(sc["worst"].net)
    assert g("F34") == pytest.approx(sc["expected"].net)
    assert g("F35") == pytest.approx(sc["best"].net)
