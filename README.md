# AWAKE Fundraiser Planner
### How much extra food should I make beyond confirmed pre-orders?

**My finding:** under a historical cost proxy and an assumed $3.50 walk-up price, an extra item needs about 50.3% sell-through to cover its cost. At 50% sell-through, a 10% production buffer adds almost no net proceeds.

As AWAKE's Finance/Social Leader, I introduced online pre-orders with day-of pickup to make food production easier to plan. Subsequent leaders continued that process after I left. I later used the available financial and order records to develop a reusable scenario planner.

**Explore:** [interactive case study](index.html) · [spreadsheet planner](exports/fundraiser_planner.xlsx) · [my analysis](docs/case_study.md) · [calculation notes](docs/technical_notes.md)

## My project in plain English

I turned my experience organizing student food fundraisers into a planning question: **after I know my pre-orders, is making extra food worth the risk of leftovers?**

- **What I built:** I connected the available order and financial records to a Python scenario model, a local app and an Excel planner.
- **How I evaluated it:** I compared producing only confirmed orders with producing extra items, then varied the fraction of extra items sold.
- **What I learned:** I found that selling half the extra items would roughly break even under my cost and price assumptions. I cannot treat a larger production buffer as an automatic increase in proceeds.

I use **sell-through** to mean the fraction of extra items sold. I distinguish my earlier introduction of pre-orders from my later analytical planner.

## The production decision

Spring 2026 recorded **29 pre-orders, 104 items and $375 revenue**. A 10% buffer rounds production up to 115 items, leaving 11 extra items to sell.

| Assumed extra-item sell-through | Net change vs. producing only pre-orders |
|---|---:|
| 0% | -$19.35 |
| 50% | -$0.10 |
| 100% | +$19.15 |

I use the S25 cost of $190 / 108 purchased items as a proxy. Applying that earlier menu's cost to S26 and choosing a $3.50 walk-up price are assumptions. These figures evaluate a plan; they are not observed S26 profit or a demand forecast.

## My analytical decisions

- **Start with committed demand.** I compare each buffer with producing exactly the confirmed pre-orders, so the extra quantity's cost and upside remain visible.
- **Charge for everything produced.** An unsold item still incurs cost. I use `extra quantity × (sell-through × price − unit cost)` to explain the buffer's incremental value.
- **Reconcile before interpreting.** F24 transactions yield $234.54 net while the memo reports $261.13. I retain the unresolved $26.59 difference and use the reproducible transaction total as my primary figure.
- **Match the method to the evidence.** With only two costed events and one pre-order event, I use scenarios rather than fit a demand model that the records cannot support.

## What I learned and want to deepen

Working back through the fundraiser records helped me connect a familiar operating problem to a production model. I could calculate when extra items would break even, yet I lacked the walk-up sales and leftover records needed to estimate demand. Better demand estimation is the next skill I want to develop here, supported by consistent event-level recordkeeping.

## My next validation step

At a future event, I would record production, actual unit costs, walk-up sales and leftovers, then compare my scenario assumptions with the observed outcome.

## Methods and records

My workflow connects transcribed CSVs, SQLite reconciliation, Python scenario calculations, sensitivity checks, Streamlit and Excel.

- [Source notes and unresolved issues](data_issues.md)
- [Methods, formulas and local setup](docs/technical_notes.md)
- [My analytical decision log](docs/SUBMISSION_NOTES_KO.md)
- [Software validation](docs/validation.md) · [leader handoff](docs/leader_brief.md)

Participant names and contact details are omitted. The public order file retains pseudonymous IDs, timestamps and amounts; the case study displays aggregates.

## Boundaries of my conclusion

Historical production, leftovers, walk-up sales and S26 costs are missing. I cannot calculate a recorded waste-reduction rate or realized S26 profit. The pre-order process and the later planner are separate developments; I have not measured an operational impact from deploying the planner. Its 0%, chosen and 100% sell-through cases hold costs and pre-order fulfillment fixed.

The HTML page opens after downloading; GitHub displays its source. The spreadsheet and full local app provide additional ways to inspect the calculations.

## AI-assisted development

I used AI tools to support project development, including code and documentation. I take responsibility for the analytical choices and interpretations presented here, and I document the data, comparisons, assumptions and limitations behind my conclusions. I distinguish AI assistance during development from the models I actually implement; I describe those models in the methods rather than imply that I built an LLM-based system.
