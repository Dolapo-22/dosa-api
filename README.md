# Dosa Restaurant REST API

A REST API backend for a dosa restaurant, built with [FastAPI](https://fastapi.tiangolo.com/) and SQLite.

## What it does

The API exposes full CRUD (Create, Read, Update, Delete) operations for three resources:

| Resource | Description |
|----------|-------------|
| **Customers** | People who place orders (name + phone number) |
| **Items** | Menu items available to order (name + price) |
| **Orders** | A customer's order, with a timestamp, optional notes, and a list of item IDs |

## Design

### Database schema (`db.sqlite`)

```
customers
  id        INTEGER  PRIMARY KEY AUTOINCREMENT
  name      TEXT     NOT NULL
  phone     TEXT     NOT NULL UNIQUE

items
  id        INTEGER  PRIMARY KEY AUTOINCREMENT
  name      TEXT     NOT NULL UNIQUE
  price     REAL     NOT NULL

orders
  id          INTEGER  PRIMARY KEY AUTOINCREMENT
  customer_id INTEGER  NOT NULL  REFERENCES customers(id)
  timestamp   INTEGER  NOT NULL
  notes       TEXT     NOT NULL DEFAULT ''

order_items           -- junction table (many orders ↔ many items)
  order_id  INTEGER  NOT NULL  REFERENCES orders(id)
  item_id   INTEGER  NOT NULL  REFERENCES items(id)
  PRIMARY KEY (order_id, item_id)
```

Orders reference customers via a foreign key, and items are linked to orders through the `order_items` junction table. SQLite foreign key enforcement is enabled at runtime via `PRAGMA foreign_keys = ON`.

### Project files

| File | Purpose |
|------|---------|
| `init_db.py` | Creates `db.sqlite` with all tables and constraints |
| `main.py` | FastAPI application — all 12 CRUD endpoints |
| `db.sqlite` | SQLite database (created by `init_db.py`) |

## How to use

### 1. Install dependencies

```bash
pip install fastapi uvicorn
```

### 2. Initialize the database

```bash
python init_db.py
```

### 3. Start the API server

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive docs (Swagger UI) are at `http://127.0.0.1:8000/docs`.

---

## API endpoints

### Customers

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/customers` | Create a customer |
| `GET` | `/customers/{id}` | Get a customer by ID |
| `PUT` | `/customers/{id}` | Update a customer |
| `DELETE` | `/customers/{id}` | Delete a customer |

**Customer JSON shape:**
```json
{ "name": "Damodhar", "phone": "732-555-5509" }
```

---

### Items

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/items` | Create a menu item |
| `GET` | `/items/{id}` | Get an item by ID |
| `PUT` | `/items/{id}` | Update an item |
| `DELETE` | `/items/{id}` | Delete an item |

**Item JSON shape:**
```json
{ "name": "Masala Dosa", "price": 10.95 }
```

---

### Orders

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/orders` | Create an order |
| `GET` | `/orders/{id}` | Get an order by ID |
| `PUT` | `/orders/{id}` | Update an order |
| `DELETE` | `/orders/{id}` | Delete an order |

**Order JSON shape:**
```json
{
  "customer_id": 1,
  "timestamp": 1702219784,
  "notes": "extra spicy",
  "items": [1, 2]
}
```

`items` is a list of item IDs to associate with the order. A PUT replaces the full item list.

---

## Error responses

| Status | Meaning |
|--------|---------|
| `404 Not Found` | The requested resource ID does not exist |
| `409 Conflict` | Duplicate unique value (phone/name) or FK violation (e.g. deleting a customer who has orders) |
| `422 Unprocessable Entity` | Request body failed validation (e.g. negative item price) |

## Example walkthrough

```bash
# Create a customer
curl -X POST http://localhost:8000/customers \
     -H "Content-Type: application/json" \
     -d '{"name": "Damodhar", "phone": "732-555-5509"}'
# → {"id":1,"name":"Damodhar","phone":"732-555-5509"}

# Create a menu item
curl -X POST http://localhost:8000/items \
     -H "Content-Type: application/json" \
     -d '{"name": "Masala Dosa", "price": 10.95}'
# → {"id":1,"name":"Masala Dosa","price":10.95}

# Place an order
curl -X POST http://localhost:8000/orders \
     -H "Content-Type: application/json" \
     -d '{"customer_id": 1, "timestamp": 1702219784, "notes": "extra spicy", "items": [1]}'
# → {"id":1,"customer_id":1,"timestamp":1702219784,"notes":"extra spicy","items":[1]}

# Retrieve the order
curl http://localhost:8000/orders/1
```
