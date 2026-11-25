/* ULTRAKILL Guide - client-side behaviour.
 *
 * Progressive enhancement: every feature here also works without JavaScript through
 * plain HTML forms. With JavaScript the page talks to the JSON API (api.py) with fetch():
 *   - live filtering of the entry lists        GET    /api/entries
 *   - posting tips without reloading           POST   /api/entries/<id>/comments
 *   - deleting entries / tips (admin)          DELETE /api/entries/<id>, /api/comments/<id>
 * Data from the server is always inserted with textContent, never innerHTML (no XSS).
 */
"use strict";

document.documentElement.classList.add("js");

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ?? "";

/* ------------------------------------------------------------------ helpers */

/** fetch() wrapper: sends the CSRF header, parses JSON, throws on HTTP errors. */
async function api(url, { method = "GET", body } = {}) {
  const response = await fetch(url, {
    method,
    headers: {
      Accept: "application/json",
      "X-CSRF-Token": csrfToken,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.error || `Request failed (${response.status})`);
    error.status = response.status;
    error.fields = data?.fields || {};
    throw error;
  }
  return data;
}

/** Create an element with optional class and text in one call. */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/** Small notification in the bottom-right corner (also announced by screen readers). */
function showToast(message, type = "success") {
  const box = document.getElementById("toasts");
  if (!box) return;
  const toast = el("p", `toast toast-${type}`, message);
  box.append(toast);
  dismissLater(toast);
}

function dismissLater(toast, delay = 4500) {
  setTimeout(() => {
    toast.classList.add("is-leaving");
    setTimeout(() => toast.remove(), 300);
  }, delay);
}

/** In-page confirmation dialog (replaces window.confirm). Resolves true or false. */
function confirmAction(text) {
  const dialog = document.getElementById("confirmDialog");
  if (!dialog?.showModal) return Promise.resolve(window.confirm(text));
  document.getElementById("confirmText").textContent = text;
  dialog.returnValue = "";
  dialog.showModal();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
  });
}

/* ------------------------------------------------------------------ navigation */

function initNav() {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.getElementById("site-nav");
  if (!toggle || !nav) return;
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    nav.classList.toggle("is-open", open);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && nav.classList.contains("is-open")) {
      toggle.setAttribute("aria-expanded", "false");
      nav.classList.remove("is-open");
      toggle.focus();
    }
  });
}

/* ------------------------------------------------------------------ live filters */

/** Build one entry card from API data (same markup as templates/_entry_card.html). */
function renderCard(entry) {
  const card = el("article", "entry-card");

  const media = el("div", entry.image_url ? "card-media" : "card-media is-icon");
  const img = el("img");
  img.src = entry.image_url || entry.faction_icon;
  img.alt = "";
  img.loading = "lazy";
  media.append(img);

  const body = el("div", "card-body");
  const kind = entry.is_secret ? "secret" : entry.category === "boss" ? "boss" : "enemy";
  const badge = el("p", "badge", `${entry.faction} // ${kind} `);
  if (entry.is_cyber_grind) {
    const cg = el("span", "badge-cg", "CG");
    cg.title = "Can spawn in the Cyber Grind";
    badge.append(cg);
  }
  const title = el("h2", "card-title");
  const link = el("a", "", entry.name);
  link.href = entry.url;
  title.append(link);

  body.append(badge, title, el("p", "card-lore", entry.lore));
  card.append(media, body);
  return card;
}

function initFilters() {
  const form = document.getElementById("filterForm");
  const grid = document.getElementById("entriesGrid");
  const counter = document.getElementById("resultCount");
  if (!form || !grid) return;

  let timer;
  let lastRequest = 0;

  async function update() {
    const params = new URLSearchParams(new FormData(form));
    // Page-level constraints that are not visible as form fields.
    if (form.dataset.fixedCategory) params.set("category", form.dataset.fixedCategory);
    if (form.dataset.secret) params.set("secret", "1");

    const requestId = ++lastRequest;
    grid.setAttribute("aria-busy", "true");
    try {
      const data = await api(`${form.dataset.api}?${params}`);
      if (requestId !== lastRequest) return; // a newer request already answered
      grid.replaceChildren(
        ...(data.entries.length
          ? data.entries.map(renderCard)
          : [el("p", "empty-state", "No entries match these filters.")])
      );
      counter.textContent = `${data.count} result${data.count === 1 ? "" : "s"}`;
      // Keep the address bar in sync so the filtered view can be bookmarked or shared.
      const visible = new URLSearchParams(new FormData(form));
      history.replaceState(null, "", `${form.action.split("?")[0]}?${visible}`);
    } catch (error) {
      showToast(`Could not load entries: ${error.message}`, "error");
    } finally {
      grid.removeAttribute("aria-busy");
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    update();
  });
  form.addEventListener("change", update);
  form.addEventListener("input", (event) => {
    if (event.target.type !== "search") return;
    clearTimeout(timer);
    timer = setTimeout(update, 250); // debounce: wait until the user stops typing
  });
}

/* ------------------------------------------------------------------ tips (comments) */

function renderComment(comment) {
  const item = el("article", "comment-item is-new");
  item.id = `comment-${comment.id}`;
  const meta = el("div", "comment-meta");
  const time = el("time", "", `${comment.created_at.slice(0, 16)} UTC`);
  time.dateTime = comment.created_at;
  meta.append(el("strong", "", comment.author), time);
  item.append(meta, el("p", "", comment.message));
  return item;
}

function setFieldError(form, name, message) {
  const field = form.elements[name];
  const output = document.getElementById(`${name}Error`);
  if (!field || !output) return;
  output.textContent = message || "";
  if (message) field.setAttribute("aria-invalid", "true");
  else field.removeAttribute("aria-invalid");
}

function initCommentForm() {
  const form = document.getElementById("commentForm");
  const list = document.getElementById("commentsList");
  if (!form || !list) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      author: form.elements.author.value.trim(),
      message: form.elements.message.value.trim(),
    };

    // Quick client-side check; the server validates again (never trust the client).
    const errors = {};
    if (!payload.author) errors.author = "Nickname is required.";
    if (!payload.message) errors.message = "Write a tip before sending.";
    ["author", "message"].forEach((name) => setFieldError(form, name, errors[name]));
    if (Object.keys(errors).length) {
      form.elements[Object.keys(errors)[0]].focus();
      return;
    }

    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const comment = await api(form.dataset.api, { method: "POST", body: payload });
      document.getElementById("noComments")?.remove();
      list.prepend(renderComment(comment));
      const counter = document.getElementById("commentCount");
      counter.textContent = `(${list.querySelectorAll(".comment-item").length})`;
      form.elements.message.value = "";
      showToast("Tip posted. Thanks!");
    } catch (error) {
      Object.entries(error.fields).forEach(([name, message]) => setFieldError(form, name, message));
      showToast(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });
}

/* ------------------------------------------------------------------ deletes (admin) */

function initDeleteForms() {
  document.querySelectorAll("form.js-delete").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!(await confirmAction(form.dataset.confirm))) return;
      try {
        await api(form.dataset.api, { method: "DELETE" });
        if (form.dataset.redirect) {
          window.location.assign(form.dataset.redirect);
          return;
        }
        document.querySelector(form.dataset.remove)?.remove();
        showToast("Deleted.");
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  });
}

/* ------------------------------------------------------------------ start */

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  document.querySelectorAll(".toast").forEach((toast) => dismissLater(toast));
  initFilters();
  initCommentForm();
  initDeleteForms();
});
