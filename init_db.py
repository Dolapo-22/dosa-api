import json
import os
import sqlite3
from collections import Counter   # 🔥 IMPORTANT

DB_PATH = "db.sqlite"
ORDERS_JSON = os.path.join(os.path.dirname(__file__), "example_orders.json")


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT    NOT NULL,
            phone TEXT    NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS items (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT    NOT NULL UNIQUE,
            price REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            timestamp   INTEGER NOT NULL,
            notes       TEXT    NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS order_items (
            order_id INTEGER NOT NULL,
            item_id  INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (order_id, item_id),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id)
        );
    """)

    con.commit()
    print("Schema created.")

    _seed(con)

    con.close()
    print(f"Database ready at {DB_PATH}")


def _seed(con):
    with open(ORDERS_JSON, encoding="utf-8") as f:
        orders = json.load(f)

    customer_id_map = {}
    item_id_map = {}

    # -----------------------
    # Customers
    # -----------------------
    for order in orders:
        phone = order["phone"]
        if phone not in customer_id_map:
            con.execute(
                "INSERT OR IGNORE INTO customers (name, phone) VALUES (?, ?)",
                (order["name"], phone),
            )
            row = con.execute(
                "SELECT id FROM customers WHERE phone = ?", (phone,)
            ).fetchone()
            customer_id_map[phone] = row[0]

    print(f"Customers loaded: {len(customer_id_map)}")

    # -----------------------
    # Items
    # -----------------------
    for order in orders:
        for item in order["items"]:
            name = item["name"]
            if name not in item_id_map:
                con.execute(
                    "INSERT OR IGNORE INTO items (name, price) VALUES (?, ?)",
                    (name, item["price"]),
                )
                row = con.execute(
                    "SELECT id FROM items WHERE name = ?", (name,)
                ).fetchone()
                item_id_map[name] = row[0]

    print(f"Items loaded: {len(item_id_map)}")

    # -----------------------
    # Orders + FIXED PART
    # -----------------------
    order_count = 0

    for order in orders:
        customer_id = customer_id_map[order["phone"]]

        cur = con.execute(
            "INSERT INTO orders (customer_id, timestamp, notes) VALUES (?, ?, ?)",
            (customer_id, order["timestamp"], order.get("notes", "")),
        )
        order_id = cur.lastrowid

        # 🔥 FIX: combine duplicate items into quantity
        item_counts = Counter(item["name"] for item in order["items"])

        for name, qty in item_counts.items():
            item_id = item_id_map[name]
            con.execute(
                "INSERT INTO order_items (order_id, item_id, quantity) VALUES (?, ?, ?)",
                (order_id, item_id, qty),
            )

        order_count += 1

    con.commit()
    print(f"Orders loaded: {order_count}")


if __name__ == "__main__":
    init_db()