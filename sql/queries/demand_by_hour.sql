-- Hour of day (timestamps as recorded; timezone unknown).
SELECT CAST(substr(timestamp, 12, 2) AS INTEGER) AS hour,
       COUNT(*)                                   AS n_orders,
       SUM(quantity)                              AS units
FROM orders
WHERE event_id = 'S26'
GROUP BY hour
ORDER BY hour;
