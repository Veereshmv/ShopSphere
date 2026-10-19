const API = {
    products: "/api/products",
    cart: "/api/cart",
    inventory: "/api/inventory",
    orders: "/api/orders",
    payments: "/api/payments",
};

const state = {
    products: [],
    cart: [],
    orders: [],
    loading: false,
};

const $ = (selector) => document.querySelector(selector);

const formatPrice = (amount) =>
    new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2,
    }).format(Number(amount));

const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (character) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    })[character]);

function showMessage(selector, message, isError = false) {
    const element = $(selector);
    element.textContent = message;
    element.style.color = isError ? "#a43e36" : "#176b4d";
}

async function request(url, options = {}) {
    let response;

    try {
        response = await fetch(url, {
            ...options,
            headers: {
                ...(options.body ? { "Content-Type": "application/json" } : {}),
                ...options.headers,
            },
        });
    } catch {
        throw new Error(
            "Cannot connect to a backend service. Check that its Docker container is running."
        );
    }

    const text = await response.text();
    let data = {};

    if (text) {
        try {
            data = JSON.parse(text);
        } catch {
            data = { detail: text };
        }
    }

    if (!response.ok) {
        const detail =
            typeof data.detail === "string"
                ? data.detail
                : JSON.stringify(data.detail ?? data);
        throw new Error(detail || `Request failed (${response.status})`);
    }

    return data;
}

function currentUserId() {
    return $("#user-id").value.trim();
}

function cartTotal() {
    return state.cart.reduce(
        (total, item) => total + Number(item.price) * Number(item.quantity),
        0
    );
}

function renderProducts() {
    const container = $("#product-list");

    if (!state.products.length) {
        container.innerHTML =
            '<p class="loading-message">No products are available right now.</p>';
        return;
    }

    const symbols = ["🖱️", "⌨️", "🔌"];

    container.innerHTML = state.products.map((product, index) => {
        const stock = Number(product.stock ?? 0);
        const unavailable = stock <= 0;

        return `
            <article class="product-card">
                <div class="product-art">
                    <span class="product-category">Electronics</span>
                    <span class="product-symbol" aria-hidden="true">
                        ${symbols[index % symbols.length]}
                    </span>
                </div>
                <h3>${escapeHtml(product.name)}</h3>
                <p class="product-description">
                    ${escapeHtml(product.description || "A useful everyday tech essential.")}
                </p>
                <div class="product-bottom">
                    <span class="product-price">${formatPrice(product.price)}</span>
                    <button
                        class="add-button"
                        type="button"
                        data-add="${Number(product.id)}"
                        ${unavailable ? "disabled" : ""}
                    >
                        ${unavailable ? "Out of stock" : "Add to cart"}
                    </button>
                </div>
            </article>
        `;
    }).join("");
}

async function loadProducts() {
    $("#product-list").innerHTML =
        '<p class="loading-message">Loading products…</p>';

    try {
        state.products = await request(`${API.products}/products`);
        renderProducts();
    } catch (error) {
        $("#product-list").innerHTML =
            '<p class="loading-message">Unable to load products.</p>';
        showMessage("#product-message", error.message, true);
    }
}

function renderCart() {
    const container = $("#cart-items");
    const count = state.cart.reduce(
        (total, item) => total + Number(item.quantity),
        0
    );

    $("#cart-count").textContent = String(count);
    $("#cart-total").textContent = formatPrice(cartTotal());
    $("#checkout-button").disabled =
        state.cart.length === 0 || state.loading;

    if (!state.cart.length) {
        container.innerHTML =
            "<p>Your cart is empty. Add a product to get started.</p>";
        return;
    }

    container.innerHTML = state.cart.map((item) => `
        <div class="cart-row">
            <div>
                <div class="cart-product-name">${escapeHtml(item.name)}</div>
                <div class="cart-product-detail">
                    ${formatPrice(item.price)} each
                </div>
            </div>
            <div class="quantity-control">
                <button type="button" data-decrease="${Number(item.product_id)}"
                    aria-label="Decrease quantity">−</button>
                <span>${Number(item.quantity)}</span>
                <button type="button" data-increase="${Number(item.product_id)}"
                    aria-label="Increase quantity">+</button>
            </div>
            <button class="remove-button" type="button"
                data-remove="${Number(item.product_id)}">Remove</button>
        </div>
    `).join("");
}

async function loadCart() {
    try {
        const data = await request(
            `${API.cart}/cart/${encodeURIComponent(currentUserId())}`
        );

        // The cart service returns a hash of product IDs to JSON item strings.
        const items = data.items ?? data;

        if (Array.isArray(items)) {
            state.cart = items;
        } else {
            state.cart = Object.values(items).map((item) =>
                typeof item === "string" ? JSON.parse(item) : item
            );
        }

        renderCart();
    } catch (error) {
        showMessage("#cart-message", error.message, true);
    }
}

async function addToCart(productId) {
    const product = state.products.find(
        (item) => Number(item.id) === Number(productId)
    );

    if (!product) return;

    try {
        await request(
            `${API.cart}/cart/${encodeURIComponent(currentUserId())}/items`,
            {
                method: "POST",
                body: JSON.stringify({
                    product_id: Number(product.id),
                    name: product.name,
                    price: Number(product.price),
                    quantity: 1,
                }),
            }
        );

        await loadCart();
        showMessage("#cart-message", `${product.name} added to your cart.`);
    } catch (error) {
        showMessage("#cart-message", error.message, true);
    }
}

async function changeQuantity(productId, delta) {
    const item = state.cart.find(
        (entry) => Number(entry.product_id) === Number(productId)
    );

    if (!item) return;

    const newQuantity = Number(item.quantity) + delta;

    try {
        if (newQuantity <= 0) {
            await removeCartItem(productId);
            return;
        }

        // The cart API adds quantities; it has no direct "set quantity" endpoint.
        // Remove the existing item and add the desired quantity instead.
        await request(
            `${API.cart}/cart/${encodeURIComponent(currentUserId())}/items/${productId}`,
            { method: "DELETE" }
        );

        await request(
            `${API.cart}/cart/${encodeURIComponent(currentUserId())}/items`,
            {
                method: "POST",
                body: JSON.stringify({
                    product_id: Number(item.product_id),
                    name: item.name,
                    price: Number(item.price),
                    quantity: newQuantity,
                }),
            }
        );

        await loadCart();
        showMessage("#cart-message", "Cart updated.");
    } catch (error) {
        await loadCart();
        showMessage("#cart-message", error.message, true);
    }
}

async function removeCartItem(productId) {
    try {
        await request(
            `${API.cart}/cart/${encodeURIComponent(currentUserId())}/items/${productId}`,
            { method: "DELETE" }
        );

        await loadCart();
        showMessage("#cart-message", "Item removed.");
    } catch (error) {
        showMessage("#cart-message", error.message, true);
    }
}

async function clearCart() {
    await request(
        `${API.cart}/cart/${encodeURIComponent(currentUserId())}`,
        { method: "DELETE" }
    );
    state.cart = [];
    renderCart();
}

async function loadOrders() {
    const userId = currentUserId();

    if (!userId) {
        showMessage("#checkout-message", "Enter a customer ID first.", true);
        return;
    }

    try {
        const data = await request(
            `${API.orders}/orders/user/${encodeURIComponent(userId)}`
        );

        state.orders = Array.isArray(data) ? data : (data.orders ?? []);
        renderOrders();
    } catch (error) {
        $("#order-list").innerHTML =
            "<p>Could not load order history.</p>";
        showMessage("#checkout-message", error.message, true);
    }
}

function renderOrders() {
    const container = $("#order-list");

    if (!state.orders.length) {
        container.innerHTML = "<p>No orders found for this customer.</p>";
        return;
    }

    container.innerHTML = state.orders.map((order) => {
        const items = order.items ?? [];
        const itemSummary = items.map((item) =>
            `${escapeHtml(item.name)} × ${Number(item.quantity)}`
        ).join(", ");

        return `
            <article class="order-card">
                <div class="order-heading">
                    <strong>Order #${Number(order.id)}</strong>
                    <span class="status ${order.status === "failed" ? "failed" : ""}">
                        ${escapeHtml(order.status)}
                    </span>
                </div>
                <div class="order-details">
                    <div>Placed: ${escapeHtml(order.created_at ?? "Recently")}</div>
                    <div>Items: ${itemSummary || "Order details unavailable"}</div>
                    <div>Total: <strong>${formatPrice(order.total_amount)}</strong></div>
                </div>
            </article>
        `;
    }).join("");
}

async function checkout(event) {
    event.preventDefault();

    if (state.loading) return;

    if (!currentUserId()) {
        showMessage("#checkout-message", "Enter a customer ID.", true);
        return;
    }

    if (!state.cart.length) {
        showMessage("#checkout-message", "Your cart is empty.", true);
        return;
    }

    state.loading = true;
    $("#checkout-button").disabled = true;

    const submitButton = $("#checkout-form button[type='submit']");
    submitButton.disabled = true;
    submitButton.textContent = "Processing…";

    let order = null;
    const reservedItems = [];

    try {
        // Step 1: Reserve stock for each cart item.
        for (const item of state.cart) {
            await request(`${API.inventory}/inventory/reserve`, {
                method: "POST",
                body: JSON.stringify({
                    product_id: Number(item.product_id),
                    quantity: Number(item.quantity),
                }),
            });

            reservedItems.push(item);
        }

        // Step 2: Create the order.
        order = await request(`${API.orders}/orders`, {
            method: "POST",
            body: JSON.stringify({
                user_id: currentUserId(),
                items: state.cart.map((item) => ({
                    product_id: Number(item.product_id),
                    name: item.name,
                    unit_price: Number(item.price),
                    quantity: Number(item.quantity),
                })),
            }),
        });

        // Step 3: Simulate a payment. No card or banking details are used.
        const payment = await request(`${API.payments}/payments`, {
            method: "POST",
            body: JSON.stringify({
                order_id: Number(order.id),
                user_id: currentUserId(),
                amount: Number(order.total_amount),
                simulate_failure: false,
            }),
        });

        if (payment.status !== "succeeded") {
            throw new Error(
                `Payment status: ${payment.status}. Your order may need reconciliation.`
            );
        }

        // Step 4: Clear the cart only after payment succeeds.
        await clearCart();

        showMessage(
            "#checkout-message",
            `Order #${order.id} placed successfully. Payment succeeded.`
        );

        await Promise.all([loadProducts(), loadOrders()]);
    } catch (error) {
        showMessage(
            "#checkout-message",
            `${error.message} Check order, payment and stock records before retrying.`,
            true
        );

        // Best-effort compensation if stock was reserved but order creation failed.
        // This restores stock only when no order was created.
        if (!order && reservedItems.length) {
            for (const item of reservedItems.reverse()) {
                try {
                    await request(`${API.inventory}/inventory/restock`, {
                        method: "POST",
                        body: JSON.stringify({
                            product_id: Number(item.product_id),
                            quantity: Number(item.quantity),
                        }),
                    });
                } catch {
                    console.error(
                        "Stock compensation failed for product",
                        item.product_id
                    );
                }
            }
        }

        await Promise.all([loadProducts(), loadOrders()]);
    } finally {
        state.loading = false;
        $("#checkout-button").disabled = state.cart.length === 0;
        submitButton.disabled = false;
        submitButton.textContent = "Place order & simulate payment";
    }
}

$("#product-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-add]");
    if (button) addToCart(button.dataset.add);
});

$("#cart-items").addEventListener("click", (event) => {
    const increase = event.target.closest("[data-increase]");
    const decrease = event.target.closest("[data-decrease]");
    const remove = event.target.closest("[data-remove]");

    if (increase) changeQuantity(increase.dataset.increase, 1);
    if (decrease) changeQuantity(decrease.dataset.decrease, -1);
    if (remove) removeCartItem(remove.dataset.remove);
});

$("#cart-toggle").addEventListener("click", () => {
    $("#cart").scrollIntoView({ behavior: "smooth" });
});

$("#checkout-button").addEventListener("click", () => {
    $("#checkout").scrollIntoView({ behavior: "smooth" });
});

$("#checkout-form").addEventListener("submit", checkout);
$("#refresh-orders").addEventListener("click", loadOrders);

$("#user-id").addEventListener("change", async () => {
    await loadCart();
    await loadOrders();
});

async function initialize() {
    await loadProducts();
    await loadCart();
    await loadOrders();
}

initialize();