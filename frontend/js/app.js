// Shared helpers used by every page.

const $ = id => document.getElementById(id);

// Escape text before putting it into HTML. This is what stops XSS (Jinja2 used to do this for us).
const esc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = n => "Rs. " + Number(n).toLocaleString("en-US");
const discount = p => Math.round((p.old_price - p.price) * 100 / p.old_price);

// Talk to the Flask API. Always sends JSON (the server rejects anything else for POST/PUT/DELETE).
async function api(url, method = "GET", data) {
  const opts = { method, headers: { "Content-Type": "application/json" }, credentials: "same-origin" };
  if (data !== undefined) opts.body = JSON.stringify(data);
  const res = await fetch(url, opts);
  let json = {};
  try { json = await res.json(); } catch (e) { /* empty body */ }
  if (!res.ok) {
    const err = new Error(json.error || "Something went wrong.");
    err.status = res.status;
    throw err;
  }
  return json;
}

// Messages: flash() shows now, flashNext() shows on the next page (after a redirect).
function flash(message, type = "error") {
  $("flash").innerHTML = `<div class="flash ${type}">${esc(message)}</div>`;
}
function flashNext(message, type = "success") {
  sessionStorage.setItem("flash", JSON.stringify([message, type]));
}

// Draws the orange header and returns the logged-in user info.
async function renderHeader() {
  const me = await api("/api/me");
  const q = new URLSearchParams(location.search).get("q") || "";
  const links = me.logged_in
    ? `<span>Hi, ${esc(me.name)}</span><a href="/orders.html">My Orders</a>` +
      (me.is_admin ? `<a href="/admin-dashboard.html">Admin</a>` : "") + `<a href="#" id="logout">Logout</a>`
    : `<a href="/login.html">Login</a><a href="/signup.html">Sign Up</a>`;
  $("header").innerHTML = `
    <header class="topbar"><div class="container nav">
      <a href="/" class="logo">daraz</a>
      <form class="search" action="/" method="get">
        <input type="text" name="q" value="${esc(q)}" placeholder="Search in Daraz" autocomplete="off">
        <button type="submit">Search</button>
        <div id="suggest" class="suggest"></div>
      </form>
      <nav class="links">${links}<a href="/cart.html">Cart (${me.cart_count})</a></nav>
    </div></header>`;
  if ($("logout")) {
    $("logout").onclick = async e => { e.preventDefault(); await api("/api/logout", "POST"); location.href = "/"; };
  }
  setupSuggest();
  const saved = sessionStorage.getItem("flash");
  if (saved && $("flash")) { sessionStorage.removeItem("flash"); flash(...JSON.parse(saved)); }
  return me;
}

// For pages that need a logged-in user.
function requireLogin(me) {
  if (!me.logged_in) { flashNext("Please log in first.", "error"); location.href = "/login.html"; return false; }
  return true;
}

// The database stores time in UTC; show it in the visitor's own timezone.
function localTime(utc) {
  const d = new Date(utc.replace(" ", "T") + "Z");
  return d.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric",
                                     hour: "2-digit", minute: "2-digit", hour12: true });
}

// Live search: after the user stops typing for 250 ms, show up to 5 matching products under the search box.
function setupSuggest() {
  const input = document.querySelector(".search input"), box = $("suggest");
  let timer;
  const hide = () => { box.innerHTML = ""; box.style.display = "none"; };
  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) return hide();
    timer = setTimeout(async () => {
      try {
        const { products } = await api("/api/products?" + new URLSearchParams({ q, limit: 5 }));
        if (input.value.trim() !== q) return;                // the user kept typing, ignore this answer
        box.innerHTML = products.length ? products.map(p =>
          `<a href="/product.html?id=${p.id}"><img src="${esc(p.image)}" alt=""><span>${esc(p.name)}</span><b>${money(p.price)}</b></a>`
        ).join("") : '<div class="none">No matching products</div>';
        box.style.display = "block";
      } catch (e) { hide(); }
    }, 250);
  });
  input.addEventListener("keydown", e => { if (e.key === "Escape") hide(); });
  document.onclick = e => {                                  // click anywhere else closes the list
    const b = $("suggest");
    if (b && !e.target.closest(".search")) { b.innerHTML = ""; b.style.display = "none"; }
  };
}

// Tabs shown at the top of every admin page.
function adminTabs(active) {
  const tabs = [["Dashboard", "/admin-dashboard.html"], ["Products", "/admin.html"], ["Orders", "/admin-orders.html"]];
  return `<nav class="tabs">${tabs.map(([name, href]) => `<a href="${href}" class="${name === active ? "on" : ""}">${name}</a>`).join("")}</nav>`;
}
