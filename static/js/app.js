/**
 * ============================================================
 *  KrishiMitra — Smart Farming AI Agent
 *  Main JavaScript  |  static/js/app.js
 *  Features:
 *    - AI Chat with IBM Watsonx.ai (via Flask backend)
 *    - Dark mode toggle with localStorage persistence
 *    - Farmer profile save/load
 *    - Crop Recommendation Engine UI
 *    - Soil Health Analyser UI
 *    - Weather-Smart Farming UI
 *    - Auto-resizing textarea
 *    - Markdown rendering
 *    - Animated counters
 *    - Toast notifications
 *    - Smooth scroll
 * ============================================================
 */

"use strict";

// ═══════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════
const STATE = {
  conversationHistory: [],
  farmerProfile: {},
  isDark: false,
  selectedWeatherCondition: "sunny",
  isLoading: false,
};

// ═══════════════════════════════════════════════════════════
//  DOM READY
// ═══════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initProfile();
  initNavHighlight();
  initAutoResizeTextarea();
  initCharCounter();
  animateCounters();
  setupEnterToSend();
  console.info("🌾 KrishiMitra — Smart Farming AI Agent loaded.");
});

// ═══════════════════════════════════════════════════════════
//  THEME (Dark / Light)
// ═══════════════════════════════════════════════════════════
function initTheme() {
  const saved = localStorage.getItem("krishimitra_theme") || "light";
  applyTheme(saved);
}

function applyTheme(theme) {
  STATE.isDark = theme === "dark";
  document.documentElement.setAttribute("data-theme", theme);
  const icon = document.getElementById("themeIcon");
  if (icon) {
    icon.className = STATE.isDark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
  }
  localStorage.setItem("krishimitra_theme", theme);
}

function toggleTheme() {
  applyTheme(STATE.isDark ? "light" : "dark");
}

document.getElementById("themeToggle")?.addEventListener("click", toggleTheme);

// ═══════════════════════════════════════════════════════════
//  SMOOTH SCROLL
// ═══════════════════════════════════════════════════════════
function scrollToSection(sectionId) {
  const el = document.getElementById(sectionId);
  if (el) {
    const offset = 72; // navbar height
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top, behavior: "smooth" });
  }
}

// ═══════════════════════════════════════════════════════════
//  NAV HIGHLIGHT (Intersection Observer)
// ═══════════════════════════════════════════════════════════
function initNavHighlight() {
  const sections = document.querySelectorAll("section[id]");
  const navLinks = document.querySelectorAll(".nav-link[data-section]");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.id;
          navLinks.forEach((link) => {
            link.classList.toggle("active", link.dataset.section === id);
          });
        }
      });
    },
    { threshold: 0.3, rootMargin: "-72px 0px 0px 0px" }
  );

  sections.forEach((s) => observer.observe(s));
}

// ═══════════════════════════════════════════════════════════
//  ANIMATED COUNTERS
// ═══════════════════════════════════════════════════════════
function animateCounters() {
  const els = document.querySelectorAll(".hero-stat-number[data-target]");
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseInt(el.dataset.target, 10);
          let current = 0;
          const step = Math.max(1, Math.ceil(target / 30));
          const interval = setInterval(() => {
            current = Math.min(current + step, target);
            el.textContent = current;
            if (current >= target) clearInterval(interval);
          }, 40);
          observer.unobserve(el);
        }
      });
    },
    { threshold: 0.5 }
  );
  els.forEach((el) => observer.observe(el));
}

// ═══════════════════════════════════════════════════════════
//  FARMER PROFILE
// ═══════════════════════════════════════════════════════════
function initProfile() {
  const saved = localStorage.getItem("krishimitra_profile");
  if (saved) {
    try {
      STATE.farmerProfile = JSON.parse(saved);
      populateProfileForm(STATE.farmerProfile);
    } catch (_) {}
  }
}

function populateProfileForm(profile) {
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el && val !== undefined && val !== null) el.value = val;
  };
  set("farmerName", profile.name);
  set("farmerLocation", profile.location);
  set("farmSize", profile.land_acres);
  set("irrigationType", profile.irrigation);
  set("soilType", profile.soil_type);
  set("preferredLanguage", profile.language);
  set("farmerNotes", profile.notes);

  // Restore crop selections
  if (Array.isArray(profile.crops)) {
    document.querySelectorAll(".crop-checkbox").forEach((cb) => {
      cb.checked = profile.crops.includes(cb.value);
    });
  }
}

function saveProfile() {
  const selectedCrops = Array.from(
    document.querySelectorAll(".crop-checkbox:checked")
  ).map((cb) => cb.value);

  STATE.farmerProfile = {
    name: document.getElementById("farmerName")?.value?.trim() || "Farmer",
    location: document.getElementById("farmerLocation")?.value?.trim() || "",
    land_acres: parseFloat(document.getElementById("farmSize")?.value) || 0,
    irrigation: document.getElementById("irrigationType")?.value || "Rainfed",
    soil_type: document.getElementById("soilType")?.value || "",
    language: document.getElementById("preferredLanguage")?.value || "English",
    crops: selectedCrops,
    notes: document.getElementById("farmerNotes")?.value?.trim() || "",
  };

  localStorage.setItem("krishimitra_profile", JSON.stringify(STATE.farmerProfile));

  const msg = document.getElementById("profileSaveMsg");
  if (msg) {
    msg.classList.remove("d-none");
    setTimeout(() => msg.classList.add("d-none"), 4000);
  }

  showToast(
    `Profile saved! Welcome, ${STATE.farmerProfile.name}! 🙏`,
    "success"
  );
}

// ═══════════════════════════════════════════════════════════
//  CHAT — Core Functions
// ═══════════════════════════════════════════════════════════
function setupEnterToSend() {
  const input = document.getElementById("chatInput");
  if (!input) return;
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

function initAutoResizeTextarea() {
  const input = document.getElementById("chatInput");
  if (!input) return;
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });
}

function initCharCounter() {
  const input = document.getElementById("chatInput");
  const counter = document.getElementById("charCount");
  if (!input || !counter) return;
  input.addEventListener("input", () => {
    counter.textContent = `${input.value.length}/1000`;
    counter.style.color =
      input.value.length > 900 ? "var(--danger)" : "var(--text-light)";
  });
}

async function sendMessage() {
  const input = document.getElementById("chatInput");
  const message = input?.value?.trim();
  if (!message || STATE.isLoading) return;

  // Add user message to UI
  addMessageToChat("user", message);
  STATE.conversationHistory.push({ role: "user", content: message });

  // Clear input
  input.value = "";
  input.style.height = "auto";
  document.getElementById("charCount").textContent = "0/1000";

  // Hide suggestions after first message
  const suggestions = document.getElementById("chatSuggestions");
  if (suggestions) suggestions.style.display = "none";

  // Show typing indicator
  showTypingIndicator(true);
  setState(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        conversation_history: STATE.conversationHistory.slice(-20),
        farmer_profile: STATE.farmerProfile,
      }),
    });

    const data = await res.json();
    showTypingIndicator(false);
    setState(false);

    if (data.error) {
      addMessageToChat("bot", `⚠️ Error: ${data.error}`);
    } else {
      const reply = data.response || "I couldn't generate a response. Please try again.";
      addMessageToChat("bot", reply);
      STATE.conversationHistory.push({ role: "assistant", content: reply });
    }
  } catch (err) {
    showTypingIndicator(false);
    setState(false);
    addMessageToChat(
      "bot",
      "⚠️ Connection error. Please check your internet connection and try again."
    );
    console.error("Chat error:", err);
  }
}

function sendSuggestion(text) {
  const input = document.getElementById("chatInput");
  if (input) {
    input.value = text;
    scrollToSection("chat");
    setTimeout(() => sendMessage(), 200);
  }
}

function addMessageToChat(role, content) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const isBot = role === "bot";
  const time = new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const msgEl = document.createElement("div");
  msgEl.className = `message ${isBot ? "bot" : "user"}-message ${
    isBot ? "animate-slideInLeft" : "animate-slideInRight"
  }`;

  const avatarIcon = isBot ? "bi-robot" : "bi-person-fill";
  const avatarClass = isBot ? "bot-avatar" : "user-avatar";
  const rendered = isBot ? renderMarkdown(content) : escapeHtml(content);

  msgEl.innerHTML = `
    <div class="message-avatar ${avatarClass}">
      <i class="bi ${avatarIcon}"></i>
    </div>
    <div class="message-content">
      <div class="message-bubble">${rendered}</div>
      <div class="message-time">${time}</div>
    </div>
  `;

  container.appendChild(msgEl);
  container.scrollTop = container.scrollHeight;
}

function showTypingIndicator(show) {
  const indicator = document.getElementById("typingIndicator");
  if (indicator) {
    indicator.classList.toggle("d-none", !show);
    if (show) {
      const container = document.getElementById("chatMessages");
      if (container) container.scrollTop = container.scrollHeight;
    }
  }
}

function setState(loading) {
  STATE.isLoading = loading;
  const btn = document.getElementById("sendBtn");
  if (btn) {
    btn.disabled = loading;
    btn.innerHTML = loading
      ? '<span class="ai-spinner"></span>'
      : '<i class="bi bi-send-fill"></i>';
  }
}

function clearChat() {
  STATE.conversationHistory = [];
  const container = document.getElementById("chatMessages");
  if (!container) return;
  container.innerHTML = `
    <div class="message bot-message animate-slideInLeft">
      <div class="message-avatar bot-avatar"><i class="bi bi-robot"></i></div>
      <div class="message-content">
        <div class="message-bubble">
          <p class="mb-1">🌾 Chat cleared! How can I help you today?</p>
          <p class="mb-0 text-muted" style="font-size:12px">Ask me anything about farming.</p>
        </div>
        <div class="message-time">Just now</div>
      </div>
    </div>`;
  const suggestions = document.getElementById("chatSuggestions");
  if (suggestions) suggestions.style.display = "";
  showToast("Chat cleared.", "info");
}

function copyLastResponse() {
  const bubbles = document.querySelectorAll(".bot-message .message-bubble");
  if (!bubbles.length) { showToast("No response to copy.", "warning"); return; }
  const last = bubbles[bubbles.length - 1];
  navigator.clipboard
    .writeText(last.innerText)
    .then(() => showToast("Response copied to clipboard!", "success"))
    .catch(() => showToast("Could not copy.", "warning"));
}

// ═══════════════════════════════════════════════════════════
//  MARKDOWN RENDERER (simple, no external lib)
// ═══════════════════════════════════════════════════════════
function renderMarkdown(text) {
  let html = escapeHtml(text);

  // Tables
  html = html.replace(/\|(.+)\|\n\|[-| ]+\|\n((?:\|.+\|\n?)+)/g, (match, header, rows) => {
    const ths = header.split("|").filter(Boolean).map((h) => `<th>${h.trim()}</th>`).join("");
    const trs = rows.trim().split("\n").map((row) => {
      const tds = row.split("|").filter(Boolean).map((d) => `<td>${d.trim()}</td>`).join("");
      return `<tr>${tds}</tr>`;
    }).join("");
    return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
  });

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Headings
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");
  // Unordered lists
  html = html.replace(/^[\*\-] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
  // Paragraph breaks
  html = html.replace(/\n{2,}/g, "</p><p>");
  html = html.replace(/\n/g, "<br />");
  // Clean up nested
  html = html.replace(/<\/ul><ul>/g, "");
  return `<p>${html}</p>`;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ═══════════════════════════════════════════════════════════
//  CROP RECOMMENDATION ENGINE
// ═══════════════════════════════════════════════════════════
async function getCropRecommendations() {
  const payload = {
    season: document.getElementById("cropSeason")?.value,
    soil_type: document.getElementById("cropSoilType")?.value,
    rainfall: parseInt(document.getElementById("rainfallSlider")?.value, 10),
    temperature: parseInt(document.getElementById("tempSlider")?.value, 10),
    region: document.getElementById("cropRegion")?.value,
  };

  const resultsEl = document.getElementById("cropResults");
  resultsEl.innerHTML = buildLoadingHTML("Analysing your farm conditions...");

  try {
    const res = await fetch("/api/crop-recommendation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    renderCropResults(data);
  } catch (err) {
    resultsEl.innerHTML = errorHTML("Could not fetch recommendations. Please try again.");
    console.error(err);
  }
}

function renderCropResults(data) {
  const el = document.getElementById("cropResults");
  const recs = data.recommendations || [];

  const cards = recs.map((r) => `
    <div class="col-sm-6">
      <div class="rec-card" onclick="askAbout('${r.crop} cultivation guide')">
        <div class="d-flex justify-content-between align-items-start">
          <div class="rec-crop-name">🌾 ${r.crop}</div>
          <span class="badge ${r.soil_match ? "bg-success" : "bg-secondary"}" style="font-size:10px">
            ${r.soil_match ? "✓ Soil Match" : "Check Soil"}
          </span>
        </div>
        <div class="rec-detail mt-1">Season: <strong>${r.season}</strong></div>
        <div class="rec-detail">Water: ${r.water_need} &bull; pH: ${r.recommended_pH}</div>
        <div class="rec-detail">Nutrients: ${r.nutrients}</div>
      </div>
    </div>`).join("");

  el.innerHTML = `
    <div class="result-card animate-fadeInUp">
      <div class="result-card-header">
        <i class="bi bi-flower1 text-success me-2"></i>Recommended Crops (${recs.length} found)
      </div>
      <div class="result-card-body">
        <div class="row g-2 mb-3">${cards}</div>
      </div>
    </div>
    <div class="result-card animate-fadeInUp" style="animation-delay:.15s">
      <div class="result-card-header">
        <i class="bi bi-robot text-primary me-2"></i>AI Personalized Advice
      </div>
      <div class="result-card-body">
        <div class="ai-narrative">${renderMarkdown(data.ai_narrative || "")}</div>
        <button class="btn btn-outline-primary btn-sm mt-3" onclick="askAbout('crop rotation plan for my region')">
          <i class="bi bi-chat-dots me-1"></i>Ask AI for more details
        </button>
      </div>
    </div>`;
}

// ═══════════════════════════════════════════════════════════
//  SOIL HEALTH ANALYSER
// ═══════════════════════════════════════════════════════════
async function analyseSoil() {
  const payload = {
    ph: parseFloat(document.getElementById("phSlider")?.value),
    nitrogen: parseFloat(document.getElementById("soilN")?.value),
    phosphorus: parseFloat(document.getElementById("soilP")?.value),
    potassium: parseFloat(document.getElementById("soilK")?.value),
    organic_carbon: parseFloat(document.getElementById("ocSlider")?.value),
    crop: document.getElementById("soilCrop")?.value,
  };

  const resultsEl = document.getElementById("soilResults");
  resultsEl.innerHTML = buildLoadingHTML("Analysing soil health parameters...");

  try {
    const res = await fetch("/api/soil-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    renderSoilResults(data);
  } catch (err) {
    resultsEl.innerHTML = errorHTML("Soil analysis failed. Please try again.");
    console.error(err);
  }
}

function renderSoilResults(data) {
  const el = document.getElementById("soilResults");
  const score = data.score || 0;
  const ringClass =
    score >= 85 ? "score-excellent" :
    score >= 70 ? "score-good" :
    score >= 50 ? "score-fair" : "score-poor";

  const issues = (data.issues || []).map((i) =>
    `<li class="text-danger"><i class="bi bi-exclamation-triangle-fill me-2"></i>${i}</li>`
  ).join("") || "<li class='text-success'>No critical issues found!</li>";

  const actions = (data.recommended_actions || []).map((a) =>
    `<li><i class="bi bi-check2-circle text-success me-2"></i>${a}</li>`
  ).join("") || "<li>Maintain current practices.</li>";

  el.innerHTML = `
    <div class="result-card animate-fadeInUp">
      <div class="result-card-header">
        <i class="bi bi-layers text-warning me-2"></i>Soil Health Score
      </div>
      <div class="result-card-body text-center">
        <div class="health-score-ring ${ringClass}">${score}</div>
        <h5 class="mb-0">${data.health_rating}</h5>
        <p class="text-muted small mt-1">Out of 100 — ${data.parameters ? `pH ${data.parameters.pH} &bull; N:${data.parameters.Nitrogen} &bull; P:${data.parameters.Phosphorus} &bull; K:${data.parameters.Potassium}` : ""}</p>
      </div>
    </div>
    <div class="result-card animate-fadeInUp" style="animation-delay:.1s">
      <div class="result-card-header"><i class="bi bi-exclamation-diamond text-danger me-2"></i>Issues Detected</div>
      <div class="result-card-body"><ul class="mb-0">${issues}</ul></div>
    </div>
    <div class="result-card animate-fadeInUp" style="animation-delay:.2s">
      <div class="result-card-header"><i class="bi bi-check2-all text-success me-2"></i>Recommended Actions</div>
      <div class="result-card-body"><ul class="mb-0">${actions}</ul></div>
    </div>
    <div class="result-card animate-fadeInUp" style="animation-delay:.3s">
      <div class="result-card-header"><i class="bi bi-robot text-primary me-2"></i>AI Detailed Plan</div>
      <div class="result-card-body">
        <div class="ai-narrative">${renderMarkdown(data.ai_narrative || "")}</div>
      </div>
    </div>`;
}

// ═══════════════════════════════════════════════════════════
//  WEATHER ADVICE
// ═══════════════════════════════════════════════════════════
function selectWeather(btn, condition) {
  document.querySelectorAll(".weather-btn").forEach((b) =>
    b.classList.remove("active")
  );
  btn.classList.add("active");
  STATE.selectedWeatherCondition = condition;
}

async function getWeatherAdvice() {
  const payload = {
    condition: STATE.selectedWeatherCondition,
    temperature: parseInt(document.getElementById("weatherTempSlider")?.value, 10),
    rainfall_mm: parseInt(document.getElementById("weatherRainSlider")?.value, 10),
    season: document.getElementById("weatherSeason")?.value,
    crop: document.getElementById("weatherCrop")?.value,
  };

  const resultsEl = document.getElementById("weatherResults");
  resultsEl.innerHTML = buildLoadingHTML("Generating weather-smart advice...");

  try {
    const res = await fetch("/api/weather-advice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    renderWeatherResults(data, payload);
  } catch (err) {
    resultsEl.innerHTML = errorHTML("Weather advice request failed. Please try again.");
    console.error(err);
  }
}

function renderWeatherResults(data, payload) {
  const el = document.getElementById("weatherResults");
  const alertClass = {
    high: "alert-high",
    medium: "alert-medium",
    normal: "alert-normal",
  }[data.alert_level] || "alert-normal";

  const alertLabel = {
    high: "⚠️ High Alert",
    medium: "⚡ Moderate Alert",
    normal: "✅ Normal",
  }[data.alert_level] || "Normal";

  const weatherEmoji = {
    sunny: "☀️", cloudy: "☁️", rainy: "🌧️",
    "heavy rain": "⛈️", drought: "🏜️", foggy: "🌫️",
  }[payload.condition] || "⛅";

  el.innerHTML = `
    <div class="result-card animate-fadeInUp">
      <div class="result-card-header">
        <i class="bi bi-thermometer-sun text-info me-2"></i>Weather Summary
      </div>
      <div class="result-card-body">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div>
            <span style="font-size:2rem">${weatherEmoji}</span>
            <span class="fw-bold ms-2 text-capitalize">${payload.condition}</span>
          </div>
          <span class="alert-badge ${alertClass}">${alertLabel}</span>
        </div>
        <div class="d-flex gap-3 mt-2 flex-wrap">
          <span class="badge bg-secondary">🌡️ ${payload.temperature}°C</span>
          <span class="badge bg-secondary">🌧️ ${payload.rainfall_mm}mm/week</span>
          <span class="badge bg-secondary">🌱 ${payload.crop}</span>
          <span class="badge bg-secondary">📅 ${payload.season}</span>
        </div>
      </div>
    </div>
    <div class="result-card animate-fadeInUp" style="animation-delay:.15s">
      <div class="result-card-header"><i class="bi bi-robot text-primary me-2"></i>AI Weather-Smart Advice</div>
      <div class="result-card-body">
        <div class="ai-narrative">${renderMarkdown(data.advice || "")}</div>
        <button class="btn btn-outline-info btn-sm mt-3" onclick="askAbout('weather resistant farming practices for ${payload.crop}')">
          <i class="bi bi-chat-dots me-1"></i>Get More Weather Tips
        </button>
      </div>
    </div>`;
}

// ═══════════════════════════════════════════════════════════
//  QUICK CHAT HELPERS
// ═══════════════════════════════════════════════════════════
function askAbout(topic) {
  scrollToSection("chat");
  setTimeout(() => {
    const input = document.getElementById("chatInput");
    if (input) {
      input.value = `Tell me about ${topic}`;
      input.dispatchEvent(new Event("input"));
      sendMessage();
    }
  }, 400);
}

function askAboutSchemes() {
  sendSuggestion(
    "Tell me about the best government schemes for small farmers in India and how to apply for them."
  );
  scrollToSection("chat");
}

// ═══════════════════════════════════════════════════════════
//  TOAST NOTIFICATIONS
// ═══════════════════════════════════════════════════════════
function showToast(message, type = "info") {
  const toast = document.getElementById("appToast");
  const body = document.getElementById("toastBody");
  if (!toast || !body) return;

  const colorMap = {
    success: "bg-success",
    warning: "bg-warning text-dark",
    danger: "bg-danger",
    info: "bg-primary",
  };
  toast.className = `toast align-items-center text-white border-0 ${colorMap[type] || "bg-primary"}`;
  body.textContent = message;

  const bsToast = bootstrap.Toast.getOrCreateInstance(toast, { delay: 3500 });
  bsToast.show();
}

// ═══════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════
function buildLoadingHTML(msg) {
  return `
    <div class="result-card animate-fadeInUp">
      <div class="result-card-body text-center py-4">
        <div class="ai-spinner mb-3" style="width:36px;height:36px;border-width:3px;margin:0 auto"></div>
        <p class="text-muted mb-0">${msg}</p>
        <div class="mt-3">
          <div class="skeleton" style="width:80%;margin:0 auto"></div>
          <div class="skeleton" style="width:65%;margin:8px auto"></div>
          <div class="skeleton" style="width:75%;margin:0 auto"></div>
        </div>
      </div>
    </div>`;
}

function errorHTML(msg) {
  return `
    <div class="result-card">
      <div class="result-card-body text-center py-4 text-danger">
        <i class="bi bi-exclamation-circle fs-2 mb-2"></i>
        <p class="mb-0">${msg}</p>
      </div>
    </div>`;
}
