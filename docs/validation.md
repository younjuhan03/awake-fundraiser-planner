# Revision validation — November 9, 2026

## Completed checks

- **79 pytest cases passed**, with no skips reported. Coverage includes all five Streamlit pages through Streamlit AppTest; planner totals, edge cases and finite-number validation; ledger and order reconciliation; privacy-pattern checks on repository text; and five Excel/Python formula-parity scenarios evaluated by the Python `formulas` library.
- **9 static-page calculator cases passed** through execution of the actual inline JavaScript in Node's VM with a small DOM stub. Cases cover the default plan, zero buffer, 0% and 100% sell-through, zero orders, inconsistent revenue, a zero walk-up price, non-finite values and a blank cost.
- **Full rebuild succeeded:** SQLite database, processed tables, seven figures and the spreadsheet were regenerated from the included records and defaults. All eight aggregate source-total checks matched.
- Static asset and document targets were checked for existence; external fonts, libraries and analytics are not required by the case-study page.

Commands:

```powershell
$env:PYTHONPATH="src"
python -m awake.build
python -m pytest -q
node tests/test_static_page.cjs
```

## Verification limits

- Browser preview access failed in this environment. The static page's visual layout, mobile rendering, keyboard interaction and browser download behavior were **not visually verified**. Responsive CSS, semantic labels, focus states and a reduced-motion rule are implemented, but implementation is not a substitute for a browser check.
- Streamlit AppTest establishes page execution without an exception; it is not a visual browser test.
- Excel parity was checked with a Python formula engine, not the native Excel or Google Sheets application. Live recalculation and visual layout in those applications remain unverified.
- The original screenshots were not provided in the source ZIP. Aggregate consistency does not establish that each transcribed row matches the originals.
- Tests do not validate the assumed cost transfer between menus, future sell-through or realized operational improvement.
- No public deployment or admissions submission was performed. Open `index.html` after extracting the ZIP; publish and test an externally accessible URL before using it in an application.
