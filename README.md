# Daraz Clone

A small e-commerce demo inspired by Daraz, built for a Web Technology course.
The backend is a Flask JSON API with a SQLite database. The frontend is plain HTML, CSS and JavaScript (no template engine).

## Features

- Browse products, search by name and filter by category
- Product detail page with price, discount and stock status
- Sign up, log in and log out
- Shopping cart: add, change quantity, remove (the header cart count updates without a page reload)
- Checkout with delivery address (Cash on Delivery) and stock check
- Order history and order details
- Admin panel: add, edit and delete products

## Tech stack

| Part | Technology |
| --- | --- |
| Backend | Python, Flask (JSON API) |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript (`fetch`) |

## Requirements

- Python 3.9 or later
- pip

## Setup on Windows

Open PowerShell in the project folder and run:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Generate a secret key and paste it into `.env` as `SECRET_KEY=...`:

```powershell
py -c "import secrets; print(secrets.token_hex(32))"
```

Create the database with sample products:

```powershell
py init_db.py
```

> Warning: `init_db.py` drops and recreates the tables. Running it again deletes existing users, carts and orders.

Start the server:

```powershell
py app.py
```

Open http://127.0.0.1:5000 in your browser.

## Demo admin account

`init_db.py` creates one local demo admin:

- Email: `admin@daraz.test`
- Password: `admin123`

Change or remove these credentials before using the app anywhere other than local development.

## Project structure

```
.
├── app.py              # Flask backend (JSON API + serves the frontend)
├── init_db.py          # Creates and seeds the SQLite database
├── requirements.txt    # Python dependencies
├── .env.example        # Template for the local .env file
└── frontend/
    ├── index.html, product.html, login.html, signup.html
    ├── cart.html, checkout.html, orders.html, order.html
    ├── admin.html, admin-form.html
    ├── css/style.css
    └── js/app.js       # Shared helpers: api(), esc(), header, messages
```

## API overview

| Method | Endpoint | Access |
| --- | --- | --- |
| GET | `/api/products`, `/api/products/<id>` | Public |
| POST | `/api/signup`, `/api/login`, `/api/logout` | Public |
| GET | `/api/me` | Public |
| GET, POST | `/api/cart`, `/api/cart/add`, `/api/cart/update`, `/api/cart/remove` | Logged in |
| POST | `/api/checkout` | Logged in |
| GET | `/api/orders`, `/api/orders/<id>` | Logged in (own orders only) |
| POST, PUT, DELETE | `/api/admin/products`, `/api/admin/products/<id>` | Admin only |

## Security notes

- Passwords are stored as hashes, never as plain text.
- The order total is calculated on the server, not taken from the browser.
- Users can only open their own orders; admin routes check the admin flag on the server.
- Write requests must be JSON, and the session cookie uses `SameSite=Lax` (protects against CSRF).
- All data is escaped before it is inserted into a page (protects against XSS).
- The secret key lives in `.env`, which is excluded from Git, together with `database.db`.
- Not included (future work): CSRF tokens, rate limiting on login, HTTPS and a production server.
