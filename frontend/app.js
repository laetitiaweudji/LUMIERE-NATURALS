// Lumière Naturals consumer dashboard.
// Every value shown after login comes from the Flask API, which reads it
// live from the Supabase database. Nothing about customers is stored here.

// When the page is served by Flask (http://127.0.0.1:5000) the API is on the
// same address. If the file is opened straight from disk, use the local server.
const API_BASE = location.protocol === "file:" ? "http://127.0.0.1:5000" : "";

const $ = (id) => document.getElementById(id);
const rupees = (n) => "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const formatDate = (iso) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;   // textContent = safe, never runs HTML
  return node;
}

// ---------------------------------------------------------------- server status
async function checkServer() {
  const status = $("server-status");
  const text = status.querySelector(".status-text");
  try {
    const res = await fetch(API_BASE + "/health");
    const data = await res.json();
    if (data.database === "connected") {
      status.className = "server-status online";
      text.textContent = "Live login server connected · database online";
    } else {
      status.className = "server-status offline";
      text.textContent = "Login server running, but the database is unreachable";
    }
  } catch {
    status.className = "server-status offline";
    text.textContent = "Login server offline — start it with: python backend/app.py";
  }
}

// ------------------------------------------------------------------------ login
async function handleLogin(event) {
  event.preventDefault();
  const email = $("email").value.trim();
  const password = $("password").value;
  const error = $("login-error");
  const button = $("login-button");

  error.textContent = "";
  if (!email || !password) {
    error.textContent = "Please enter your email and password.";
    return;
  }

  button.disabled = true;
  button.textContent = "Signing in…";
  try {
    const res = await fetch(API_BASE + "/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Login failed.");
    showDashboard(data);
  } catch (err) {
    error.textContent = err instanceof TypeError
      ? "Cannot reach the login server. Is the backend running?"
      : err.message;
  } finally {
    button.disabled = false;
    button.textContent = "Log In";
  }
}

function logout() {
  $("dashboard").hidden = true;
  $("login-screen").hidden = false;
  $("login-form").reset();
  $("orders-list").replaceChildren();
  $("profile").replaceChildren();
  $("email").focus();
}

// -------------------------------------------------------------------- dashboard
function showDashboard({ customer, orders, summary }) {
  const firstName = customer.name.split(" ")[0];
  $("welcome").textContent = `Welcome back, ${firstName}`;
  $("order-summary").textContent = summary.total_orders === 0
    ? "You haven't placed an order yet."
    : `You've placed ${summary.total_orders} order${summary.total_orders === 1 ? "" : "s"} with us since ${formatDate(summary.first_order_date)}.`;
  $("hero-points").textContent = summary.loyalty_points.toLocaleString("en-IN");

  renderOrders(orders);
  renderProfile(customer, summary);

  $("login-screen").hidden = true;
  $("dashboard").hidden = false;
  window.scrollTo(0, 0);
}

function stars(rating) {
  const wrap = el("div", "stars");
  if (rating == null) {
    wrap.textContent = "Not rated yet";
    return wrap;
  }
  wrap.setAttribute("aria-label", `Rated ${rating} out of 5`);
  for (let i = 1; i <= 5; i++) wrap.append(el("span", i <= rating ? "" : "off", "★"));
  return wrap;
}

function renderOrders(orders) {
  const list = $("orders-list");
  list.replaceChildren();
  if (orders.length === 0) {
    list.append(el("li", "empty", "No orders yet."));
    return;
  }
  for (const o of orders) {
    const item = el("li", "order");

    const left = el("div");
    const qty = o.quantity > 1 ? ` × ${o.quantity}` : "";
    left.append(
      el("div", "order-name", `${o.product_name} · ${o.size}${qty}`),
      el("div", "order-meta", `${formatDate(o.order_date)} · ${o.channel_name} · ${o.order_id}`),
    );

    const right = el("div", "order-right");
    right.append(el("div", "order-price", rupees(o.revenue)), stars(o.rating));

    item.append(left, right);
    list.append(item);
  }
}

function renderProfile(customer, summary) {
  const rows = [
    ["Email", customer.email],
    ["Location", `${customer.city}, ${customer.country}`],
    ["Age group", customer.age_group],
    ["Total spent", rupees(summary.total_spent)],
    ["Loyalty points", summary.loyalty_points.toLocaleString("en-IN")],
  ];
  const profile = $("profile");
  profile.replaceChildren();
  for (const [label, value] of rows) {
    const row = el("div", "profile-row");
    row.append(el("dt", "", label), el("dd", "", value));
    profile.append(row);
  }
}

$("login-form").addEventListener("submit", handleLogin);
$("logout-button").addEventListener("click", logout);
checkServer();
