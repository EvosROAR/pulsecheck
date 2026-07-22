const API = "/api/v1";
const TOKEN_KEY = "pulsecheck_token";

function t(key, vars) {
  return window.PulseI18n ? window.PulseI18n.t(key, vars) : key;
}

const state = {
  mode: "login",
  token: localStorage.getItem(TOKEN_KEY),
  user: null,
  monitors: [],
  statsById: {},
  selectedId: null,
  probeRegion: "local",
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
  detailUptime24h: document.getElementById("detail-uptime-24h"),
  detailLatency: document.getElementById("detail-latency"),
  detailP95: document.getElementById("detail-p95"),
  detailStatus: document.getElementById("detail-status"),
  detailChecks: document.getElementById("detail-checks"),
  checksList: document.getElementById("checks-list"),
  sparkline: document.getElementById("latency-sparkline"),
  publicLink: document.getElementById("public-link"),
  toast: document.getElementById("toast"),
  statTotal: document.getElementById("stat-total"),
  statUp: document.getElementById("stat-up"),
  statDown: document.getElementById("stat-down"),
  statLatency: document.getElementById("stat-latency"),
};

function renderProbeNotes() {
  const text = t("settings.probeNote", { region: state.probeRegion || "server" });
  const note = document.getElementById("probe-note");
  const detailNote = document.getElementById("detail-probe-note");
  if (note) note.textContent = text;
  if (detailNote) detailNote.textContent = text;
}

async function loadMeta() {
  try {
    const meta = await fetch("/api/v1/meta").then((r) => r.json());
    state.probeRegion = meta.probe_region || "server";
  } catch {
    state.probeRegion = "server";
  }
  renderProbeNotes();
}

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
  els.authTitle.textContent = t(isLogin ? "auth.titleLogin" : "auth.titleRegister");
  els.authSubtitle.textContent = t(isLogin ? "auth.subLogin" : "auth.subRegister");
  els.authSubmit.textContent = t(isLogin ? "auth.submitLogin" : "auth.submitRegister");
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
      : detail || t("common.error");
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
  const webhookInput = document.getElementById("discord-webhook");
  if (webhookInput) {
    webhookInput.value = state.user.discord_webhook_url || "";
  }
}

async function loadMonitors() {
  const [monitors, stats] = await Promise.all([
    api("/monitors"),
    api("/monitors/stats/summary"),
  ]);
  state.monitors = monitors;
  state.statsById = Object.fromEntries((stats || []).map((s) => [s.monitor_id, s]));
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
    const tone = s?.last_status_tone || (s?.last_status === "up" ? "up" : s?.last_status ? "down" : "unknown");
    const label = s?.last_status_label || s?.last_status || "UNKNOWN";
    const card = document.createElement("button");
    card.type = "button";
    card.className = `monitor-card${m.is_active ? "" : " is-paused"}`;
    card.innerHTML = `
      <span class="status-orb ${tone}"></span>
      <div class="monitor-meta">
        <h4>${escapeHtml(m.name)}</h4>
        <p>${escapeHtml(m.url)}</p>
        ${m.is_active ? "" : `<span class="paused-tag">${t("dash.paused")}</span>`}
      </div>
      <div class="monitor-side">
        <span class="badge ${tone}">${escapeHtml(label)}</span>
        <small>${
          s ? t("dash.uptime", { n: s.uptime_percentage }) : t("dash.noChecksYet")
        }</small>
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

/** Parse API timestamps (UTC) and show them in the viewer's local timezone. */
function formatUserTime(value) {
  if (!value) return "—";
  let raw = String(value).trim();
  if (!/[zZ]$|[+-]\d{2}:\d{2}$/.test(raw)) {
    raw = `${raw}Z`;
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatBytes(bytes) {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function renderInsights(details) {
  const grid = document.getElementById("insights-grid");
  const empty = document.getElementById("insights-error");
  if (!grid || !empty) return;

  if (!details) {
    grid.innerHTML = "";
    empty.hidden = false;
    empty.textContent = t("detail.insightsEmpty");
    return;
  }

  empty.hidden = true;
  const securityPresent = Object.entries(details.security_headers || {})
    .filter(([, ok]) => ok)
    .map(([name]) => name);
  const sslText = details.ssl_checked
    ? details.ssl_valid
      ? `${details.ssl_warning ? "Expiring soon · " : "Valid · "}${details.ssl_days_remaining ?? "?"}d left`
      : details.ssl_error || "Invalid"
    : "N/A";
  const keywordText =
    details.keyword_matched == null ? "—" : details.keyword_matched ? "Matched" : "Missing";
  const cards = [
    { label: "Status", value: details.status_label || "—", warn: false },
    {
      label: "Response Time",
      value: details.response_time_ms != null ? `${Math.round(details.response_time_ms)} ms` : "—",
      warn: false,
    },
    { label: "Response Size", value: formatBytes(details.response_size_bytes), warn: false },
    { label: "Region", value: details.probe_region || "—", warn: false },
    { label: "DNS", value: details.dns_ok ? "OK" : details.dns_error || "Failed", warn: !details.dns_ok },
    { label: "IP", value: (details.ip_addresses || []).join(", ") || "—", warn: false },
    { label: "SSL", value: sslText, warn: Boolean(details.ssl_warning || details.ssl_valid === false) },
    { label: "SSL Issuer", value: details.ssl_issuer || "—", warn: false },
    { label: "Final URL", value: details.final_url || "—", warn: false },
    {
      label: "Redirected",
      value: details.redirected == null ? "—" : details.redirected ? "Yes" : "No",
      warn: false,
    },
    { label: "Keyword", value: keywordText, warn: details.keyword_matched === false },
    { label: "Server", value: details.server || "—", warn: false },
    { label: "CDN", value: details.cdn || "—", warn: false },
    { label: "Tech Stack", value: (details.tech_stack || []).join(", ") || "—", warn: false },
    {
      label: "Security Score",
      value: details.security_score != null ? `${details.security_score}/100` : "—",
      warn: details.security_score != null && details.security_score < 50,
    },
    {
      label: "Security Headers",
      value: securityPresent.length ? securityPresent.join(", ") : "None detected",
      warn: false,
      wide: true,
    },
    { label: "Error Analysis", value: details.error_analysis || "—", warn: false, wide: true },
  ];

  grid.innerHTML = cards
    .map((card) => {
      const wide = card.wide ? " wide" : "";
      const warn = card.warn ? " warn" : "";
      return `<div class="insight-card${wide}${warn}"><span>${escapeHtml(card.label)}</span><strong>${escapeHtml(
        String(card.value),
      )}</strong></div>`;
    })
    .join("");
}

function formatDuration(seconds) {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem ? `${hours}h ${rem}m` : `${hours}h`;
}

function renderIncidents(incidents) {
  const list = document.getElementById("incidents-list");
  if (!list) return;
  if (!incidents.length) {
    list.innerHTML = `<p class="auth-hint">${t("detail.noIncidents")}</p>`;
    return;
  }
  list.innerHTML = incidents
    .map((item) => {
      const tone = item.status_tone || "down";
      const label = item.status_label || "DOWN";
      const when = formatUserTime(item.started_at);
      const dur = item.is_ongoing
        ? t("detail.incidentOngoing")
        : t("detail.incidentDuration", { n: formatDuration(item.duration_seconds) });
      return `
        <div class="check-row">
          <div>
            <strong class="tone-${tone}">${escapeHtml(label)}</strong>
            <small> · ${item.failed_checks} checks · ${escapeHtml(dur)}</small>
          </div>
          <small>${when}</small>
        </div>
      `;
    })
    .join("");
}

function renderSparkline(checks) {
  const svg = els.sparkline;
  if (!svg) return;
  const points = [...checks]
    .reverse()
    .map((c) => c.response_time_ms)
    .filter((v) => typeof v === "number");
  if (points.length < 2) {
    svg.innerHTML = "";
    return;
  }
  const width = 320;
  const height = 72;
  const pad = 8;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = Math.max(max - min, 1);
  const coords = points.map((value, index) => {
    const x = pad + (index / (points.length - 1)) * (width - pad * 2);
    const y = height - pad - ((value - min) / span) * (height - pad * 2);
    return [x, y];
  });
  const line = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${coords[coords.length - 1][0].toFixed(1)},${height - pad} L${coords[0][0].toFixed(
    1,
  )},${height - pad} Z`;
  svg.innerHTML = `
    <path d="${area}" fill="rgba(45, 212, 191, 0.16)"></path>
    <path d="${line}" fill="none" stroke="#2dd4bf" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></path>
  `;
}

function syncDetailActions(monitor) {
  const pauseBtn = document.getElementById("btn-toggle-pause");
  const publicBtn = document.getElementById("btn-toggle-public");
  if (pauseBtn) {
    pauseBtn.textContent = t(monitor.is_active ? "detail.pause" : "detail.resume");
  }
  if (publicBtn) {
    publicBtn.textContent = t(monitor.public_slug ? "detail.disablePublic" : "detail.makePublic");
  }
  if (els.publicLink) {
    if (monitor.public_slug) {
      const url = `${window.location.origin}/status/${monitor.public_slug}`;
      els.publicLink.hidden = false;
      els.publicLink.innerHTML = `${escapeHtml(t("detail.publicLink"))}: <a href="${url}" target="_blank" rel="noopener">${escapeHtml(
        url,
      )}</a>`;
    } else {
      els.publicLink.hidden = true;
      els.publicLink.textContent = "";
    }
  }
}

async function openDetail(id) {
  state.selectedId = id;
  const monitor = state.monitors.find((m) => m.id === id);
  if (!monitor) return;

  els.detailTitle.textContent = monitor.name;
  els.detailUrl.textContent = monitor.url;
  els.detailUrl.href = monitor.url;
  syncDetailActions(monitor);

  const [stats, checks, incidents] = await Promise.all([
    api(`/monitors/${id}/stats`),
    api(`/monitors/${id}/checks?limit=24`),
    api(`/monitors/${id}/incidents?limit=10`),
  ]);
  state.statsById[id] = stats;

  els.detailUptime.textContent = `${stats.uptime_percentage}%`;
  els.detailUptime24h.textContent =
    stats.uptime_24h != null ? `${stats.uptime_24h}%` : "—";
  els.detailLatency.textContent =
    stats.avg_response_time_ms != null ? `${Math.round(stats.avg_response_time_ms)} ms` : "—";
  els.detailP95.textContent =
    stats.p95_response_time_ms != null ? `${Math.round(stats.p95_response_time_ms)} ms` : "—";
  els.detailStatus.textContent = stats.last_status_label || stats.last_status || "—";
  els.detailChecks.textContent = String(stats.total_checks);
  renderInsights(stats.last_insights || checks.find((c) => c.details)?.details || null);
  renderSparkline(checks);
  renderIncidents(incidents || []);

  els.checksList.innerHTML = checks.length
    ? checks
        .map((c) => {
          const when = formatUserTime(c.checked_at);
          const rt = c.response_time_ms != null ? `${Math.round(c.response_time_ms)} ms` : "—";
          const code = c.status_code ?? "—";
          const tone = c.status_tone || (c.is_up ? "up" : "down");
          const label = c.status_label || (c.is_up ? "UP" : "DOWN");
          return `
            <div class="check-row">
              <div>
                <strong class="tone-${tone}">${escapeHtml(label)}</strong>
                <small> · ${code} · ${rt}</small>
              </div>
              <small>${when}</small>
            </div>
          `;
        })
        .join("")
    : `<p class="auth-hint">${t("detail.noHistory")}</p>`;

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
  await loadMeta();
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
      if (!fullName) throw new Error(t("auth.needName"));
      await register(email, password, fullName);
    }
    await login(email, password);
    await enterDashboard();
    showToast(t("toast.welcome"));
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
  showToast(t("toast.logout"));
});

document.getElementById("btn-open-create").addEventListener("click", openCreateModal);
document.getElementById("btn-empty-create").addEventListener("click", openCreateModal);
document.getElementById("btn-refresh").addEventListener("click", async () => {
  await loadMonitors();
  showToast(t("toast.refreshed"));
});

document.getElementById("btn-check-all").addEventListener("click", async () => {
  try {
    const result = await api("/monitors/check-all", { method: "POST" });
    await loadMonitors();
    if (state.selectedId) await openDetail(state.selectedId);
    showToast(t("toast.checkedAll", { n: result.checked }));
  } catch (err) {
    showToast(err.message);
  }
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
    expected_body_contains: document.getElementById("monitor-keyword").value.trim() || null,
  };

  try {
    await api("/monitors", { method: "POST", json: payload });
    closeCreateModal();
    await loadMonitors();
    showToast(t("toast.monitorAdded"));
  } catch (err) {
    els.createError.textContent = err.message;
    els.createError.hidden = false;
  }
});

document.getElementById("btn-run-check").addEventListener("click", async () => {
  if (!state.selectedId) return;
  try {
    const result = await api(`/monitors/${state.selectedId}/check`, { method: "POST" });
    showToast(
      result.is_up
        ? `${result.status_label || "UP"} · ${Math.round(result.response_time_ms)} ms`
        : result.status_label || "DOWN",
    );
    await openDetail(state.selectedId);
    await loadMonitors();
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("btn-delete-monitor").addEventListener("click", async () => {
  if (!state.selectedId) return;
  if (!confirm(t("detail.deleteConfirm"))) return;
  try {
    await api(`/monitors/${state.selectedId}`, { method: "DELETE" });
    closeDrawer();
    await loadMonitors();
    showToast(t("toast.monitorDeleted"));
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("btn-toggle-pause").addEventListener("click", async () => {
  if (!state.selectedId) return;
  const monitor = state.monitors.find((m) => m.id === state.selectedId);
  if (!monitor) return;
  try {
    const updated = await api(`/monitors/${state.selectedId}`, {
      method: "PATCH",
      json: { is_active: !monitor.is_active },
    });
    const idx = state.monitors.findIndex((m) => m.id === updated.id);
    if (idx >= 0) state.monitors[idx] = updated;
    syncDetailActions(updated);
    await loadMonitors();
    showToast(t(updated.is_active ? "toast.resumed" : "toast.paused"));
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("btn-toggle-public").addEventListener("click", async () => {
  if (!state.selectedId) return;
  const monitor = state.monitors.find((m) => m.id === state.selectedId);
  if (!monitor) return;
  try {
    const updated = await api(`/monitors/${state.selectedId}`, {
      method: "PATCH",
      json: { public_enabled: !monitor.public_slug },
    });
    const idx = state.monitors.findIndex((m) => m.id === updated.id);
    if (idx >= 0) state.monitors[idx] = updated;
    syncDetailActions(updated);
    showToast(t(updated.public_slug ? "toast.publicOn" : "toast.publicOff"));
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("btn-export-csv").addEventListener("click", async () => {
  if (!state.selectedId) return;
  try {
    const response = await fetch(`${API}/monitors/${state.selectedId}/export.csv`, {
      headers: state.token ? { Authorization: `Bearer ${state.token}` } : {},
    });
    if (!response.ok) throw new Error(t("common.error"));
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `pulsecheck-${state.selectedId}-checks.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showToast(t("toast.exported"));
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("webhook-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const discord_webhook_url = document.getElementById("discord-webhook").value.trim() || null;
  try {
    state.user = await api("/auth/me", {
      method: "PATCH",
      json: { discord_webhook_url },
    });
    document.getElementById("discord-webhook").value = state.user.discord_webhook_url || "";
    showToast(discord_webhook_url ? t("toast.webhookSaved") : t("toast.webhookCleared"));
  } catch (err) {
    showToast(err.message);
  }
});

window.onLocaleChange = () => {
  setAuthMode(state.mode);
  renderProbeNotes();
  renderDashboard();
  if (state.selectedId) {
    openDetail(state.selectedId);
  }
};

setAuthMode("login");
boot();
