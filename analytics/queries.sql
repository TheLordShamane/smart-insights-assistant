-- 1. Top 5 products by revenue in the last quarter
-- 2. Monthly revenue trend (last 12 months)
-- 3. Repeat purchase rate (customers with >1 order)
-- 4. Average order value by customer segment (premium vs non-premium)
-- 5. Top 10 customers by lifetime value
-- 6. Sales by country
-- 7. Distribution of order sizes (items per order)
-- 8. Products with highest return rate (if we had returns)
-- 9. Average delivery time by carrier
-- 10. Support tickets per month and resolution time
-- 11. Correlation: average delivery delay vs negative support tickets
-- 12. Cohort analysis: retention by signup month
-- 13. Inventory exposure: products with low sales but high stock (later)
-- 14. Sales seasonality by category
-- 15. Top products with increasing momentum (MoM growth)
-- 16. SQL to produce a weekly summary table
-- 17. Window function example: running total of revenue
-- 18. Query to generate a features table for ML: customer-level features
-- 19. Query to join RAG results: example pattern (pseudocode)
-- 20. Query to extract top keywords from support_tickets (basic)


-- Example implementation: Top 5 products by revenue last 90 days
SELECT p.product_id, p.name AS product_name, SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_date >= now() - INTERVAL '90 days'
GROUP BY p.product_id, p.name
ORDER BY revenue DESC
LIMIT 5;

-- Example: Monthly revenue trend (last 12 months)
SELECT date_trunc('month', o.order_date) AS month,
SUM(o.total_amount) AS revenue
FROM orders o
WHERE o.order_date >= date_trunc('month', now()) - INTERVAL '12 months'
GROUP BY 1
ORDER BY 1;

-- Repeat Purchase Rate
SELECT COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_id END) * 1.0 / COUNT(DISTINCT customer_id) AS repeat_purchase_rate
FROM (
    SELECT customer_id, COUNT(order_id) AS order_count
    FROM orders
    GROUP BY customer_id
) subquery;

-- Average Order Value by Customer Segment
SELECT c.is_premium, AVG(o.total_amount) AS avg_order_value
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.is_premium;

-- Top 10 Customers by Lifetime Value
SELECT c.customer_id, c.customer_name, SUM(o.total_amount) AS lifetime_value
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY lifetime_value DESC
LIMIT 10;

-- Sales by Country
SELECT c.country, SUM(o.total_amount) AS total_sales
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.country;

-- Distribution of Order Sizes
SELECT o.order_id, COUNT(oi.product_id) AS items_per_order
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY o.order_id;

-- Average Delivery Time by Carrier
SELECT dl.carrier, AVG(EXTRACT(EPOCH FROM (dl.delivered_at - dl.shipped_at))/3600) AS avg_delivery_time_hours
FROM delivery_logs dl
WHERE dl.delivered_at IS NOT NULL AND dl.shipped_at IS NOT NULL
GROUP BY dl.carrier;

-- Support Tickets per Month and Resolution Time
SELECT date_trunc('month', st.created_at) AS month,
COUNT(st.ticket_id) AS ticket_count,
AVG(EXTRACT(EPOCH FROM (st.resolved_at - st.created_at))/3600) AS avg_resolution_time_hours
FROM support_tickets st
WHERE st.created_at IS NOT NULL
GROUP BY month
ORDER BY month;

-- Correlation: Average Delivery Delay vs Negative Support Tickets
WITH delivery_delays AS (
    SELECT dl.order_id, EXTRACT(EPOCH FROM (dl.delivered_at - dl.shipped_at))/3600 AS delivery_delay_hours
    FROM delivery_logs dl
    WHERE dl.delivered_at IS NOT NULL AND dl.shipped_at IS NOT NULL
), negative_tickets AS (
    SELECT st.customer_id, COUNT(st.ticket_id) AS negative_ticket_count
    FROM support_tickets st
    WHERE st.subject ILIKE '%complaint%' OR st.body ILIKE '%bad%'
    GROUP BY st.customer_id
)
SELECT AVG(dd.delivery_delay_hours) AS avg_delivery_delay, AVG(nt.negative_ticket_count) AS avg_negative_tickets
FROM delivery_delays dd
JOIN negative_tickets nt ON dd.order_id = nt.customer_id;

-- Cohort Analysis: Retention by Signup Month
WITH cohorts AS (
    SELECT c.customer_id, date_trunc('month', c.signup_date) AS signup_month
    FROM customers c
), orders_by_cohort AS (
    SELECT co.signup_month, date_trunc('month', o.order_date) AS order_month, COUNT(DISTINCT o.customer_id) AS active_customers
    FROM cohorts co
    JOIN orders o ON o.customer_id = co.customer_id
    GROUP BY co.signup_month, order_month
) 
SELECT signup_month, order_month,
       COUNT(active_customers) AS active_customers
FROM orders_by_cohort
GROUP BY signup_month, order_month
ORDER BY signup_month, order_month;

-- Sales Seasonality by Category
SELECT p.category, date_trunc('month', o.order_date) AS month,
SUM(oi.quantity * oi.unit_price) AS monthly_sales
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
GROUP BY p.category, month
ORDER BY p.category, month;

-- Top Products with Increasing Momentum (MoM Growth)
WITH monthly_sales AS (
    SELECT p.product_id, date_trunc('month', o.order_date) AS month,
    SUM(oi.quantity * oi.unit_price) AS sales
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    JOIN orders o ON o.order_id = oi.order_id
    GROUP BY p.product_id, month
), sales_growth AS (
    SELECT product_id, month, sales,
    LAG(sales) OVER (PARTITION BY product_id ORDER BY month) AS previous_month_sales
    FROM monthly_sales
)
SELECT product_id, month,
       (sales - previous_month_sales) / NULLIF(previous_month_sales, 0) AS mom_growth
FROM sales_growth
WHERE previous_month_sales IS NOT NULL
ORDER BY mom_growth DESC
LIMIT 10;

-- Window Function Example: Running Total of Revenue
SELECT o.order_date,
       SUM(o.total_amount) OVER (ORDER BY o.order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total_revenue
FROM orders o
ORDER BY o.order_date;

-- Query to generate a features table for ML: customer-level features
SELECT c.customer_id,
       COUNT(o.order_id) AS total_orders,
       SUM(o.total_amount) AS total_spent,
       AVG(o.total_amount) AS avg_order_value,
       MAX(o.order_date) AS last_order_date,
       c.is_premium
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.is_premium;

-- Query to extract top keywords from support_tickets (basic)
SELECT unnest(string_to_array(lower(st.subject || ' ' || st.body), ' ')) AS keyword,
       COUNT(*) AS frequency
FROM support_tickets st
GROUP BY keyword
ORDER BY frequency DESC
LIMIT 20;

-- SQL to produce a weekly summary table
CREATE TABLE weekly_summary AS
SELECT date_trunc('week', o.order_date) AS week,
       COUNT(o.order_id) AS total_orders,
       SUM(o.total_amount) AS total_revenue
FROM orders o
GROUP BY week
ORDER BY week;

-- Query to join RAG results: example pattern (pseudocode)
-- Assuming we have a table rag_results with columns: customer_id, rag_score