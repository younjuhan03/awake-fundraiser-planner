"""Pure planning logic (no I/O, no pandas). All money in USD.

Model (deliberately simple; every step is a formula a leader can check by hand):
  production_qty   = ceil(preorder_units * (1 + walkup_buffer_pct))
  walkup_capacity  = production_qty - preorder_units
  walkup_units     = walkup_capacity * walkup_sellthrough_pct          (ESTIMATE)
  revenue          = preorder_revenue + walkup_units * walkup_price
  total_cost       = production_qty * unit_cost + fixed_costs          (every item cooked is paid for)
  net              = revenue - total_cost
Pre-orders are assumed to be fulfilled and paid (all 29 S26 orders confirmed payment).
Walk-up quantities are scenarios, not forecasts: no walk-up data exists.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Mapping, Optional


@dataclass(frozen=True)
class PlannerInputs:
    preorder_units: int
    preorder_revenue: float
    walkup_buffer_pct: float          # fraction, 0.10 = 10%
    walkup_sellthrough_pct: float     # fraction of buffer items sold to walk-ups
    walkup_price: float
    unit_cost: float
    fixed_costs: float = 0.0

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.preorder_units < 0 or int(self.preorder_units) != self.preorder_units:
            raise ValueError("preorder_units must be a non-negative integer")
        if self.preorder_revenue < 0:
            raise ValueError("preorder_revenue must be >= 0")
        if self.preorder_units == 0 and self.preorder_revenue > 0:
            raise ValueError("preorder_revenue > 0 with zero pre-order units")
        if self.walkup_buffer_pct < 0:
            raise ValueError("walkup_buffer_pct must be >= 0")
        if not 0 <= self.walkup_sellthrough_pct <= 1:
            raise ValueError("walkup_sellthrough_pct must be between 0 and 1")
        if self.walkup_price < 0 or self.unit_cost < 0 or self.fixed_costs < 0:
            raise ValueError("prices and costs must be >= 0")


@dataclass(frozen=True)
class PlannerResult:
    production_qty: int
    walkup_capacity: int
    walkup_units_sold: float
    leftover_units: float
    preorder_revenue: float
    walkup_revenue: float
    revenue: float
    variable_cost: float
    fixed_costs: float
    total_cost: float
    net: float
    margin: Optional[float]               # None when revenue == 0
    contribution_margin_walkup: float     # walkup_price - unit_cost
    breakeven_units_sold: Optional[int]   # total items that must be sold to net >= 0; None if unreachable
    breakeven_walkup_units: Optional[int]
    breakeven_reachable: bool             # break-even <= production_qty
    buffer_expected_to_pay: bool          # sellthrough * walkup_price > unit_cost


def production_quantity(preorder_units: int, buffer_pct: float) -> int:
    # round() guards against float noise such as 100 * 1.1 = 110.00000000000001
    return math.ceil(round(preorder_units * (1 + buffer_pct), 9))


def breakeven(inputs: PlannerInputs, production_qty: int):
    """Items that must be sold to cover total cost: pre-orders first (at their average price),
    then walk-ups at the walk-up price. Returns (total_units, walkup_units) or (None, None)."""
    total_cost = production_qty * inputs.unit_cost + inputs.fixed_costs
    if total_cost <= 1e-12:
        return 0, 0
    if inputs.preorder_revenue >= total_cost - 1e-12:
        avg = inputs.preorder_revenue / inputs.preorder_units
        return math.ceil(round(total_cost / avg, 9)), 0
    gap = total_cost - inputs.preorder_revenue
    if inputs.walkup_price <= 0:
        return None, None
    walkup = math.ceil(round(gap / inputs.walkup_price, 9))
    return inputs.preorder_units + walkup, walkup


def evaluate(inputs: PlannerInputs) -> PlannerResult:
    inputs.validate()
    q = production_quantity(inputs.preorder_units, inputs.walkup_buffer_pct)
    capacity = q - inputs.preorder_units
    sold = capacity * inputs.walkup_sellthrough_pct
    walkup_rev = sold * inputs.walkup_price
    revenue = inputs.preorder_revenue + walkup_rev
    variable = q * inputs.unit_cost
    total = variable + inputs.fixed_costs
    net = revenue - total
    be_total, be_walk = breakeven(inputs, q)
    return PlannerResult(
        production_qty=q,
        walkup_capacity=capacity,
        walkup_units_sold=sold,
        leftover_units=capacity - sold,
        preorder_revenue=inputs.preorder_revenue,
        walkup_revenue=walkup_rev,
        revenue=revenue,
        variable_cost=variable,
        fixed_costs=inputs.fixed_costs,
        total_cost=total,
        net=net,
        margin=(net / revenue) if revenue > 0 else None,
        contribution_margin_walkup=inputs.walkup_price - inputs.unit_cost,
        breakeven_units_sold=be_total,
        breakeven_walkup_units=be_walk,
        breakeven_reachable=(be_total is not None and be_total <= q),
        buffer_expected_to_pay=inputs.walkup_sellthrough_pct * inputs.walkup_price > inputs.unit_cost,
    )


def scenarios(inputs: PlannerInputs) -> dict:
    """Worst / expected / best = walk-up sell-through 0% / assumed / 100% (scenarios, not forecasts)."""
    return {
        "worst": evaluate(replace(inputs, walkup_sellthrough_pct=0.0)),
        "expected": evaluate(inputs),
        "best": evaluate(replace(inputs, walkup_sellthrough_pct=1.0)),
    }


def price_for_quantity(quantity: int, schedule: Mapping[int, float], fallback_per_item: float) -> float:
    """Quote an order: observed schedule if the quantity was seen, else fallback_per_item * quantity (ESTIMATE)."""
    if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity <= 0 or int(quantity) != quantity:
        raise ValueError("quantity must be a positive integer")
    if not math.isfinite(fallback_per_item) or fallback_per_item < 0:
        raise ValueError("fallback_per_item must be finite and non-negative")
    if quantity in schedule:
        return float(schedule[quantity])
    return round(quantity * fallback_per_item, 2)
