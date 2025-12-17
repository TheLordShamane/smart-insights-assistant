"""
Simple mock-data generator for milestone 1.
Generates products, customers, orders, order_items, support_tickets, and delivery_logs.

"""

import argparse
import random
from datetime import datetime, timedelta
from faker import Faker
import psycopg2

fake = Faker()

CREATE_TABLES_SQL = open('db/schema.sql').read()

def connect(db_url):
    conn = psycopg2.connect(db_url)
    return conn

def seed(conn, n_products=100, n_customers=50, n_orders=200):
    cur = conn.cursor()
    cur.execute(CREATE_TABLES_SQL)
    conn.commit()
    
    products = []
    for i in range(n_products):
        sku = f"SKU-{i:05d}"
        name = fake.word().title() + " Product"
        category = random.choice(['Electronics','Apparel','Home','Books','Grocery','Toys'])
        price = round(random.uniform(5, 500), 2)
        cur.execute(
            "INSERT INTO products (sku, name, category, price) VALUES (%s,%s,%s,%s) RETURNING product_id",
            (sku,name,category,price)
        )
        pid = cur.fetchone()[0]
        products.append({'product_id': pid, 'price': price})


    customers = []
    for i in range(n_customers):
        email = fake.unique.email()
        fn = fake.first_name()
        ln = fake.last_name()
        country = fake.country()
        signup = fake.date_between(start_date='-2y', end_date='today')
        is_premium = random.random() < 0.1
        cur.execute(
            "INSERT INTO customers (email, first_name, last_name, country, signup_date, is_premium) VALUES (%s,%s,%s,%s,%s,%s) RETURNING customer_id",
            (email,fn,ln,country,signup,is_premium)
        )
        cid = cur.fetchone()[0]
        customers.append(cid)


    for i in range(n_orders):
        cid = random.choice(customers)
        order_date = datetime.now() - timedelta(days=random.randint(0, 365))
        num_items = random.randint(1,5)
        total = 0
        cur.execute("INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES (%s,%s,%s,%s) RETURNING order_id",
        (cid, order_date, 0.0, 'completed'))
        oid = cur.fetchone()[0]
        for _ in range(num_items):
            p = random.choice(products)
            qty = random.randint(1,3)
            unit = p['price']
            cur.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s,%s,%s,%s)",
                        (oid, p['product_id'], qty, unit))
            total += qty * unit
        cur.execute("UPDATE orders SET total_amount = %s WHERE order_id = %s", (round(total,2), oid))


        # delivery
        shipped = order_date + timedelta(days=random.randint(0,3))
        delivered = shipped + timedelta(days=random.randint(1,7))
        carrier = random.choice(['DHL','FedEx','LocalCarrier'])
        status = 'delivered'
        cur.execute("INSERT INTO delivery_logs (order_id, shipped_at, delivered_at, carrier, status) VALUES (%s,%s,%s,%s,%s)",
        (oid, shipped, delivered, carrier, status))

    # create some support tickets
    for _ in range(int(n_orders * 0.05)):
        cid = random.choice(customers)
        subj = fake.sentence(nb_words=6)
        body = fake.paragraph(nb_sentences=3)
        created = datetime.now() - timedelta(days=random.randint(0, 365))
        resolved = created + timedelta(days=random.randint(0, 14))
        channel = random.choice(['email','chat','phone'])
        cur.execute("INSERT INTO support_tickets (customer_id, subject, body, created_at, resolved_at, channel) VALUES (%s,%s,%s,%s,%s,%s)",
                    (cid, subj, body, created, resolved, channel))


    conn.commit()
    cur.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-url', required=True)
    args = parser.parse_args()
    conn = connect(args.db_url)
    seed(conn)
    conn.close()
    print('Seeding complete')