-- Database: smart_insights


CREATE TABLE products (
product_id SERIAL PRIMARY KEY,
sku VARCHAR(50) UNIQUE NOT NULL,
name VARCHAR(255) NOT NULL,
category VARCHAR(100),
price NUMERIC(10,2) NOT NULL,
created_at TIMESTAMP DEFAULT NOW()
);


CREATE TABLE customers (
customer_id SERIAL PRIMARY KEY,
email VARCHAR(255) UNIQUE,
first_name VARCHAR(100),
last_name VARCHAR(100),
country VARCHAR(100),
signup_date DATE,
is_premium BOOLEAN DEFAULT FALSE
);


CREATE TABLE orders (
order_id SERIAL PRIMARY KEY,
customer_id INT NOT NULL REFERENCES customers(customer_id),
order_date TIMESTAMP NOT NULL,
total_amount NUMERIC(12,2) NOT NULL,
status VARCHAR(50) DEFAULT 'completed'
);


CREATE TABLE order_items (
order_item_id SERIAL PRIMARY KEY,
order_id INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
product_id INT NOT NULL REFERENCES products(product_id),
quantity INT NOT NULL,
unit_price NUMERIC(10,2) NOT NULL
);


CREATE TABLE support_tickets (
ticket_id SERIAL PRIMARY KEY,
customer_id INT REFERENCES customers(customer_id),
subject TEXT,
body TEXT,
created_at TIMESTAMP DEFAULT NOW(),
resolved_at TIMESTAMP NULL,
channel VARCHAR(50) -- email/chat/phone
);


CREATE TABLE delivery_logs (
delivery_id SERIAL PRIMARY KEY,
order_id INT REFERENCES orders(order_id),
shipped_at TIMESTAMP,
delivered_at TIMESTAMP,
carrier VARCHAR(100),
status VARCHAR(50)
);


-- Indexes to support analytical queries
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_customers_country ON customers(country);