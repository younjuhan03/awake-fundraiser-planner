# Detailed methods and reproduction

I keep the full calculation notes, earlier results and local setup here. The [project README](../README.md) summarizes my current conclusion.

# AWAKE Fundraiser Planner

**From pre-orders to a defensible production plan.** My analysis uses actual student organization records.

## Start here

- Open **[index.html](../index.html)** for the case study and interactive calculator. No installation or internet connection is required.
- Read **[the case study](../docs/case_study.md)** for the role, method, conclusions and limits.
- Use **[the spreadsheet](../exports/fundraiser_planner.xlsx)** for formula-based planning.
- Run **Streamlit** for historical event P&L, demand, the planner and data notes.

## Context and ownership

As AWAKE's Finance/Social Leader, I introduced online pre-orders with day-of pickup to make food production easier to plan. Subsequent leaders continued the pre-order process after I left.

This later, retrospective project adds a planning tool using three semesters of records. The operational change and this newly built tool are distinct. Continued use of pre-orders does not establish adoption of this app. Recorded production and leftovers are missing, so the available data cannot quantify waste reduction or establish causal profit improvement.


## Main decision

At a historical cost proxy of $190 / 108 items purchased and an assumed $3.50 walk-up price, an extra item requires **50.3% sell-through** to break even. Applying an earlier menu's cost to S26 is an assumption.

A 10% buffer on 104 pre-orders rounds production up to 115: **11 extra items**. Relative to producing exactly 104:

| Buffer sell-through | Incremental net (scenario) |
|---|---:|
| 0% | -$19.35 |
| 50% chosen input | -$0.10 |
| 100% | +$19.15 |

Start from confirmed orders; choose a buffer after checking current costs, capacity and acceptable downside. The tool evaluates a chosen buffer. It does not optimize quantity or price, or forecast demand.

## Evidence

| Source | Result | Status |
|---|---|---|
| F24 transactions | $496 revenue, $261.46 fundraiser cost, $234.54 net | Revenue/cost observed; net derived |
| S25 transactions | $372 revenue, $190 cost, $182 net | Revenue/cost observed; net derived |
| S26 order form | 29 orders, 104 items, $375 | Observed; costs and actual production unknown |
| Largest S26 order | 28 items, $100; 26.9% of units, 26.7% of revenue | Derived |
| S26 profit | About $101–$294 if exactly 104 were cooked, across four cost cases | Scenario range, not realized profit or confidence interval |

F24's memo reports $261.13 net, leaving an unresolved $26.59 difference. The primary result uses the transactions. Including a separately classified $75 parking fine reduces net to $159.54. See [data_issues.md](../data_issues.md).

## Sources and privacy

| Source | Included files |
|---|---|
| 2024–25 account book, 16 transactions and budget table | `data/raw/transactions.csv`, `ledger_budget.csv` |
| Planning memo, semester unconfirmed | `unit_costs.csv`, `brookie_ingredients.csv` |
| S26 pre-orders | `data/raw/orders.csv` |

The original screenshots are not included. Hand-transcribed CSV totals are internally checked, not independently audited row by row. Participant names and contact details are omitted. Pseudonymous IDs, timestamps and amounts remain, so the raw order file is not guaranteed anonymous against outside information. The case study displays aggregates; its narrative names only the project author.

## Method

CSV → SQLite and named SQL queries → reconciliation, P&L, concentration and timing → pure Python scenario evaluation → Streamlit, figures and Excel.

- Production = `ceil(preorder_units * (1 + buffer))`, guarding against floating-point noise.
- Extra quantity = production − pre-orders.
- Scenario walk-up sales = extra quantity × chosen sell-through. Fractions are scenario averages.
- Revenue = pre-order revenue + scenario walk-up sales × assumed walk-up price.
- Cost = production × unit cost + fixed costs. Every cooked item incurs cost.
- Net = revenue − cost.
- Incremental buffer net = extra quantity × (sell-through × walk-up price − unit cost).
- Extra-item break-even sell-through = unit cost / walk-up price, when price is positive.
- Total cost break-even counts pre-orders at their average price first, then walk-ups. This is an accounting threshold at a fixed production quantity, not payment timing.

The 0% / chosen / 100% cases vary walk-up sales only. They do not bound cost overruns, cancellations or spoilage, and have no estimated probabilities. Internal keys such as `expected` and `net_buffer_expected` are retained for compatibility and mean **the user-chosen scenario**, not statistical expected value.

S25 unit cost uses items **purchased**, not sold. Memo cases add an assumed $0.39 supplies allowance to $0.39 or $0.60 ingredients; menu and semester are unconfirmed. The 1.5× stress test is a judgment call. Even zero-buffer S26 net depends on assumed cost. Avoid double-counting supplies already included in all-in unit cost.

## Run locally

From this directory, in PowerShell (Python 3.12+ intended):

```powershell
pip install -r requirements.txt
$env:PYTHONPATH="src"
python -m awake.build
python -m pytest -q
streamlit run app.py
```

On Bash, use `export PYTHONPATH=src`. The static `index.html` opens directly; optional serving: `python -m http.server 8765`.

The build recreates SQLite, CSV/JSON tables, figures and the spreadsheet. Missing spreadsheet dependencies fail explicitly instead of silently retaining an old export. See [validation.md](../docs/validation.md) for checks and limits.

## Limitations and next validation

Two costed events and one pre-order event do not support a reliable demand model. Menus and semesters differ, so they are not a comparable causal before/after design. Price anomalies are preserved. The single average unit cost assumes linear, interchangeable items: recipe batches, menu mix, capacity and discounts are not modeled.

Next event: record costs, actual production, fulfillment, walk-up sales/revenue, leftovers and preparation hours. Register the plan before the event and compare with actuals before claiming impact. Data collection is proposed, not completed.

## Project map

| Location | Purpose |
|---|---|
| `index.html` | Case study + browser calculator |
| `app.py` | Streamlit overview and analytical pages |
| `src/awake/` | Planner, analysis, figures, spreadsheet generator, build |
| `config/assumptions.yaml` | Defaults with provenance |
| `data/raw/`, `sql/` | Transcribed records, schema and queries |
| `docs/` | Case study, review, figures and validation |
| `tests/` | Data, planner, Streamlit and formula checks |

I keep my interpretation and analytical decisions in [my decision log](../docs/SUBMISSION_NOTES_KO.md).
