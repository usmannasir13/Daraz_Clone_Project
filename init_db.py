import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ---------- TABLES ----------
cur.executescript("""
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    email     TEXT NOT NULL UNIQUE,
    password  TEXT NOT NULL,          -- hashed, never plain text
    is_admin  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    category     TEXT NOT NULL,
    price        INTEGER NOT NULL,    -- in Rs
    old_price    INTEGER,             -- for discount display
    description  TEXT,
    image        TEXT,                -- image URL
    stock        INTEGER NOT NULL DEFAULT 10
);

CREATE TABLE cart_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    total       INTEGER NOT NULL,
    address     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'Pending',
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    price       INTEGER NOT NULL      -- price at the time of order
);
""")

# ---------- SAMPLE PRODUCTS ----------
# (name, category, price, old_price, description, image, stock)
def img(seed):
    return f"https://picsum.photos/seed/{seed}/400/400"

products = [
    ("Wireless Earbuds Bluetooth 5.3", "Electronics", 2499, 3999, "Noise reduction, 20 hours battery, touch controls.", img("earbuds"), 25),
    ("Smart Watch Series 8", "Electronics", 4999, 7999, "Heart rate, step counter, AMOLED display.", img("smartwatch"), 15),
    ("Power Bank 20000mAh", "Electronics", 3199, 4500, "Fast charging, dual USB output.", img("powerbank"), 30),
    ("Men's Cotton T-Shirt", "Fashion", 899, 1499, "Soft cotton, regular fit, available in many colors.", img("tshirt"), 50),
    ("Women's Printed Lawn Suit", "Fashion", 2799, 3999, "3-piece unstitched lawn suit.", img("lawnsuit"), 20),
    ("Running Sneakers", "Fashion", 3499, 5499, "Lightweight and comfortable daily-wear shoes.", img("sneakers"), 18),
    ("Non-Stick Fry Pan 28cm", "Home", 1299, 1999, "Durable non-stick coating, even heating.", img("frypan"), 40),
    ("Electric Kettle 1.8L", "Home", 1899, 2599, "Auto shut-off, stainless steel body.", img("kettle"), 22),
    ("LED Desk Lamp", "Home", 1099, 1699, "Adjustable brightness, USB powered.", img("desklamp"), 35),
    ("Face Wash 150ml", "Beauty", 599, 799, "Gentle daily cleanser for all skin types.", img("facewash"), 60),
    ("Perfume for Men 100ml", "Beauty", 1999, 2999, "Long-lasting fragrance.", img("perfume"), 28),
    ("Python Programming Book", "Books", 1499, 1999, "Beginner-friendly guide with examples.", img("pythonbook"), 12),
]

cur.executemany(
    "INSERT INTO products (name, category, price, old_price, description, image, stock) VALUES (?,?,?,?,?,?,?)",
    products,
)

# ---------- ADMIN USER ----------
cur.execute(
    "INSERT INTO users (name, email, password, is_admin) VALUES (?,?,?,1)",
    ("Admin", "admin@daraz.test", generate_password_hash("admin123")),
)

conn.commit()
conn.close()
print("Database ready: database.db")
print("Admin login -> admin@daraz.test / admin123")
