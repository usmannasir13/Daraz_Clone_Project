import os
import sqlite3
from functools import wraps
from flask import Flask, request, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

# Backend = Flask JSON API. Frontend = plain HTML/CSS/JavaScript files in the "frontend" folder.
app = Flask(__name__, static_folder="frontend", static_url_path="")
app.secret_key = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def to_list(rows):
    return [dict(r) for r in rows]


def error(message, status=400):
    return jsonify({"error": message}), status


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@app.before_request
def json_only_for_writes():
    # A cross-site HTML form cannot send application/json, so this also blocks CSRF.
    if request.path.startswith("/api/") and request.method in ("POST", "PUT", "DELETE") and not request.is_json:
        return error("JSON requests only.", 415)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return error("Please log in first.", 401)
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return error("Please log in first.", 401)
        if not session.get("is_admin"):
            return error("Admins only.", 403)
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
def home_page():
    return send_from_directory(app.static_folder, "index.html")


# ---------------- ACCOUNT ----------------
@app.route("/api/me")
def me():
    count = 0
    if "user_id" in session:
        db = get_db()
        count = db.execute("SELECT COALESCE(SUM(quantity), 0) FROM cart_items WHERE user_id = ?",
                           (session["user_id"],)).fetchone()[0]
        db.close()
    return jsonify(logged_in="user_id" in session, name=session.get("user_name"),
                   is_admin=bool(session.get("is_admin")), cart_count=count)


@app.route("/api/signup", methods=["POST"])
def signup():
    d = body()
    name = str(d.get("name", "")).strip()
    email = str(d.get("email", "")).strip().lower()
    password = str(d.get("password", ""))
    if not name or not email or len(password) < 6:
        return error("Fill all fields. Password must be at least 6 characters.")
    db = get_db()
    if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        db.close()
        return error("This email is already registered. Please log in.", 409)
    db.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
               (name, email, generate_password_hash(password)))
    db.commit()
    db.close()
    return jsonify(ok=True)


@app.route("/api/login", methods=["POST"])
def login():
    d = body()
    email = str(d.get("email", "")).strip().lower()
    password = str(d.get("password", ""))
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    if user and check_password_hash(user["password"], password):
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["is_admin"] = user["is_admin"]
        return jsonify(ok=True)
    return error("Wrong email or password.", 401)


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(ok=True)


# ---------------- PRODUCTS ----------------
@app.route("/api/products")
def products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sql, params = "SELECT * FROM products WHERE 1=1", []
    if q:
        sql += " AND name LIKE ?"
        params.append(f"%{q}%")
    if category:
        sql += " AND category = ?"
        params.append(category)
    db = get_db()
    items = to_list(db.execute(sql + " ORDER BY id", params).fetchall())
    cats = [r["category"] for r in db.execute("SELECT DISTINCT category FROM products ORDER BY category")]
    db.close()
    return jsonify(products=items, categories=cats)


@app.route("/api/products/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    p = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    db.close()
    if p is None:
        return error("Product not found.", 404)
    return jsonify(dict(p))


# ---------------- CART ----------------
CART_SQL = """SELECT c.id, c.quantity, p.id AS product_id, p.name, p.price, p.image, p.stock
              FROM cart_items c JOIN products p ON p.id = c.product_id WHERE c.user_id = ?"""


@app.route("/api/cart")
@login_required
def cart():
    db = get_db()
    items = to_list(db.execute(CART_SQL, (session["user_id"],)).fetchall())
    db.close()
    return jsonify(items=items, total=sum(i["price"] * i["quantity"] for i in items),
                   item_count=sum(i["quantity"] for i in items))


@app.route("/api/cart/add", methods=["POST"])
@login_required
def cart_add():
    d = body()
    pid = to_int(d.get("product_id"))
    qty = max(1, to_int(d.get("quantity", 1)) or 1)
    db = get_db()
    p = db.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()
    if p is None or p["stock"] < 1:
        db.close()
        return error("This product is out of stock.")
    row = db.execute("SELECT id, quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
                     (session["user_id"], pid)).fetchone()
    if row:
        db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (min(row["quantity"] + qty, p["stock"]), row["id"]))
    else:
        db.execute("INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
                   (session["user_id"], pid, min(qty, p["stock"])))
    db.commit()
    db.close()
    return jsonify(ok=True)


@app.route("/api/cart/update", methods=["POST"])
@login_required
def cart_update():
    d = body()
    item_id, qty = to_int(d.get("item_id")), to_int(d.get("quantity"))
    if item_id is None or qty is None:
        return error("Invalid data.")
    db = get_db()
    item = db.execute("""SELECT c.id, p.stock FROM cart_items c JOIN products p ON p.id = c.product_id
                         WHERE c.id = ? AND c.user_id = ?""", (item_id, session["user_id"])).fetchone()
    if item:
        if qty < 1:
            db.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
        else:
            db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (min(qty, item["stock"]), item_id))
        db.commit()
    db.close()
    return jsonify(ok=True)


@app.route("/api/cart/remove", methods=["POST"])
@login_required
def cart_remove():
    item_id = to_int(body().get("item_id"))
    db = get_db()
    db.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, session["user_id"]))
    db.commit()
    db.close()
    return jsonify(ok=True)


# ---------------- CHECKOUT & ORDERS ----------------
@app.route("/api/checkout", methods=["POST"])
@login_required
def checkout():
    address = str(body().get("address", "")).strip()
    db = get_db()
    items = db.execute(CART_SQL, (session["user_id"],)).fetchall()
    if not items:
        db.close()
        return error("Your cart is empty.")
    if len(address) < 10:
        db.close()
        return error("Please enter your full delivery address.")
    total = sum(i["price"] * i["quantity"] for i in items)    # always calculated on the server
    try:
        order_id = db.execute("INSERT INTO orders (user_id, total, address) VALUES (?, ?, ?)",
                              (session["user_id"], total, address)).lastrowid
        for i in items:
            res = db.execute("UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                             (i["quantity"], i["product_id"], i["quantity"]))
            if res.rowcount == 0:
                raise ValueError(i["name"])
            db.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                       (order_id, i["product_id"], i["quantity"], i["price"]))
        db.execute("DELETE FROM cart_items WHERE user_id = ?", (session["user_id"],))
        db.commit()
    except ValueError as e:
        db.rollback()
        db.close()
        return error(f"Not enough stock for {e}. Please update your cart.")
    db.close()
    return jsonify(ok=True, order_id=order_id)


@app.route("/api/orders")
@login_required
def orders():
    db = get_db()
    rows = to_list(db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)))
    db.close()
    return jsonify(orders=rows)


@app.route("/api/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?",    # users see only their own orders
                       (order_id, session["user_id"])).fetchone()
    if order is None:
        db.close()
        return error("Order not found.", 404)
    items = to_list(db.execute("""SELECT oi.quantity, oi.price, p.name, p.image FROM order_items oi
                                  JOIN products p ON p.id = oi.product_id WHERE oi.order_id = ?""", (order_id,)))
    db.close()
    return jsonify(order=dict(order), items=items)


# ---------------- ADMIN ----------------
def read_product(d):
    name, category = str(d.get("name", "")).strip(), str(d.get("category", "")).strip()
    price, stock = to_int(d.get("price")), to_int(d.get("stock"))
    old_price = to_int(d.get("old_price")) or None
    image = str(d.get("image", "")).strip()
    errors = []
    if not name or not category:
        errors.append("Name and category are required.")
    if price is None or price < 1:
        errors.append("Price must be a positive number.")
    if old_price and price is not None and old_price <= price:
        errors.append("Old price must be higher than the price (or leave it empty).")
    if stock is None or stock < 0:
        errors.append("Stock must be 0 or more.")
    if image and not image.startswith(("http://", "https://")):
        errors.append("Image must be a full URL starting with http:// or https://")
    data = {"name": name, "category": category, "price": price, "old_price": old_price, "stock": stock,
            "description": str(d.get("description", "")).strip(),
            "image": image or "https://picsum.photos/seed/default/400/400"}
    return data, errors


@app.route("/api/admin/products", methods=["POST"])
@admin_required
def admin_add():
    data, errors = read_product(body())
    if errors:
        return error(" ".join(errors))
    db = get_db()
    db.execute("""INSERT INTO products (name, category, price, old_price, description, image, stock)
                  VALUES (:name, :category, :price, :old_price, :description, :image, :stock)""", data)
    db.commit()
    db.close()
    return jsonify(ok=True)


@app.route("/api/admin/products/<int:product_id>", methods=["PUT"])
@admin_required
def admin_edit(product_id):
    data, errors = read_product(body())
    if errors:
        return error(" ".join(errors))
    data["id"] = product_id
    db = get_db()
    res = db.execute("""UPDATE products SET name = :name, category = :category, price = :price,
                        old_price = :old_price, description = :description, image = :image, stock = :stock
                        WHERE id = :id""", data)
    db.commit()
    db.close()
    return jsonify(ok=True) if res.rowcount else error("Product not found.", 404)


@app.route("/api/admin/products/<int:product_id>", methods=["DELETE"])
@admin_required
def admin_delete(product_id):
    db = get_db()
    if db.execute("SELECT 1 FROM order_items WHERE product_id = ? LIMIT 1", (product_id,)).fetchone():
        db.close()
        return error("This product is part of existing orders, so it cannot be deleted. Set its stock to 0 instead.", 409)
    db.execute("DELETE FROM cart_items WHERE product_id = ?", (product_id,))
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    db.close()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(debug=True)
