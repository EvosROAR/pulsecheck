const API = "/api/v1";
const TOKEN_KEY = "pulsecheck_token";

const state = {
  mode: "login",
  token: localStorage.getItem(TOKEN_KEY),
  user: null,
  monitors: [],
  statsById: {},
  selectedId: null,
};

const els = {
  views: {
    landing: document.getElementById("view-landing"),
    auth: document.getElementById("view-auth"),
    dashboard: document.getElementById("view-dashboard"),
  },
  authForm: document.getElementById("auth-form"),
  authTitle: document.getElementById("auth-title"),
  authSubtitle: document.getElementById("auth-subtitle"),
  authSubmit: document.getElementById("auth-submit"),
  authError: document.getElementById("auth-error"),
  userChip: document.getElementById("user-chip"),
  monitorsList: document.getElementById("monitors-list"),
  monitorsEmpty: document.getElementById("monitors-empty"),
  createModal: document.getElementById("create-modal"),
  createForm: document.getElementById("create-form"),
  createError: document.getElementById("create-error"),
  drawer: document.getElementById("detail-drawer"),
  detailTitle: document.getElementById("detail-title"),
  detailUrl: document.getElementById("detail-url"),
  detailUptime: document.getElementById("detail-uptime"),
  detailLatency: document.getElementById("detail-latency"),
  detailStatus: document.getElementById("detail-status"),
  detailChecks: document.getElementById("detail-checks"),
  checksList: document.getElementById("checks-list"),
  toast: document.getElementById("toast"),
  statTotal: document.getElementById("stat-total"),
  statUp: document.getElementById("stat-up"),
  statDown: document.getElementById("stat-down"),
  statLatency: document.getElementById("stat-latency"),
};

function showToast(message) {
  els.toast.textContent = message;
  els.toast.hidden = false;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => {
    els.toast.hidden = true;
  }, 2600);
}

function showView(name) {
  Object.entries(els.views).forEach(([key, node]) => {
    node.classList.toggle("is-active", key === name);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setAuthMode(mode) {
  state.mode = mode;
  document.body.classList.toggle("mode-register", mode === "register");
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.mode === mode);
  });
  const isLogin = mode === "login";
  els.authTitle.textContent = isLogin ? "Masuk ke dashboard" : "Buat akun PulseCheck";
  els.authSubtitle.textContent = isLogin
    ? "Pantau monitor Anda dan jalankan pengecekan uptime kapan saja."
    : "Daftar gratis, lalu tambahkan URL pertama Anda dalam hitungan detik.";
  els.authSubmit.textContent = isLogin ? "Masuk" : "Daftar";
  document.getElementById("password").autocomplete = isLogin
    ? "current-password"
    : "new-password";
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (options.json) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API}${path}`, {
    ...options,
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
  });

  if (response.status === 204) return null;

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg).join(", ")
      : detail || "Terjadi kesalahan";
    throw new Error(message);
  }
  return data;
}

async function register(email, password, fullName) {
  await api("/auth/register", {
    method: "POST",
    json: { email, password, full_name: fullName },
  });
}

async function login(email, password) {
  const body = new URLSearchParams({
    username: email,
    password,
  });
  const data = await api("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  state.token = data.access_token;
  localStorage.setItem(TOKEN_KEY, state.token);
}

async function loadMe() {
  state.user = await api("/auth/me");
  els.userChip.textContent = state.user.full_name || state.user.email;
}

async function loadMonitors() {
  state.monitors = await api("/monitors");
  const stats = await Promise.all(
    state.monitors.map(async (m) => {
      try {
        const s = await api(`/monitors/${m.id}/stats`);
        return [m.id, s];
      } catch {
        return [m.id, null];
      }
    }),
  );
  state.statsById = Object.fromEntries(stats);
  renderDashboard();
}

function renderDashboard() {
  const monitors = state.monitors;
  els.statTotal.textContent = String(monitors.length);

  let up = 0;
  let down = 0;
  const latencies = [];

  monitors.forEach((m) => {
    const s = state.statsById[m.id];
    if (s?.last_status === "up") up += 1;
    else if (s?.last_status === "down") down += 1;
    if (typeof s?.avg_response_time_ms === "number") latencies.push(s.avg_response_time_ms);
  });

  els.statUp.textContent = String(up);
  els.statDown.textContent = String(down);
  els.statLatency.textContent = latencies.length
    ? `${Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length)} ms`
    : "—";

  const empty = monitors.length === 0;
  els.monitorsEmpty.hidden = !empty;
  els.monitorsList.hidden = empty;
  els.monitorsList.innerHTML = "";

  monitors.forEach((m) => {
    const s = state.statsById[m.id];
    const status = s?.last_status || "unknown";
    const card = document.createElement("button");
    card.type = "button";
    card.className = "monitor-card";
    card.innerHTML = `
      <span class="status-orb ${status}"></span>
      <div class="monitor-meta">
        <h4>${escapeHtml(m.name)}</h4>
        <p>${escapeHtml(m.url)}</p>
      </div>
      <div class="monitor-side">
        <span class="badge ${status}">${status}</span>
        <small>${s ? `${s.uptime_percentage}% uptime` : "Belum ada check"}</small>
      </div>
    `;
    card.addEventListener("click", () => openDetail(m.id));
    els.monitorsList.appendChild(card);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function openDetail(id) {
  state.selectedId = id;
  const monitor = state.monitors.find((m) => m.id === id);
  if (!monitor) return;

  els.detailTitle.textContent = monitor.name;
  els.detailUrl.textContent = monitor.url;
  els.detailUrl.href = monitor.url;

  const [stats, checks] = await Promise.all([
    api(`/monitors/${id}/stats`),
    api(`/monitors/${id}/checks?limit=12`),
  ]);
  state.statsById[id] = stats;

  els.detailUptime.textContent = `${stats.uptime_percentage}%`;
  els.detailLatency.textContent =
    stats.avg_response_time_ms != null ? `${Math.round(stats.avg_response_time_ms)} ms` : "—";
  els.detailStatus.textContent = stats.last_status || "—";
  els.detailChecks.textContent = String(stats.total_checks);

  els.checksList.innerHTML = checks.length
    ? checks
        .map((c) => {
          const when = new Date(c.checked_at).toLocaleString("id-ID");
          const rt = c.response_time_ms != null ? `${Math.round(c.response_time_ms)} ms` : "—";
          return `
            <div class="check-row">
              <div>
                <strong class="${c.is_up ? "tone-up" : "tone-down"}">${c.is_up ? "UP" : "DOWN"}</strong>
                <small> · ${c.status_code ?? "no status"} · ${rt}</small>
              </div>
              <small>${when}</small>
            </div>
          `;
        })
        .join("")
    : `<p class="auth-hint">Belum ada riwayat. Jalankan check pertama.</p>`;

  els.drawer.classList.add("is-open");
  els.drawer.setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  els.drawer.classList.remove("is-open");
  els.drawer.setAttribute("aria-hidden", "true");
  state.selectedId = null;
}

function openCreateModal() {
  els.createError.hidden = true;
  els.createForm.reset();
  document.getElementById("monitor-interval").value = "60";
  document.getElementById("monitor-status").value = "200";
  els.createModal.classList.add("is-open");
  els.createModal.setAttribute("aria-hidden", "false");
}

function closeCreateModal() {
  els.createModal.classList.remove("is-open");
  els.createModal.setAttribute("aria-hidden", "true");
}

async function enterDashboard() {
  showView("dashboard");
  await loadMe();
  await loadMonitors();
}

async function boot() {
  if (!state.token) {
    showView("landing");
    return;
  }
  try {
    await enterDashboard();
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    state.token = null;
    showView("landing");
  }
}

/* Events */
document.querySelectorAll("[data-goto]").forEach((node) => {
  node.addEventListener("click", (event) => {
    event.preventDefault();
    const target = node.dataset.goto;
    if (target === "auth") {
      setAuthMode(node.dataset.mode || "login");
      showView("auth");
      return;
    }
    if (target === "dashboard" && state.token) {
      showView("dashboard");
      return;
    }
    showView(target);
  });
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => setAuthMode(tab.dataset.mode));
});

els.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  els.authError.hidden = true;
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const fullName = document.getElementById("full_name").value.trim();

  try {
    els.authSubmit.disabled = true;
    if (state.mode === "register") {
      if (!fullName) throw new Error("Nama lengkap wajib diisi");
      await register(email, password, fullName);
    }
    await login(email, password);
    await enterDashboard();
    showToast("Selamat datang di PulseCheck");
  } catch (err) {
    els.authError.textContent = err.message;
    els.authError.hidden = false;
  } finally {
    els.authSubmit.disabled = false;
  }
});

document.getElementById("btn-logout").addEventListener("click", () => {
  state.token = null;
  state.user = null;
  state.monitors = [];
  localStorage.removeItem(TOKEN_KEY);
  showView("landing");
  showToast("Anda sudah keluar");
});

document.getElementById("btn-open-create").addEventListener("click", openCreateModal);
document.getElementById("btn-empty-create").addEventListener("click", openCreateModal);
document.getElementById("btn-refresh").addEventListener("click", async () => {
  await loadMonitors();
  showToast("Dashboard diperbarui");
});

document.querySelectorAll("[data-close-modal]").forEach((node) => {
  node.addEventListener("click", closeCreateModal);
});
document.querySelectorAll("[data-close-drawer]").forEach((node) => {
  node.addEventListener("click", closeDrawer);
});

els.createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  els.createError.hidden = true;
  const payload = {
    name: document.getElementById("monitor-name").value.trim(),
    url: document.getElementById("monitor-url").value.trim(),
    interval_seconds: Number(document.getElementById("monitor-interval").value || 60),
    expected_status: Number(document.getElementById("monitor-status").value || 200),
  };

  try {
    await api("/monitors", { method: "POST", json: payload });
    closeCreateModal();
    await loadMonitors();
    showToast("Monitor ditambahkan");
  } catch (err) {
    els.createError.textContent = err.message;
    els.createError.hidden = false;
  }
});

document.getElementById("btn-run-check").addEventListener("click", async () => {
  if (!state.selectedId) return;
  try {
    const result = await api(`/monitors/${state.selectedId}/check`, { method: "POST" });
    showToast(result.is_up ? `UP · ${Math.round(result.response_time_ms)} ms` : "DOWN");
    await openDetail(state.selectedId);
    await loadMonitors();
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("btn-delete-monitor").addEventListener("click", async () => {
  if (!state.selectedId) return;
  if (!confirm("Hapus monitor ini?")) return;
  try {
    await api(`/monitors/${state.selectedId}`, { method: "DELETE" });
    closeDrawer();
    await loadMonitors();
    showToast("Monitor dihapus");
  } catch (err) {
    showToast(err.message);
  }
});

setAuthMode("login");
boot();
