-- =====================================================
-- Data Exploration: หาความผิดปกติในข้อมูลดิบ
-- =====================================================

-- [1] จำนวนแถวแต่ละ view
SELECT 'customers' AS source, COUNT(*) AS row_count FROM vw_raw_customers
UNION ALL SELECT 'orders',   COUNT(*) FROM vw_raw_orders
UNION ALL SELECT 'fx_rates', COUNT(*) FROM vw_exchange_rates;

-- [2] ลูกค้าซ้ำ (customer_id เดียวกันมากกว่า 1 แถว)
SELECT customer_id, COUNT(*) AS dup_count, GROUP_CONCAT(signup_date) AS signup_dates
FROM vw_raw_customers
GROUP BY customer_id
HAVING COUNT(*) > 1;

-- [3] ค่าที่หายไปในตารางลูกค้า
SELECT COUNT(*) AS total,
       SUM(CASE WHEN email IS NULL OR TRIM(email)='' THEN 1 ELSE 0 END) AS missing_email,
       SUM(CASE WHEN phone IS NULL OR TRIM(phone)='' THEN 1 ELSE 0 END) AS missing_phone
FROM vw_raw_customers;

-- [4] เบอร์โทรที่มีตัวอักษรปน
SELECT customer_id, full_name, phone
FROM vw_raw_customers
WHERE phone GLOB '*[A-Za-z]*';

-- [5] Order ที่ยอดเงินไม่ถูกต้อง
SELECT order_id, customer_id, total_amount, currency, status
FROM vw_raw_orders
WHERE total_amount IS NULL OR total_amount <= 0;

-- [6] สรุปสถานะ order
SELECT status, COUNT(*) AS cnt, ROUND(SUM(total_amount),2) AS total
FROM vw_raw_orders GROUP BY status ORDER BY cnt DESC;

-- [7] Order ที่ currency หรือ order_date เป็น NULL
SELECT SUM(CASE WHEN currency   IS NULL THEN 1 ELSE 0 END) AS null_currency,
       SUM(CASE WHEN order_date IS NULL THEN 1 ELSE 0 END) AS null_order_date
FROM vw_raw_orders;

-- [8] Order ที่หา exchange rate ไม่เจอ
SELECT o.currency, COUNT(*) AS orders_without_rate
FROM vw_raw_orders o
LEFT JOIN vw_exchange_rates r
       ON r.currency = o.currency AND DATE(r.date) = DATE(o.order_date)
WHERE r.rate_to_usd IS NULL AND o.currency IS NOT NULL
GROUP BY o.currency;

-- [9] ช่วงวันที่ orders vs fx_rates
SELECT 'orders' AS ds, MIN(order_date) AS min_date, MAX(order_date) AS max_date FROM vw_raw_orders
UNION ALL
SELECT 'fx_rates', MIN(date), MAX(date) FROM vw_exchange_rates;

-- [10] Orphan orders (customer_id ไม่มีในตารางลูกค้า)
SELECT o.order_id, o.customer_id
FROM vw_raw_orders o
LEFT JOIN vw_raw_customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;