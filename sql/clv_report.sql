-- =====================================================
-- Customer Lifetime Value (CLV) Report
-- Source: analytics.db (dim_customers, fct_orders)
-- นิยาม: ผลรวมมูลค่า order ที่ COMPLETED ของลูกค้าแต่ละราย (USD)
-- =====================================================

SELECT
    c.customer_id,
    c.full_name,
    c.email,
    COUNT(o.order_id)                             AS total_orders,
    ROUND(SUM(o.amount_usd), 2)                   AS lifetime_value_usd,
    ROUND(AVG(o.amount_usd), 2)                   AS avg_order_value_usd,
    MIN(DATE(o.order_date))                       AS first_order_date,
    MAX(DATE(o.order_date))                       AS last_order_date
FROM dim_customers AS c
INNER JOIN fct_orders AS o
        ON o.customer_id = c.customer_id
WHERE UPPER(TRIM(o.status)) = 'COMPLETED'
GROUP BY c.customer_id, c.full_name, c.email
ORDER BY lifetime_value_usd DESC;