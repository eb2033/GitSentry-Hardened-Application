// API is served under /api on the same origin (proxied by nginx).
const API = "/api";
const list = document.getElementById("list");
const errorEl = document.getElementById("error");

async function load() {
  try {
    const res = await fetch(`${API}/items`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const items = await res.json();
    list.replaceChildren(...items.map((i) => {
      const li = document.createElement("li");
      li.textContent = i.name;
      return li;
    }));
    errorEl.textContent = "";
  } catch (e) {
    errorEl.textContent = `Failed to load items: ${e.message}`;
  }
}

document.getElementById("form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const input = document.getElementById("name");
  try {
    const res = await fetch(`${API}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: input.value }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    input.value = "";
    await load();
  } catch (e) {
    errorEl.textContent = `Failed to add item: ${e.message}`;
  }
});

load();
