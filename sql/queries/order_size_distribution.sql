SELECT quantity,
       COUNT(*)                   AS n_orders,
       SUM(quantity)              AS units,
       SUM(amount_usd)            AS revenue_usd
FROM orders
WHERE event_id = 'S26'
GROUP BY quantity
ORDER BY quantity;
