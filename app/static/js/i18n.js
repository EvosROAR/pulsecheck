const LANG_KEY = "pulsecheck_lang";

const I18N = {
  id: {
    "nav.login": "Masuk",
    "nav.back": "Kembali",
    "nav.logout": "Keluar",
    "landing.headline": "Rasakan denyut situs Anda.",
    "landing.lede": "Pantau uptime, latency, dan status HTTP dari satu dashboard yang ringkas.",
    "landing.ctaStart": "Mulai gratis",
    "landing.ctaLogin": "Sudah punya akun",
    "landing.live": "Live probe siap",
    "auth.tabLogin": "Masuk",
    "auth.tabRegister": "Daftar",
    "auth.fullName": "Nama lengkap",
    "auth.emailPlaceholder": "kamu@email.com",
    "auth.passwordPlaceholder": "Minimal 8 karakter",
    "auth.titleLogin": "Masuk ke dashboard",
    "auth.titleRegister": "Buat akun PulseCheck",
    "auth.subLogin": "Pantau monitor Anda dan jalankan pengecekan uptime kapan saja.",
    "auth.subRegister": "Daftar gratis, lalu tambahkan URL pertama Anda dalam hitungan detik.",
    "auth.submitLogin": "Masuk",
    "auth.submitRegister": "Daftar",
    "auth.needName": "Nama lengkap wajib diisi",
    "dash.title": "Dashboard",
    "dash.subtitle": "Ringkasan kesehatan semua monitor Anda.",
    "dash.newMonitor": "+ Monitor baru",
    "dash.statTotal": "Total monitor",
    "dash.statUp": "Sedang up",
    "dash.statDown": "Sedang down",
    "dash.statLatency": "Avg latency",
    "dash.monitors": "Monitor",
    "dash.refresh": "Refresh",
    "dash.checkAll": "Check semua",
    "dash.emptyTitle": "Belum ada monitor",
    "dash.emptyCopy": "Tambahkan URL pertama Anda untuk mulai memantau uptime.",
    "dash.addMonitor": "Tambah monitor",
    "dash.noChecksYet": "Belum ada check",
    "dash.uptime": "{n}% uptime",
    "dash.paused": "Paused",
    "settings.title": "Auto-check & Discord alert",
    "settings.autoOn": "Auto aktif",
    "settings.copy":
      "Monitor dicek otomatis sesuai interval. Isi Discord webhook supaya dapat notifikasi saat DOWN / recover.",
    "settings.probeNote":
      "Dicek dari server monitoring ({region}), bukan dari PC Anda. Hasil browser bisa beda karena jaringan/WAF.",
    "settings.webhook": "Discord webhook URL",
    "settings.saveWebhook": "Simpan webhook",
    "settings.webhookHint":
      "Di Discord: Channel Settings → Integrations → Webhooks → New Webhook → Copy URL",
    "detail.eyebrow": "Detail monitor",
    "detail.uptime": "Uptime",
    "detail.uptime24h": "Uptime 24h",
    "detail.avgLatency": "Avg latency",
    "detail.p95": "p95 latency",
    "detail.lastStatus": "Last status",
    "detail.totalChecks": "Total checks",
    "detail.checksHint": "Termasuk auto-check tiap interval.",
    "detail.latencyChart": "Latency (terbaru)",
    "detail.insightsTitle": "Detail probe",
    "detail.insightsEmpty": "Jalankan check untuk melihat DNS, SSL, IP, CDN, dan security headers.",
    "detail.runCheck": "Jalankan check",
    "detail.pause": "Pause",
    "detail.resume": "Resume",
    "detail.exportCsv": "Export CSV",
    "detail.makePublic": "Aktifkan public",
    "detail.disablePublic": "Nonaktifkan public",
    "detail.publicLink": "Halaman publik",
    "detail.delete": "Hapus",
    "detail.history": "Riwayat check",
    "detail.tzHint": "Waktu = zona lokal perangkat Anda.",
    "detail.noHistory": "Belum ada riwayat. Jalankan check pertama.",
    "detail.deleteConfirm": "Hapus monitor ini?",
    "create.title": "Monitor baru",
    "create.name": "Nama",
    "create.namePlaceholder": "Landing page",
    "create.urlPlaceholder": "https://contoh.com",
    "create.interval": "Interval (detik)",
    "create.expected": "Expected status",
    "create.keyword": "Keyword di body (opsional)",
    "create.keywordPlaceholder": "teks yang harus ada di response",
    "common.cancel": "Batal",
    "common.save": "Simpan",
    "common.close": "Tutup",
    "common.error": "Terjadi kesalahan",
    "toast.welcome": "Selamat datang di PulseCheck",
    "toast.logout": "Anda sudah keluar",
    "toast.refreshed": "Dashboard diperbarui",
    "toast.monitorAdded": "Monitor ditambahkan",
    "toast.monitorDeleted": "Monitor dihapus",
    "toast.webhookSaved": "Webhook Discord disimpan",
    "toast.webhookCleared": "Webhook dihapus",
    "toast.paused": "Monitor di-pause",
    "toast.resumed": "Monitor di-resume",
    "toast.checkedAll": "Selesai check {n} monitor",
    "toast.publicOn": "Halaman publik aktif",
    "toast.publicOff": "Halaman publik dimatikan",
    "toast.exported": "CSV diunduh",
  },
  en: {    "nav.login": "Sign in",
    "nav.back": "Back",
    "nav.logout": "Log out",
    "landing.headline": "Feel your site’s pulse.",
    "landing.lede": "Track uptime, latency, and HTTP status from one compact dashboard.",
    "landing.ctaStart": "Start free",
    "landing.ctaLogin": "I already have an account",
    "landing.live": "Live probe ready",
    "auth.tabLogin": "Sign in",
    "auth.tabRegister": "Sign up",
    "auth.fullName": "Full name",
    "auth.emailPlaceholder": "you@email.com",
    "auth.passwordPlaceholder": "At least 8 characters",
    "auth.titleLogin": "Sign in to your dashboard",
    "auth.titleRegister": "Create a PulseCheck account",
    "auth.subLogin": "Watch your monitors and run uptime checks anytime.",
    "auth.subRegister": "Sign up free, then add your first URL in seconds.",
    "auth.submitLogin": "Sign in",
    "auth.submitRegister": "Sign up",
    "auth.needName": "Full name is required",
    "dash.title": "Dashboard",
    "dash.subtitle": "Health overview of all your monitors.",
    "dash.newMonitor": "+ New monitor",
    "dash.statTotal": "Total monitors",
    "dash.statUp": "Currently up",
    "dash.statDown": "Currently down",
    "dash.statLatency": "Avg latency",
    "dash.monitors": "Monitors",
    "dash.refresh": "Refresh",
    "dash.checkAll": "Check all",
    "dash.emptyTitle": "No monitors yet",
    "dash.emptyCopy": "Add your first URL to start tracking uptime.",
    "dash.addMonitor": "Add monitor",
    "dash.noChecksYet": "No checks yet",
    "dash.uptime": "{n}% uptime",
    "dash.paused": "Paused",
    "settings.title": "Auto-check & Discord alerts",
    "settings.autoOn": "Auto on",
    "settings.copy":
      "Monitors are checked automatically by interval. Add a Discord webhook to get DOWN / recovery alerts.",
    "settings.probeNote":
      "Checked from the monitoring server ({region}), not your PC. Browser results can differ due to network/WAF.",
    "settings.webhook": "Discord webhook URL",
    "settings.saveWebhook": "Save webhook",
    "settings.webhookHint":
      "In Discord: Channel Settings → Integrations → Webhooks → New Webhook → Copy URL",
    "detail.eyebrow": "Monitor detail",
    "detail.uptime": "Uptime",
    "detail.uptime24h": "Uptime 24h",
    "detail.avgLatency": "Avg latency",
    "detail.p95": "p95 latency",
    "detail.lastStatus": "Last status",
    "detail.totalChecks": "Total checks",
    "detail.checksHint": "Includes automatic checks every interval.",
    "detail.latencyChart": "Latency (recent)",
    "detail.insightsTitle": "Probe insights",
    "detail.insightsEmpty": "Run a check to see DNS, SSL, IP, CDN, and security headers.",
    "detail.runCheck": "Run check",
    "detail.pause": "Pause",
    "detail.resume": "Resume",
    "detail.exportCsv": "Export CSV",
    "detail.makePublic": "Enable public",
    "detail.disablePublic": "Disable public",
    "detail.publicLink": "Public page",
    "detail.delete": "Delete",
    "detail.history": "Check history",
    "detail.tzHint": "Times use your device timezone.",
    "detail.noHistory": "No history yet. Run the first check.",
    "detail.deleteConfirm": "Delete this monitor?",
    "create.title": "New monitor",
    "create.name": "Name",
    "create.namePlaceholder": "Landing page",
    "create.urlPlaceholder": "https://example.com",
    "create.interval": "Interval (seconds)",
    "create.expected": "Expected status",
    "create.keyword": "Body keyword (optional)",
    "create.keywordPlaceholder": "text that must appear in the response",
    "common.cancel": "Cancel",
    "common.save": "Save",
    "common.close": "Close",
    "common.error": "Something went wrong",
    "toast.welcome": "Welcome to PulseCheck",
    "toast.logout": "You have been logged out",
    "toast.refreshed": "Dashboard refreshed",
    "toast.monitorAdded": "Monitor added",
    "toast.monitorDeleted": "Monitor deleted",
    "toast.webhookSaved": "Discord webhook saved",
    "toast.webhookCleared": "Webhook cleared",
    "toast.paused": "Monitor paused",
    "toast.resumed": "Monitor resumed",
    "toast.checkedAll": "Checked {n} monitors",
    "toast.publicOn": "Public status page enabled",
    "toast.publicOff": "Public status page disabled",
    "toast.exported": "CSV downloaded",
  },
};
function detectLang() {
  const saved = localStorage.getItem(LANG_KEY);
  if (saved === "id" || saved === "en") return saved;
  const browser = (navigator.language || "en").toLowerCase();
  return browser.startsWith("id") ? "id" : "en";
}

window.PulseI18n = {
  lang: detectLang(),
  t(key, vars = {}) {
    const table = I18N[this.lang] || I18N.en;
    let text = table[key] || I18N.en[key] || key;
    Object.entries(vars).forEach(([k, v]) => {
      text = text.replaceAll(`{${k}}`, String(v));
    });
    return text;
  },
  apply() {
    document.documentElement.lang = this.lang;
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = this.t(node.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
      node.setAttribute("placeholder", this.t(node.dataset.i18nPlaceholder));
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
      node.setAttribute("aria-label", this.t(node.dataset.i18nAria));
    });
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.lang === this.lang);
    });
    if (typeof window.onLocaleChange === "function") {
      window.onLocaleChange(this.lang);
    }
  },
  setLang(lang) {
    if (lang !== "id" && lang !== "en") return;
    this.lang = lang;
    localStorage.setItem(LANG_KEY, lang);
    this.apply();
  },
};

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => window.PulseI18n.setLang(btn.dataset.lang));
  });
  window.PulseI18n.apply();
});
