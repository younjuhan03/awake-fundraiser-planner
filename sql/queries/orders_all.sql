SELECT order_id, timestamp, quantity, amount_usd,
       ROUND(amount_usd * 1.0 / quantity, 4) AS price_per_unit_usd
FROM orders
WHERE event_id = 'S26'
ORDER BY timestamp;
