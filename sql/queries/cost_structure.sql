-- Expense by category per event (positive numbers), unplanned included as its own category.
SELECT event_id,
       category,
       ROUND(-SUM(amount_usd), 2) AS cost_usd
FROM transactions
WHERE amount_usd < 0
GROUP BY event_id, category
ORDER BY event_id, category;
