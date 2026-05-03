import sqlite3
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB_PATH = "db.sqlite"

app = FastAPI(title="Dosa Restaurant API")


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
@contextmanager
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# -----------------------------
# MODELS (INPUT / OUTPUT)
# -----------------------------
class CustomerIn(BaseModel):
    name: str
    phone: str


class CustomerOut(CustomerIn):
    id: int


class ItemIn(BaseModel):
    name: str
    price: float = Field(gt=0)


class ItemOut(ItemIn):
    id: int


class OrderItem(BaseModel):
    item_id: int
    quantity: int = 1


class OrderIn(BaseModel):
    customer_id: int
    timestamp: int
    notes: str = ""
    items: list[OrderItem]


class OrderOut(BaseModel):
    id: int
    customer_id: int
    timestamp: int
    notes: str
    items: list[dict]


# -----------------------------
# CUSTOMER ENDPOINTS
# -----------------------------
@app.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(customer: CustomerIn):
    with get_db() as con:
        try:
            cur = con.execute(
                "INSERT INTO customers (name, phone) VALUES (?, ?)",
                (customer.name, customer.phone),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Phone already exists")

    return CustomerOut(id=cur.lastrowid, **customer.model_dump())


@app.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int):
    with get_db() as con:
        row = con.execute(
            "SELECT id, name, phone FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    return CustomerOut(**row)


@app.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, customer: CustomerIn):
    with get_db() as con:
        try:
            cur = con.execute(
                "UPDATE customers SET name=?, phone=? WHERE id=?",
                (customer.name, customer.phone, customer_id),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Phone already exists")

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Customer not found")

    return CustomerOut(id=customer_id, **customer.model_dump())


@app.delete("/customers/{customer_id}", status_code=204)
def delete_customer(customer_id: int):
    with get_db() as con:
        cur = con.execute(
            "DELETE FROM customers WHERE id = ?", (customer_id,)
        )

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Customer not found")


# -----------------------------
# ITEM ENDPOINTS
# -----------------------------
@app.post("/items", response_model=ItemOut, status_code=201)
def create_item(item: ItemIn):
    with get_db() as con:
        try:
            cur = con.execute(
                "INSERT INTO items (name, price) VALUES (?, ?)",
                (item.name, item.price),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Item already exists")

    return ItemOut(id=cur.lastrowid, **item.model_dump())


@app.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int):
    with get_db() as con:
        row = con.execute(
            "SELECT id, name, price FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    return ItemOut(**row)


@app.put("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, item: ItemIn):
    with get_db() as con:
        try:
            cur = con.execute(
                "UPDATE items SET name=?, price=? WHERE id=?",
                (item.name, item.price, item_id),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Item already exists")

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")

    return ItemOut(id=item_id, **item.model_dump())


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    with get_db() as con:
        cur = con.execute("DELETE FROM items WHERE id = ?", (item_id,))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")


# -----------------------------
# ORDER HELPER
# -----------------------------
def _fetch_order(con, order_id):
    row = con.execute(
        "SELECT id, customer_id, timestamp, notes FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()

    if not row:
        return None

    items = [
        {"item_id": r["item_id"], "quantity": r["quantity"]}
        for r in con.execute(
            "SELECT item_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
    ]

    return OrderOut(
        id=row["id"],
        customer_id=row["customer_id"],
        timestamp=row["timestamp"],
        notes=row["notes"],
        items=items,
    )


# -----------------------------
# ORDER ENDPOINTS
# -----------------------------
@app.post("/orders", response_model=OrderOut, status_code=201)
def create_order(order: OrderIn):
    with get_db() as con:
        try:
            cur = con.execute(
                "INSERT INTO orders (customer_id, timestamp, notes) VALUES (?, ?, ?)",
                (order.customer_id, order.timestamp, order.notes),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Invalid customer_id")

        order_id = cur.lastrowid

        for item in order.items:
            con.execute(
                "INSERT INTO order_items (order_id, item_id, quantity) VALUES (?, ?, ?)",
                (order_id, item.item_id, item.quantity),
            )

        result = _fetch_order(con, order_id)

    return result


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int):
    with get_db() as con:
        result = _fetch_order(con, order_id)

    if not result:
        raise HTTPException(status_code=404, detail="Order not found")

    return result


@app.put("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, order: OrderIn):
    with get_db() as con:
        cur = con.execute(
            "UPDATE orders SET customer_id=?, timestamp=?, notes=? WHERE id=?",
            (order.customer_id, order.timestamp, order.notes, order_id),
        )

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Order not found")

        con.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))

        for item in order.items:
            con.execute(
                "INSERT INTO order_items (order_id, item_id, quantity) VALUES (?, ?, ?)",
                (order_id, item.item_id, item.quantity),
            )

        result = _fetch_order(con, order_id)

    return result


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: int):
    with get_db() as con:
        cur = con.execute("DELETE FROM orders WHERE id = ?", (order_id,))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Order not found")