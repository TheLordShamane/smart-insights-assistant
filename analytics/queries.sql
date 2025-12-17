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
SELECT p.product_id, p.name, p.category, SUM(oi.quantity * oi.unit_price) AS revenue
FROM products p
JOIN order_items oi ON oi.product_id = p.product_id
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_date >= now() - INTERVAL '90 days'
GROUP BY p.product_id, p.name, p.category
ORDER BY revenue DESC
LIMIT 5;


-- Example: Monthly revenue trend (last 12 months)
SELECT date_trunc('month', o.order_date) AS month,
SUM(o.total_amount) AS revenue
FROM orders o
WHERE o.order_date >= date_trunc('month', now()) - INTERVAL '12 months'
GROUP BY 1
ORDER BY 1;