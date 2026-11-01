-- Connect to data/retail.duckdb. Money: PEN; one fact row = one order.
-- Slice / dice
SELECT city, category, sum(revenue) AS revenue,
       sum(revenue-cost) AS profit,
       100.0*sum(revenue-cost)/nullif(sum(revenue),0) AS margin
FROM sales
WHERE date BETWEEN DATE '2025-01-01' AND DATE '2025-12-31' AND channel='Web'
GROUP BY city, category ORDER BY revenue DESC;

-- Roll up: detail + city subtotal + grand total
SELECT city, category, grouping(city) AS city_total,
       grouping(category) AS category_total, sum(revenue) AS revenue
FROM sales GROUP BY ROLLUP(city, category);

-- Temporal drill down: replace month with quarter or year
WITH periods AS (
  SELECT date_trunc('month',date) AS period, sum(revenue) AS revenue
  FROM sales GROUP BY 1
)
SELECT *, revenue-lag(revenue) OVER (ORDER BY period) AS change
FROM periods ORDER BY period;
