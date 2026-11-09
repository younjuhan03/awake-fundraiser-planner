# From pre-orders to a defensible production plan

**Juhan Youn · AWAKE Fundraiser Planner · Applied analytics case study**

## Context and role

AWAKE's food fundraisers required leaders to commit money and volunteer effort before knowing walk-up demand. As Finance/Social Leader, I introduced online pre-orders with day-of pickup to improve production planning. Later leaders continued the pre-order process after I left.

I developed this planner after introducing the pre-order process. My goal was to turn the records into a transparent comparison of production choices, with each conclusion tied to either recorded data or an explicit assumption.

## Evidence and method

The data comprise two events with financial records, a planning memo with an unconfirmed semester, and 29 Spring 2026 pre-orders. Hand-transcribed CSVs and SQLite queries reconcile totals before examining unit economics, concentration and production scenarios. Participant names and contact details were omitted.

Fall 2024's memo reports $261.13 net, while its transactions yield $234.54. The $26.59 difference remains unresolved. The transaction-based result is primary, with the alternative including a separately classified parking fine disclosed. Aggregate agreement does not independently validate every transcribed row.

Two costed events do not support a credible demand model. Instead, the planner exposes assumptions and evaluates their consequences. It charges for every item produced, rounds production up to whole items and compares a chosen buffer with producing only pre-orders. Streamlit and an Excel handoff expose the inputs and calculations.

## Decision insight

Spring 2026 recorded 104 pre-ordered items and $375 revenue. Using the previous event's $190 / 108 cost per purchased item as a proxy and an assumed $3.50 walk-up price, an extra item requires about 50.3% sell-through to break even.

A 10% buffer produces 115 items, 11 beyond pre-orders. At chosen 50% sell-through, those extras reduce net by about $0.10 relative to producing exactly 104. With zero walk-up sales, the loss is about $19.35; if all 11 sell, the gain is about $19.15. These are conditional calculations, not forecasts. Transferring another menu's cost to Spring 2026 is an assumption.

Leaders should verify current unit costs, preparation capacity and acceptable downside before producing beyond confirmed orders. The tool does not establish an optimal price or quantity. A single order accounts for 26.9% of units, making large-order fulfillment another useful check before purchasing.

## What remains unproven

S26 costs, production, walk-up sales and leftovers are not recorded. The project cannot report realized profit, quantify waste reduction or establish that pre-orders caused better outcomes. The approximate $101–$294 net range across cost cases is a scenario comparison, not an observed result or confidence interval.

Next validation: record actual costs, production, fulfillment, walk-up sales, leftovers and preparation hours, then compare a plan registered before the event with realized outcomes. Measuring improvement also requires a comparable baseline and attention to menu and event differences.

## Reflection

The most useful output was a decision threshold and a clearer measurement plan. This experience connects my economics and statistics background to a question I want to study more deeply: how to turn imperfect analytical evidence into decisions under operational constraints, then evaluate whether those decisions improved the outcome.

[Methods, source notes and development details](../README.md).
