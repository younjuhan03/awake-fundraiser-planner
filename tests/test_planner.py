import math

import pytest

from awake import planner as p
from awake.planner import PlannerInputs


def base(**kw):
    d = dict(preorder_units=100, preorder_revenue=350.0, walkup_buffer_pct=0.10,
             walkup_sellthrough_pct=0.50, walkup_price=3.50, unit_cost=1.50, fixed_costs=20.0)
    d.update(kw)
    return PlannerInputs(**d)


def test_production_quantity_rounds_up_and_ignores_float_noise():
    assert p.production_quantity(100, 0.10) == 110      # 100*1.1 = 110.00000000000001 in floats
    assert p.production_quantity(104, 0.10) == 115      # 114.4 -> 115
    assert p.production_quantity(7, 0.0) == 7


def test_totals_reconcile():
    r = p.evaluate(base())
    assert r.production_qty == 110
    assert r.walkup_capacity == 10
    assert r.walkup_units_sold == 5
    assert r.leftover_units == 5
    assert r.revenue == pytest.approx(r.preorder_revenue + r.walkup_revenue)
    assert r.total_cost == pytest.approx(r.variable_cost + r.fixed_costs)
    assert r.net == pytest.approx(r.revenue - r.total_cost)
    assert r.revenue == pytest.approx(350 + 5 * 3.5)
    assert r.total_cost == pytest.approx(110 * 1.5 + 20)
    assert r.margin == pytest.approx(r.net / r.revenue)
    assert r.walkup_units_sold + r.leftover_units == r.walkup_capacity


def test_zero_buffer_means_preorders_only():
    r = p.evaluate(base(walkup_buffer_pct=0.0))
    assert r.production_qty == 100
    assert r.walkup_capacity == 0 and r.walkup_revenue == 0 and r.leftover_units == 0
    assert r.net == pytest.approx(350 - 100 * 1.5 - 20)
    # sell-through is irrelevant with no buffer
    assert p.evaluate(base(walkup_buffer_pct=0.0, walkup_sellthrough_pct=1.0)).net == pytest.approx(r.net)


def test_breakeven_covered_by_preorders():
    # cost = 100*1.5+20 = 170 < 350 pre-order revenue; avg price 3.5 -> ceil(170/3.5) = 49 items
    r = p.evaluate(base(walkup_buffer_pct=0.0))
    assert r.breakeven_units_sold == math.ceil(170 / 3.5) == 49
    assert r.breakeven_walkup_units == 0
    assert r.breakeven_reachable


def test_breakeven_needs_walkups_but_exceeds_capacity():
    # cost = 110*4 = 440 ; pre-orders 350 ; gap 90 ; 90/3.5 = 25.7 -> 26 walk-ups, capacity is only 10
    r = p.evaluate(base(unit_cost=4.0, fixed_costs=0.0))
    assert r.breakeven_walkup_units == 26
    assert r.breakeven_units_sold == 126
    assert not r.breakeven_reachable


def test_breakeven_gap_math_is_ceiling():
    inputs = base(unit_cost=4.0, fixed_costs=0.0, walkup_buffer_pct=0.5)
    total, walk = p.breakeven(inputs, 150)
    assert walk == math.ceil((150 * 4.0 - 350) / 3.5) == 72
    assert total == 172
    # selling that many walk-ups covers cost; one fewer does not
    assert 350 + walk * 3.5 >= 150 * 4.0
    assert 350 + (walk - 1) * 3.5 < 150 * 4.0


def test_breakeven_unreachable_when_walkup_price_zero():
    r = p.evaluate(base(walkup_price=0.0, unit_cost=4.0))
    assert r.breakeven_units_sold is None and r.breakeven_walkup_units is None
    assert not r.breakeven_reachable


def test_price_below_cost_flags_buffer_as_losing():
    r = p.evaluate(base(walkup_price=1.0, unit_cost=1.5, walkup_sellthrough_pct=1.0))
    assert r.contribution_margin_walkup < 0
    assert not r.buffer_expected_to_pay
    assert r.net < p.evaluate(base(walkup_price=1.0, unit_cost=1.5, walkup_buffer_pct=0.0)).net


def test_buffer_pays_only_above_cost_over_price_sellthrough():
    # unit cost 1.75 / price 3.5 = 50% threshold
    assert not p.evaluate(base(unit_cost=1.75, walkup_sellthrough_pct=0.50)).buffer_expected_to_pay
    assert p.evaluate(base(unit_cost=1.75, walkup_sellthrough_pct=0.51)).buffer_expected_to_pay


def test_scenarios_ordering_and_definition():
    s = p.scenarios(base())
    assert s["worst"].walkup_units_sold == 0
    assert s["best"].walkup_units_sold == s["best"].walkup_capacity
    assert s["worst"].net <= s["expected"].net <= s["best"].net
    assert s["expected"] == p.evaluate(base())
    # worst case = pre-order revenue minus full cost
    assert s["worst"].net == pytest.approx(350 - s["worst"].total_cost)


def test_edge_case_zero_everything():
    r = p.evaluate(PlannerInputs(0, 0.0, 0.1, 0.5, 3.5, 1.5, 0.0))
    assert r.production_qty == 0 and r.revenue == 0 and r.net == 0
    assert r.margin is None
    assert r.breakeven_units_sold == 0


def test_zero_cost_has_zero_breakeven():
    r = p.evaluate(base(unit_cost=0.0, fixed_costs=0.0))
    assert r.breakeven_units_sold == 0 and r.net == pytest.approx(r.revenue)


def test_fixed_costs_only_with_no_preorders():
    r = p.evaluate(PlannerInputs(0, 0.0, 0.0, 0.0, 3.5, 1.5, 40.0))
    assert r.net == -40.0
    assert r.breakeven_walkup_units == math.ceil(40 / 3.5)
    assert not r.breakeven_reachable   # nothing was produced to sell


@pytest.mark.parametrize("kw", [
    dict(preorder_units=-1), dict(preorder_units=2.5), dict(preorder_revenue=-1.0),
    dict(walkup_buffer_pct=-0.1), dict(walkup_sellthrough_pct=1.1), dict(walkup_sellthrough_pct=-0.1),
    dict(walkup_price=-1.0), dict(unit_cost=-0.01), dict(fixed_costs=-5.0),
    dict(preorder_units=0, preorder_revenue=10.0),
])
def test_invalid_inputs_raise(kw):
    with pytest.raises(ValueError):
        p.evaluate(base(**kw))


def test_price_for_quantity_observed_and_fallback():
    sched = {1: 7, 2: 7, 3: 11, 4: 14, 6: 21, 28: 100}
    assert p.price_for_quantity(3, sched, 3.5) == 11.0
    assert p.price_for_quantity(5, sched, 3.5) == 17.5      # not observed -> fallback estimate
    assert p.price_for_quantity(28, sched, 3.5) == 100.0
    with pytest.raises(ValueError):
        p.price_for_quantity(0, sched, 3.5)


@pytest.mark.parametrize("field", list(PlannerInputs.__dataclass_fields__))
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_inputs_rejected(field, value):
    with pytest.raises(ValueError, match="finite"):
        p.evaluate(base(**{field: value}))


def test_incremental_buffer_profit_equals_sales_less_extra_cost():
    inputs = base()
    with_buffer = p.evaluate(inputs)
    without_buffer = p.evaluate(base(walkup_buffer_pct=0))
    assert with_buffer.net - without_buffer.net == pytest.approx(
        with_buffer.walkup_capacity * (inputs.walkup_sellthrough_pct * inputs.walkup_price - inputs.unit_cost))


@pytest.mark.parametrize("quantity", [1.5, float("nan"), float("inf"), True])
def test_price_quote_rejects_invalid_item_counts(quantity):
    with pytest.raises(ValueError):
        p.price_for_quantity(quantity, {}, 3.5)
