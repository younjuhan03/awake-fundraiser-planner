-- Observed (quantity -> amount) pairs. Several amounts for one quantity = inconsistency (flagged in Python).
SELECT quantity,
       amount_usd,
       COUNT(*) AS n_orders
FROM orders
WHERE event_id = 'S26'
GROUP BY quantity, amount_usd
ORDER BY quantity, n_orders DESC;
