-- Observed event P&L. cost excludes 'unplanned' (parking fine); it is reported separately.
SELECT e.event_id,
       e.label,
       e.status,
       e.ledger_memo_net_usd,
       ROUND(COALESCE(SUM(CASE WHEN t.category = 'revenue' THEN t.amount_usd END), 0), 2)            AS revenue_usd,
       ROUND(-COALESCE(SUM(CASE WHEN t.amount_usd < 0 AND t.category <> 'unplanned'
                                THEN t.amount_usd END), 0), 2)                                       AS cost_usd,
       ROUND(-COALESCE(SUM(CASE WHEN t.category = 'unplanned' THEN t.amount_usd END), 0), 2)         AS unplanned_usd,
       COALESCE(SUM(t.units_purchased), 0)                                                           AS units_purchased
FROM events e
LEFT JOIN transactions t ON t.event_id = e.event_id
GROUP BY e.event_id
ORDER BY e.event_id;
