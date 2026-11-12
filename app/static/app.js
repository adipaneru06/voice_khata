/**
 * Voice Khata — Single Page Application logic
 * Complete Shop Owner Authentication, Registration, Google Maps & Dashboard System
 */

// ---------------------------------------------------------------------------
// Global Variables & Configuration
// ---------------------------------------------------------------------------
let SHOP_NAME = "My Shop";
let authToken = localStorage.getItem("khata_token") || null;
let currentRole = localStorage.getItem("khata_role") || "guest"; // "guest" | "owner" | "admin"
let currentOwner = null;
let currentShop = null;

// Application State
const state = {
  // Voice Khata Ledger State
  customers: [],
  currentView: "home", // "home" | "confirm" | "ledger" | "auth" | "otp" | "wizard" | "dashboard" | "admin"
  previousView: "home",
  currentCustomerId: null,
  currentCustomerName: null,
  currentCustomerBalance: 0,
  selectedKind: "credit", // "credit" | "cash" | "payment"
  rawTranscript: "",
  mediaRecorder: null,
  audioChunks: [],
  recordingInterval: null,
  recordingSeconds: 0,
  isSaving: false,
  lastAudioBlob: null,

  // Auth & Wizard State
  authTab: "login", // "login" | "register"
  otpChannel: "email", // "email" | "phone"
  otpRecipient: "",
  otpTimerInterval: null,
  otpExpiresSeconds: 300,
  otpCooldownInterval: null,
  otpCooldownSeconds: 45,
  wizardStep: 1,
  wizardCoords: { lat: 28.6139, lng: 77.2090 },

  // Admin State
  adminTab: "owners", // "owners" | "shops" | "logs"
};

// Map instances
let wizardMap = null;
let wizardMarker = null;
let dashOverviewMap = null;
let dashOverviewMarker = null;
let dashEditMap = null;
let dashEditMarker = null;

// ---------------------------------------------------------------------------
// Toast Notification Helper
// ---------------------------------------------------------------------------
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  const bgColors = {
    success: "bg-green-950/90 border-green-500 text-green-200",
    error: "bg-red-950/90 border-red-500 text-red-200",
    warning: "bg-amber-950/90 border-amber-500 text-amber-200",
    info: "bg-indigo-950/90 border-indigo-500 text-indigo-200",
  };
  const icons = {
    success: "check_circle",
    error: "error",
    warning: "warning",
    info: "info",
  };

  toast.className = `pointer-events-auto flex items-center gap-2 px-4 py-3 rounded-xl border backdrop-blur-md shadow-2xl text-[13px] font-medium transition-all duration-300 transform translate-y-2 opacity-0 ${bgColors[type] || bgColors.info}`;
  toast.innerHTML = `
    <span class="material-symbols-outlined text-[18px] shrink-0">${icons[type] || "info"}</span>
    <span class="flex-1 leading-tight">${escapeHtml(message)}</span>
    <button type="button" class="text-white/60 hover:text-white cursor-pointer ml-1 text-base leading-none">✕</button>
  `;

  const closeBtn = toast.querySelector("button");
  closeBtn.addEventListener("click", () => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  });

  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.remove("opacity-0", "translate-y-2");
  });

  // Auto-dismiss after 4.5 seconds
  setTimeout(() => {
    if (toast.parentElement) {
      toast.classList.add("opacity-0", "translate-y-2");
      setTimeout(() => toast.remove(), 300);
    }
  }, 4500);
}

// ---------------------------------------------------------------------------
// Authenticated Fetch Helper
// ---------------------------------------------------------------------------
async function apiFetch(url, options = {}) {
  options.headers = options.headers || {};
  if (authToken) {
    options.headers["Authorization"] = `Bearer ${authToken}`;
  }
  if (options.body && !(options.body instanceof FormData) && typeof options.body === "object") {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  const res = await fetch(url, options);
  if (res.status === 401 && !url.includes("/api/auth/login") && !url.includes("/api/admin/login")) {
    // Session expired or invalid
    clearAuthSession();
    showToast("Session expired. Please sign in again.", "warning");
    switchView("auth");
    throw new Error("Unauthorized");
  }
  return res;
}

function clearAuthSession() {
  authToken = null;
  currentRole = "guest";
  currentOwner = null;
  currentShop = null;
  localStorage.removeItem("khata_token");
  localStorage.removeItem("khata_role");
  updateHeaderAuthUI();
}

// ---------------------------------------------------------------------------
// Error Notification Helpers
// ---------------------------------------------------------------------------
let currentRetryCallback = null;

function showError(message, retryCallback = null) {
  const banner = document.getElementById("error-banner");
  const msgEl = document.getElementById("error-message");
  const retryBtn = document.getElementById("error-retry-btn");
  if (!banner || !msgEl) return;

  msgEl.textContent = message;
  banner.classList.remove("hidden");

  if (retryCallback && typeof retryCallback === "function") {
    currentRetryCallback = retryCallback;
    if (retryBtn) retryBtn.classList.remove("hidden");
  } else {
    currentRetryCallback = null;
    if (retryBtn) retryBtn.classList.add("hidden");
  }
}

function clearError() {
  const banner = document.getElementById("error-banner");
  if (!banner) return;
  banner.classList.add("hidden");
  const retryBtn = document.getElementById("error-retry-btn");
  if (retryBtn) retryBtn.classList.add("hidden");
  currentRetryCallback = null;
}

const errorCloseBtn = document.getElementById("error-close-btn");
if (errorCloseBtn) {
  errorCloseBtn.addEventListener("click", clearError);
}

const errorRetryBtn = document.getElementById("error-retry-btn");
if (errorRetryBtn) {
  errorRetryBtn.addEventListener("click", () => {
    const cb = currentRetryCallback;
    clearError();
    if (cb && typeof cb === "function") cb();
  });
}

// ---------------------------------------------------------------------------
// View Switching Logic
// ---------------------------------------------------------------------------
function switchView(viewName) {
  if (state.currentView !== viewName) {
    state.previousView = state.currentView;
  }
  state.currentView = viewName;
  clearError();
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Hide all view containers
  const viewMap = {
    home: document.getElementById("view-home"),
    confirm: document.getElementById("view-confirm"),
    ledger: document.getElementById("view-ledger"),
    auth: document.getElementById("view-auth"),
    otp: document.getElementById("view-otp"),
    wizard: document.getElementById("view-wizard"),
    dashboard: document.getElementById("view-dashboard"),
    admin: document.getElementById("view-admin"),
  };

  Object.values(viewMap).forEach((el) => {
    if (el) el.classList.add("hidden");
  });

  const headerBackBtn = document.getElementById("header-back-btn");
  const headerTitle = document.getElementById("header-title");
  const shopNameHeader = document.getElementById("shop-name-header");

  if (viewMap[viewName]) {
    viewMap[viewName].classList.remove("hidden");
  }

  // View-specific setup
  if (viewName === "home") {
    if (headerBackBtn) headerBackBtn.classList.add("hidden");
    if (headerTitle) headerTitle.textContent = "Ledger Dashboard";
    if (shopNameHeader) shopNameHeader.textContent = currentShop ? currentShop.shop_name : SHOP_NAME;
    setVoiceSubState("idle");
    loadCustomers();
    loadRecentTransactions();
  } else if (viewName === "confirm") {
    if (headerBackBtn) headerBackBtn.classList.remove("hidden");
    if (headerTitle) headerTitle.textContent = "Confirm Entry";
    if (shopNameHeader) shopNameHeader.textContent = "Review & Save";
    validateConfirmForm();
  } else if (viewName === "ledger") {
    if (headerBackBtn) headerBackBtn.classList.remove("hidden");
    if (headerTitle) headerTitle.textContent = state.currentCustomerName || "Customer Ledger";
    if (shopNameHeader) shopNameHeader.textContent = "Running Balance";
  } else if (viewName === "auth") {
    if (headerBackBtn) headerBackBtn.classList.remove("hidden");
    if (headerTitle) headerTitle.textContent = "Shop Owner Portal";
    if (shopNameHeader) shopNameHeader.textContent = "Sign In / Register";
    renderSavedAccounts();
  } else if (viewName === "otp") {
    if (headerBackBtn) headerBackBtn.classList.remove("hidden");
    if (headerTitle) headerTitle.textContent = "Account Verification";
    if (shopNameHeader) shopNameHeader.textContent = "Security Code";
    focusFirstOtpBox();
  } else if (viewName === "wizard") {
    if (headerBackBtn) headerBackBtn.classList.add("hidden");
    if (headerTitle) headerTitle.textContent = "Shop Registration Wizard";
    if (shopNameHeader) shopNameHeader.textContent = "4-Step Setup";
    renderWizardStep(state.wizardStep);
  } else if (viewName === "dashboard") {
    if (headerBackBtn) headerBackBtn.classList.remove("hidden");
    if (headerTitle) headerTitle.textContent = "Shop Dashboard";
    if (shopNameHeader) shopNameHeader.textContent = currentShop ? currentShop.shop_name : SHOP_NAME;
    loadDashboardData();
  } else if (viewName === "admin") {
    if (headerBackBtn) headerBackBtn.classList.remove("hidden");
    if (headerTitle) headerTitle.textContent = "Admin Portal";
    if (shopNameHeader) shopNameHeader.textContent = "Platform Management";
    loadAdminStats();
    loadAdminOwners();
  }

  updateHeaderAuthUI();
}

// Header Back Button Handler
const headerBackBtn = document.getElementById("header-back-btn");
if (headerBackBtn) {
  headerBackBtn.addEventListener("click", () => {
    if (state.currentView === "confirm" || state.currentView === "ledger") {
      switchView("home");
    } else if (state.currentView === "auth" || state.currentView === "dashboard" || state.currentView === "admin") {
      switchView("home");
    } else if (state.currentView === "otp") {
      switchView("auth");
    } else {
      switchView("home");
    }
  });
}

// ---------------------------------------------------------------------------
// Header User Profile Menu & Auth Status UI
// ---------------------------------------------------------------------------
function updateHeaderAuthUI() {
  const btnLogin = document.getElementById("btn-header-login");
  const btnProfile = document.getElementById("btn-header-profile");
  const roleBadge = document.getElementById("role-badge");
  const btnAdmin = document.getElementById("btn-header-admin");
  const dropdownAdmin = document.getElementById("dropdown-btn-admin");
  const ownerNameEl = document.getElementById("header-owner-name");
  const initialsEl = document.getElementById("header-avatar-initials");
  const dropNameEl = document.getElementById("dropdown-user-name");
  const dropEmailEl = document.getElementById("dropdown-user-email");

  if (!authToken || !currentOwner) {
    if (btnLogin) btnLogin.classList.remove("hidden");
    if (btnProfile) btnProfile.classList.add("hidden");
    if (roleBadge) roleBadge.classList.add("hidden");
    if (btnAdmin) btnAdmin.classList.add("hidden");
    if (dropdownAdmin) dropdownAdmin.classList.add("hidden");
  } else {
    if (btnLogin) btnLogin.classList.add("hidden");
    if (btnProfile) btnProfile.classList.remove("hidden");

    const initials = currentOwner.full_name
      ? currentOwner.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
      : "O";

    if (initialsEl) initialsEl.textContent = initials;
    if (ownerNameEl) ownerNameEl.textContent = currentOwner.full_name || "Owner";
    if (dropNameEl) dropNameEl.textContent = currentOwner.full_name || "Shop Owner";
    if (dropEmailEl) dropEmailEl.textContent = currentOwner.email || currentOwner.mobile_number || "";

    if (currentOwner.role === "admin") {
      if (roleBadge) {
        roleBadge.textContent = "Admin";
        roleBadge.className = "text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-400 border border-amber-500/30";
        roleBadge.classList.remove("hidden");
      }
      if (btnAdmin) btnAdmin.classList.remove("hidden");
      if (dropdownAdmin) dropdownAdmin.classList.remove("hidden");
    } else {
      if (roleBadge) {
        roleBadge.textContent = "Owner";
        roleBadge.className = "text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-950/80 text-indigo-400 border border-indigo-500/30";
        roleBadge.classList.remove("hidden");
      }
      if (btnAdmin) btnAdmin.classList.add("hidden");
      if (dropdownAdmin) dropdownAdmin.classList.add("hidden");
    }
  }
}

// User Profile dropdown toggle
const btnHeaderProfile = document.getElementById("btn-header-profile");
const userDropdown = document.getElementById("header-user-dropdown");
if (btnHeaderProfile && userDropdown) {
  btnHeaderProfile.addEventListener("click", (e) => {
    e.stopPropagation();
    userDropdown.classList.toggle("hidden");
  });
  document.addEventListener("click", () => {
    userDropdown.classList.add("hidden");
  });
}

// Dropdown button handlers
document.getElementById("dropdown-btn-dashboard")?.addEventListener("click", () => switchView("dashboard"));
document.getElementById("dropdown-btn-khata")?.addEventListener("click", () => switchView("home"));
document.getElementById("dropdown-btn-admin")?.addEventListener("click", () => switchView("admin"));
document.getElementById("dropdown-btn-logout")?.addEventListener("click", handleLogout);
document.getElementById("btn-header-login")?.addEventListener("click", () => switchView("auth"));
document.getElementById("btn-header-store")?.addEventListener("click", () => {
  if (authToken && currentOwner) {
    switchView("dashboard");
  } else {
    switchView("auth");
  }
});
document.getElementById("btn-header-admin")?.addEventListener("click", () => switchView("admin"));

// ---------------------------------------------------------------------------
// Saved Accounts Manager (Local Storage - Non-sensitive metadata only)
// ---------------------------------------------------------------------------
function getSavedAccounts() {
  try {
    const raw = localStorage.getItem("khata_saved_accounts");
    return raw ? JSON.parse(raw) : [];
  } catch (err) {
    return [];
  }
}

function saveAccountLocally(account) {
  try {
    let accounts = getSavedAccounts();
    // Deduplicate by identifier
    accounts = accounts.filter((a) => a.identifier.toLowerCase() !== account.identifier.toLowerCase());
    accounts.unshift({
      identifier: account.identifier,
      name: account.name || "Shop Owner",
      shopName: account.shopName || "My Shop",
      avatar: account.name ? account.name.slice(0, 2).toUpperCase() : "SO",
      savedAt: new Date().toISOString(),
    });
    // Keep max 5 accounts
    if (accounts.length > 5) accounts = accounts.slice(0, 5);
    localStorage.setItem("khata_saved_accounts", JSON.stringify(accounts));
  } catch (err) {
    console.warn("Could not save account to localStorage:", err);
  }
}

function removeSavedAccount(identifier) {
  try {
    let accounts = getSavedAccounts();
    accounts = accounts.filter((a) => a.identifier.toLowerCase() !== identifier.toLowerCase());
    localStorage.setItem("khata_saved_accounts", JSON.stringify(accounts));
    renderSavedAccounts();
    showToast("Saved account removed.", "info");
  } catch (err) {
    console.warn("Error removing saved account:", err);
  }
}

function renderSavedAccounts() {
  const container = document.getElementById("saved-accounts-section");
  const listEl = document.getElementById("saved-accounts-list");
  if (!container || !listEl) return;

  const accounts = getSavedAccounts();
  if (accounts.length === 0) {
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");
  listEl.innerHTML = accounts
    .map(
      (a) => `
    <div class="flex items-center justify-between p-2 rounded-lg bg-surface-container hover:bg-surface-container-high transition-colors group">
      <div class="flex items-center gap-2.5 min-w-0 cursor-pointer flex-1" onclick="selectSavedAccount('${escapeHtml(a.identifier)}')">
        <div class="w-8 h-8 rounded-full bg-indigo-600/30 text-indigo-300 font-semibold text-[11px] flex items-center justify-center shrink-0 border border-indigo-500/20">
          ${escapeHtml(a.avatar)}
        </div>
        <div class="flex flex-col min-w-0">
          <span class="font-medium text-white text-[12px] truncate">${escapeHtml(a.name)} • ${escapeHtml(a.shopName)}</span>
          <span class="text-[11px] text-on-surface-variant font-mono truncate">${escapeHtml(a.identifier)}</span>
        </div>
      </div>
      <button type="button" onclick="event.stopPropagation(); removeSavedAccount('${escapeHtml(a.identifier)}')" class="text-on-surface-variant/40 hover:text-red-400 p-1 rounded transition-colors cursor-pointer" title="Remove saved account">
        <span class="material-symbols-outlined text-[16px]">close</span>
      </button>
    </div>
  `
    )
    .join("");
}

window.selectSavedAccount = function (identifier) {
  const input = document.getElementById("login-identifier");
  const pwdInput = document.getElementById("login-password");
  if (input) {
    input.value = identifier;
    if (pwdInput) pwdInput.focus();
    showToast(`Selected saved account: ${identifier}`, "info");
  }
};

window.removeSavedAccount = removeSavedAccount;

// ---------------------------------------------------------------------------
// Authentication Controller (Login, Register, Logout)
// ---------------------------------------------------------------------------

// Tab Switching (Login vs Register)
const tabBtnLogin = document.getElementById("tab-btn-login");
const tabBtnRegister = document.getElementById("tab-btn-register");
const cardLogin = document.getElementById("card-auth-login");
const cardRegister = document.getElementById("card-auth-register");
const cardForgot = document.getElementById("card-auth-forgot");

tabBtnLogin?.addEventListener("click", () => {
  state.authTab = "login";
  tabBtnLogin.className = "flex-1 py-2 text-center rounded-lg font-medium text-body-sm transition-all bg-surface-container text-white shadow-sm cursor-pointer";
  tabBtnRegister.className = "flex-1 py-2 text-center rounded-lg font-medium text-body-sm transition-all text-on-surface-variant hover:text-white cursor-pointer";
  cardLogin.classList.remove("hidden");
  cardRegister.classList.add("hidden");
  cardForgot.classList.add("hidden");
});

tabBtnRegister?.addEventListener("click", () => {
  state.authTab = "register";
  tabBtnRegister.className = "flex-1 py-2 text-center rounded-lg font-medium text-body-sm transition-all bg-surface-container text-white shadow-sm cursor-pointer";
  tabBtnLogin.className = "flex-1 py-2 text-center rounded-lg font-medium text-body-sm transition-all text-on-surface-variant hover:text-white cursor-pointer";
  cardRegister.classList.remove("hidden");
  cardLogin.classList.add("hidden");
  cardForgot.classList.add("hidden");
});

// Password Visibility Toggles
document.getElementById("btn-toggle-login-pwd")?.addEventListener("click", () => {
  const input = document.getElementById("login-password");
  const icon = document.getElementById("icon-login-eye");
  if (!input || !icon) return;
  const isPwd = input.type === "password";
  input.type = isPwd ? "text" : "password";
  icon.textContent = isPwd ? "visibility_off" : "visibility";
});

document.getElementById("btn-toggle-reg-pwd")?.addEventListener("click", () => {
  const input = document.getElementById("reg-password");
  const icon = document.getElementById("icon-reg-eye");
  if (!input || !icon) return;
  const isPwd = input.type === "password";
  input.type = isPwd ? "text" : "password";
  icon.textContent = isPwd ? "visibility_off" : "visibility";
});

// Password Strength Meter
const regPwdInput = document.getElementById("reg-password");
regPwdInput?.addEventListener("input", (e) => {
  const val = e.target.value;
  const bar = document.getElementById("pwd-strength-bar");
  const text = document.getElementById("pwd-strength-text");
  if (!bar || !text) return;

  let score = 0;
  if (val.length >= 8) score++;
  if (/[A-Z]/.test(val)) score++;
  if (/[a-z]/.test(val)) score++;
  if (/\d/.test(val)) score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;

  if (score <= 1) {
    bar.style.width = "20%";
    bar.className = "h-full transition-all duration-300 rounded-full bg-red-500";
    text.textContent = "Strength: Weak";
    text.className = "text-red-400";
  } else if (score <= 3) {
    bar.style.width = "60%";
    bar.className = "h-full transition-all duration-300 rounded-full bg-amber-500";
    text.textContent = "Strength: Medium";
    text.className = "text-amber-400";
  } else {
    bar.style.width = "100%";
    bar.className = "h-full transition-all duration-300 rounded-full bg-green-500";
    text.textContent = "Strength: Strong";
    text.className = "text-green-400";
  }
});

// Form: Login Submission
const formLogin = document.getElementById("form-login");
formLogin?.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();

  const identifier = document.getElementById("login-identifier").value.trim();
  const password = document.getElementById("login-password").value;
  const rememberMe = document.getElementById("login-remember-me").checked;
  const saveAccount = document.getElementById("login-save-account").checked;
  const submitBtn = document.getElementById("btn-submit-login");

  if (!identifier || !password) {
    showError("Please enter email/phone and password.");
    return;
  }

  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">sync</span><span>Signing In...</span>`;

    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password, remember_me: rememberMe }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Authentication failed.");
    }

    // Success
    authToken = data.token;
    localStorage.setItem("khata_token", authToken);
    localStorage.setItem("khata_role", data.owner.role);

    currentOwner = data.owner;
    currentShop = data.shop;

    if (saveAccount) {
      saveAccountLocally({
        identifier,
        name: currentOwner.full_name,
        shopName: currentShop ? currentShop.shop_name : "My Shop",
      });
    }

    showToast(`Welcome back, ${currentOwner.full_name}!`, "success");

    // Route according to status
    if (data.next_step === "verify_email" || data.next_step === "verify_phone") {
      state.otpChannel = data.next_step === "verify_phone" ? "phone" : "email";
      state.otpRecipient = state.otpChannel === "phone" ? currentOwner.mobile_number : currentOwner.email;
      switchView("otp");
    } else if (data.next_step === "wizard" || !data.has_shop) {
      switchView("wizard");
    } else {
      SHOP_NAME = currentShop.shop_name;
      document.getElementById("shop-name-header").textContent = SHOP_NAME;
      switchView("dashboard");
    }
  } catch (err) {
    console.error("Login error:", err);
    showError(err.message || "Failed to log in.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-[18px]">login</span><span>Sign In to Shop</span>`;
  }
});

// Form: Registration Submission
const formRegister = document.getElementById("form-register");
formRegister?.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();

  const fullName = document.getElementById("reg-fullname").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const mobile = document.getElementById("reg-mobile").value.trim();
  const password = document.getElementById("reg-password").value;
  const confirmPassword = document.getElementById("reg-confirm-password").value;
  const terms = document.getElementById("reg-terms").checked;
  const submitBtn = document.getElementById("btn-submit-register");

  if (!fullName || !email || !mobile || !password) {
    showError("Please fill all required fields.");
    return;
  }

  if (password !== confirmPassword) {
    showError("Passwords do not match.");
    return;
  }

  if (!terms) {
    showError("Please accept the Terms of Service.");
    return;
  }

  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">sync</span><span>Creating Account...</span>`;

    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: fullName,
        email,
        mobile_number: mobile,
        password,
        confirm_password: confirmPassword,
        terms_accepted: terms,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Registration failed.");
    }

    showToast("Account created successfully! Please verify OTP.", "success");

    // Automatically sign in with credentials to establish session for OTP verification
    const loginRes = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: email, password }),
    });

    if (loginRes.ok) {
      const loginData = await loginRes.json();
      authToken = loginData.token;
      currentOwner = loginData.owner;
      localStorage.setItem("khata_token", authToken);
      localStorage.setItem("khata_role", currentOwner.role);
    }

    state.otpChannel = "email";
    state.otpRecipient = email;

    // Display dev_otp banner if returned in dev mode
    if (data.dev_otp) {
      const devBanner = document.getElementById("dev-otp-banner");
      const devCodeEl = document.getElementById("dev-otp-code");
      if (devBanner && devCodeEl) {
        devCodeEl.textContent = data.dev_otp;
        devBanner.classList.remove("hidden");
      }
    }

    startOtpExpiryTimer();
    startOtpCooldownTimer(45);
    switchView("otp");
  } catch (err) {
    console.error("Registration error:", err);
    showError(err.message || "Registration failed.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-[18px]">how_to_reg</span><span>Register & Continue</span>`;
  }
});

// Logout Handler
async function handleLogout() {
  try {
    if (authToken) {
      await apiFetch("/api/auth/logout", { method: "POST" });
    }
  } catch (err) {
    console.warn("Logout error:", err);
  } finally {
    clearAuthSession();
    showToast("Signed out successfully.", "info");
    switchView("home");
  }
}

// ---------------------------------------------------------------------------
// Forgot Password Flow
// ---------------------------------------------------------------------------
const btnForgotTrigger = document.getElementById("btn-forgot-password-trigger");
btnForgotTrigger?.addEventListener("click", () => {
  cardLogin.classList.add("hidden");
  cardRegister.classList.add("hidden");
  cardForgot.classList.remove("hidden");
  document.getElementById("forgot-step-1").classList.remove("hidden");
  document.getElementById("forgot-step-2").classList.add("hidden");
});

document.getElementById("btn-close-forgot-card")?.addEventListener("click", () => {
  cardForgot.classList.add("hidden");
  cardLogin.classList.remove("hidden");
});

document.getElementById("btn-send-reset-otp")?.addEventListener("click", async () => {
  const identifier = document.getElementById("forgot-identifier").value.trim();
  if (!identifier) {
    showError("Please enter your registered email or phone.");
    return;
  }

  try {
    const res = await fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to send reset code.");
    }

    document.getElementById("forgot-step-1").classList.add("hidden");
    document.getElementById("forgot-step-2").classList.remove("hidden");

    let notice = `Reset code sent to ${identifier}!`;
    if (data.dev_otp) notice += ` (Dev OTP: ${data.dev_otp})`;
    document.getElementById("forgot-otp-notice").textContent = notice;
    showToast("Reset code sent! Check your email or phone.", "success");
  } catch (err) {
    showError(err.message || "Could not send reset code.");
  }
});

document.getElementById("btn-submit-password-reset")?.addEventListener("click", async () => {
  const identifier = document.getElementById("forgot-identifier").value.trim();
  const otpCode = document.getElementById("forgot-otp-input").value.trim();
  const newPassword = document.getElementById("forgot-new-pwd").value;
  const confirmPassword = document.getElementById("forgot-confirm-pwd").value;

  if (!otpCode || !newPassword || !confirmPassword) {
    showError("Please fill all password reset fields.");
    return;
  }

  if (newPassword !== confirmPassword) {
    showError("New passwords do not match.");
    return;
  }

  try {
    const res = await fetch("/api/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        identifier,
        otp_code: otpCode,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to reset password.");
    }

    showToast("Password updated successfully! Please sign in with your new password.", "success");
    cardForgot.classList.add("hidden");
    cardLogin.classList.remove("hidden");
    document.getElementById("login-identifier").value = identifier;
    document.getElementById("login-password").value = "";
  } catch (err) {
    showError(err.message || "Password reset failed.");
  }
});

// Switch to Admin Login directly from card
document.getElementById("btn-switch-admin-login")?.addEventListener("click", () => {
  const emailInput = document.getElementById("login-identifier");
  const pwdInput = document.getElementById("login-password");
  if (emailInput && pwdInput) {
    emailInput.value = "admin@voicekhata.com";
    pwdInput.value = "Admin@123456";
    showToast("Prefilled default administrator credentials for review.", "info");
  }
});

// ---------------------------------------------------------------------------
// OTP Verification Controller
// ---------------------------------------------------------------------------
const otpInputs = document.querySelectorAll(".otp-input");

otpInputs.forEach((input, index) => {
  input.addEventListener("input", (e) => {
    const val = e.target.value;
    if (val.length === 1 && index < otpInputs.length - 1) {
      otpInputs[index + 1].focus();
    }
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Backspace" && !input.value && index > 0) {
      otpInputs[index - 1].focus();
    }
  });

  input.addEventListener("paste", (e) => {
    e.preventDefault();
    const paste = (e.clipboardData || window.clipboardData).getData("text").trim();
    if (/^\d{6}$/.test(paste)) {
      paste.split("").forEach((char, i) => {
        if (otpInputs[i]) otpInputs[i].value = char;
      });
      otpInputs[5].focus();
    }
  });
});

function getEnteredOtp() {
  return Array.from(otpInputs).map((i) => i.value.trim()).join("");
}

function focusFirstOtpBox() {
  otpInputs.forEach((i) => (i.value = ""));
  if (otpInputs[0]) otpInputs[0].focus();
}

function startOtpExpiryTimer() {
  if (state.otpTimerInterval) clearInterval(state.otpTimerInterval);
  state.otpExpiresSeconds = 300; // 5 minutes

  const textEl = document.getElementById("otp-expires-text");

  state.otpTimerInterval = setInterval(() => {
    state.otpExpiresSeconds--;
    if (state.otpExpiresSeconds <= 0) {
      clearInterval(state.otpTimerInterval);
      if (textEl) textEl.innerHTML = `<span class="material-symbols-outlined text-[14px] text-red-400">error</span><span class="text-red-400 font-semibold">OTP Expired</span>`;
      showToast("OTP expired. Please request a new code.", "error");
    } else {
      const mins = Math.floor(state.otpExpiresSeconds / 60);
      const secs = state.otpExpiresSeconds % 60;
      const formatted = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      if (textEl) {
        textEl.innerHTML = `<span class="material-symbols-outlined text-[14px]">timer</span><span>Expires in ${formatted}</span>`;
      }
    }
  }, 1000);
}

function startOtpCooldownTimer(seconds = 45) {
  if (state.otpCooldownInterval) clearInterval(state.otpCooldownInterval);
  state.otpCooldownSeconds = seconds;

  const btnResend = document.getElementById("btn-resend-otp");
  const countEl = document.getElementById("resend-cooldown-count");
  if (btnResend) btnResend.disabled = true;

  state.otpCooldownInterval = setInterval(() => {
    state.otpCooldownSeconds--;
    if (state.otpCooldownSeconds <= 0) {
      clearInterval(state.otpCooldownInterval);
      if (btnResend) {
        btnResend.disabled = false;
        btnResend.innerHTML = `Resend OTP`;
      }
    } else {
      if (countEl) countEl.textContent = state.otpCooldownSeconds;
    }
  }, 1000);
}

// Method toggle: Email vs Phone OTP
document.getElementById("otp-method-email")?.addEventListener("click", async () => {
  state.otpChannel = "email";
  document.getElementById("otp-method-email").className = "py-1.5 rounded-md text-[12px] font-medium transition-colors bg-indigo-600 text-white cursor-pointer";
  document.getElementById("otp-method-phone").className = "py-1.5 rounded-md text-[12px] font-medium transition-colors text-on-surface-variant hover:text-white cursor-pointer";
  await resendOtpAction();
});

document.getElementById("otp-method-phone")?.addEventListener("click", async () => {
  state.otpChannel = "phone";
  document.getElementById("otp-method-phone").className = "py-1.5 rounded-md text-[12px] font-medium transition-colors bg-indigo-600 text-white cursor-pointer";
  document.getElementById("otp-method-email").className = "py-1.5 rounded-md text-[12px] font-medium transition-colors text-on-surface-variant hover:text-white cursor-pointer";
  await resendOtpAction();
});

async function resendOtpAction() {
  clearError();
  const endpoint = state.otpChannel === "phone" ? "/api/otp/send-phone" : "/api/otp/send-email";
  try {
    const res = await apiFetch(endpoint, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not resend OTP");

    showToast(`New OTP sent via ${state.otpChannel.toUpperCase()}!`, "info");
    startOtpExpiryTimer();
    startOtpCooldownTimer(45);

    if (data.dev_otp) {
      const devBanner = document.getElementById("dev-otp-banner");
      const devCodeEl = document.getElementById("dev-otp-code");
      if (devBanner && devCodeEl) {
        devCodeEl.textContent = data.dev_otp;
        devBanner.classList.remove("hidden");
      }
    }
  } catch (err) {
    showError(err.message || "Failed to resend OTP.");
  }
}

document.getElementById("btn-resend-otp")?.addEventListener("click", resendOtpAction);

// Verify OTP Action
document.getElementById("btn-submit-verify-otp")?.addEventListener("click", async () => {
  clearError();
  const code = getEnteredOtp();
  if (code.length !== 6) {
    showError("Please enter all 6 digits of the OTP code.");
    return;
  }

  const endpoint = state.otpChannel === "phone" ? "/api/otp/verify-phone" : "/api/otp/verify-email";
  const submitBtn = document.getElementById("btn-submit-verify-otp");

  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">sync</span><span>Verifying...</span>`;

    const res = await apiFetch(endpoint, {
      method: "POST",
      body: { otp_code: code },
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "OTP verification failed.");

    showToast("Verification successful!", "success");

    // Fetch updated status
    const statusRes = await apiFetch("/api/shop-owner/status");
    if (statusRes.ok) {
      const statusData = await statusRes.json();
      currentOwner = statusData.owner;
      currentShop = statusData.shop;

      if (!statusData.has_shop) {
        switchView("wizard");
      } else {
        SHOP_NAME = currentShop.shop_name;
        document.getElementById("shop-name-header").textContent = SHOP_NAME;
        switchView("dashboard");
      }
    } else {
      switchView("wizard");
    }
  } catch (err) {
    console.error("OTP verification error:", err);
    showError(err.message || "Invalid or expired OTP code.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-[18px]">verified_user</span><span>Verify & Continue</span>`;
  }
});

document.getElementById("btn-cancel-otp")?.addEventListener("click", () => {
  handleLogout();
});

document.getElementById("btn-copy-dev-otp")?.addEventListener("click", () => {
  const code = document.getElementById("dev-otp-code")?.textContent;
  if (code) {
    code.split("").forEach((char, i) => {
      if (otpInputs[i]) otpInputs[i].value = char;
    });
    showToast("Dev OTP auto-filled!", "success");
  }
});

// ---------------------------------------------------------------------------
// 4-Step Shop Owner Registration Wizard Controller
// ---------------------------------------------------------------------------
function renderWizardStep(step) {
  state.wizardStep = step;
  const labelEl = document.getElementById("wizard-step-label");
  const pctEl = document.getElementById("wizard-progress-percent");

  const steps = [
    { title: "Owner Verification", pct: "25%" },
    { title: "Shop Information", pct: "50%" },
    { title: "Shop Location & Maps", pct: "75%" },
    { title: "Review & Submit", pct: "100%" },
  ];

  if (labelEl) labelEl.textContent = `Step ${step} of 4: ${steps[step - 1].title}`;
  if (pctEl) pctEl.textContent = steps[step - 1].pct;

  // Update track pills
  for (let i = 1; i <= 4; i++) {
    const pill = document.getElementById(`step-pill-${i}`);
    const name = document.getElementById(`step-name-${i}`);
    const pane = document.getElementById(`wizard-pane-${i}`);

    if (pill) {
      pill.className = i <= step ? "h-2 rounded-full bg-indigo-600 transition-all" : "h-2 rounded-full bg-surface-container-high transition-all";
    }
    if (name) {
      name.className = i <= step ? "text-white font-semibold" : "text-on-surface-variant/70 font-medium";
    }
    if (pane) {
      pane.classList.toggle("hidden", i !== step);
    }
  }

  // Populate data per step
  if (step === 1) {
    if (currentOwner) {
      document.getElementById("wz-owner-name").value = currentOwner.full_name || "";
      document.getElementById("wz-owner-mobile").value = currentOwner.mobile_number || "";
      document.getElementById("wz-owner-email").value = currentOwner.email || "";
      document.getElementById("wz-status-email").textContent = currentOwner.email_verified ? "Verified" : "Pending";
      document.getElementById("wz-status-phone").textContent = currentOwner.phone_verified ? "Verified" : "Active";
    }
  } else if (step === 3) {
    initWizardMap();
  } else if (step === 4) {
    populateWizardReview();
  }
}

// Step 1 -> Step 2
document.getElementById("btn-wz-next-1")?.addEventListener("click", async () => {
  // Save step 1 progress
  try {
    await apiFetch("/api/shop-owner/wizard/step", {
      method: "POST",
      body: { step: 1, data: { owner_name: currentOwner?.full_name } },
    });
  } catch (err) {
    console.warn("Could not save step 1 progress:", err);
  }
  renderWizardStep(2);
});

// Step 2 Category Dropdown Toggle
document.getElementById("wz-shop-category")?.addEventListener("change", (e) => {
  const box = document.getElementById("wz-custom-category-box");
  if (box) box.classList.toggle("hidden", e.target.value !== "Other");
});

// Step 2 -> Back to 1
document.getElementById("btn-wz-back-2")?.addEventListener("click", () => renderWizardStep(1));

// Step 2 -> Step 3
document.getElementById("btn-wz-next-2")?.addEventListener("click", async () => {
  const shopName = document.getElementById("wz-shop-name").value.trim();
  const category = document.getElementById("wz-shop-category").value;
  const customCat = document.getElementById("wz-custom-category")?.value.trim();
  const mobile = document.getElementById("wz-shop-mobile").value.trim();

  if (!shopName) {
    showError("Please enter your Shop Name.");
    return;
  }
  if (category === "Other" && !customCat) {
    showError("Please specify your Custom Category.");
    return;
  }
  if (!mobile) {
    showError("Please enter your Shop Contact Mobile.");
    return;
  }

  // Save step 2 progress
  try {
    await apiFetch("/api/shop-owner/wizard/step", {
      method: "POST",
      body: {
        step: 2,
        data: {
          shop_name: shopName,
          shop_category: category === "Other" ? customCat : category,
          shop_description: document.getElementById("wz-shop-desc").value.trim(),
          shop_mobile_number: mobile,
          alternative_contact_number: document.getElementById("wz-shop-alt-phone").value.trim(),
          opening_time: document.getElementById("wz-opening-time").value,
          closing_time: document.getElementById("wz-closing-time").value,
          weekly_closing_day: document.getElementById("wz-weekly-closing").value,
        },
      },
    });
  } catch (err) {
    console.warn("Could not save step 2 progress:", err);
  }

  renderWizardStep(3);
});

// Step 3 -> Back to 2
document.getElementById("btn-wz-back-3")?.addEventListener("click", () => renderWizardStep(2));

// Step 3 -> Step 4
document.getElementById("btn-wz-next-3")?.addEventListener("click", async () => {
  const address = document.getElementById("wz-address").value.trim();
  const city = document.getElementById("wz-city").value.trim();
  const stateVal = document.getElementById("wz-state").value.trim();
  const pincode = document.getElementById("wz-pincode").value.trim();

  if (!address || !city || !stateVal || !pincode) {
    showError("Please complete all required address fields.");
    return;
  }

  // Save step 3 progress
  try {
    await apiFetch("/api/shop-owner/wizard/step", {
      method: "POST",
      body: {
        step: 3,
        data: {
          shop_address: address,
          landmark: document.getElementById("wz-landmark").value.trim(),
          city,
          state: stateVal,
          pincode,
          latitude: state.wizardCoords.lat,
          longitude: state.wizardCoords.lng,
        },
      },
    });
  } catch (err) {
    console.warn("Could not save step 3 progress:", err);
  }

  renderWizardStep(4);
});

// Step 4 -> Back to 3
document.getElementById("btn-wz-back-4")?.addEventListener("click", () => renderWizardStep(3));

function populateWizardReview() {
  const name = document.getElementById("wz-shop-name").value.trim();
  const cat = document.getElementById("wz-shop-category").value;
  const customCat = document.getElementById("wz-custom-category")?.value.trim();
  const effectiveCat = cat === "Other" ? customCat : cat;
  const desc = document.getElementById("wz-shop-desc").value.trim();
  const phone = document.getElementById("wz-shop-mobile").value.trim();
  const openT = document.getElementById("wz-opening-time").value;
  const closeT = document.getElementById("wz-closing-time").value;
  const offDay = document.getElementById("wz-weekly-closing").value;

  const address = document.getElementById("wz-address").value.trim();
  const landmark = document.getElementById("wz-landmark").value.trim();
  const city = document.getElementById("wz-city").value.trim();
  const stateVal = document.getElementById("wz-state").value.trim();
  const pincode = document.getElementById("wz-pincode").value.trim();

  document.getElementById("rev-shop-name").textContent = name;
  document.getElementById("rev-shop-category").textContent = effectiveCat;
  document.getElementById("rev-shop-desc").textContent = desc || "No description provided.";
  document.getElementById("rev-owner-name").textContent = currentOwner ? currentOwner.full_name : "Owner";
  document.getElementById("rev-shop-phone").textContent = phone;
  document.getElementById("rev-timings").textContent = `${openT} - ${closeT}`;
  document.getElementById("rev-weekly-off").textContent = offDay;

  const fullAddr = [address, landmark, city, stateVal, pincode].filter(Boolean).join(", ");
  document.getElementById("rev-address").textContent = fullAddr;
  document.getElementById("rev-coords").textContent = `Coordinates: ${state.wizardCoords.lat.toFixed(4)}, ${state.wizardCoords.lng.toFixed(4)}`;
}

// Final Submit
document.getElementById("btn-wz-submit-final")?.addEventListener("click", async () => {
  clearError();
  const submitBtn = document.getElementById("btn-wz-submit-final");

  const name = document.getElementById("wz-shop-name").value.trim();
  const cat = document.getElementById("wz-shop-category").value;
  const customCat = document.getElementById("wz-custom-category")?.value.trim();
  const effectiveCat = cat === "Other" ? customCat : cat;

  const payload = {
    shop_name: name,
    shop_category: effectiveCat,
    shop_description: document.getElementById("wz-shop-desc").value.trim(),
    shop_mobile_number: document.getElementById("wz-shop-mobile").value.trim(),
    alternative_contact_number: document.getElementById("wz-shop-alt-phone").value.trim(),
    shop_email: currentOwner ? currentOwner.email : "",
    opening_time: document.getElementById("wz-opening-time").value,
    closing_time: document.getElementById("wz-closing-time").value,
    weekly_closing_day: document.getElementById("wz-weekly-closing").value,
    shop_address: document.getElementById("wz-address").value.trim(),
    landmark: document.getElementById("wz-landmark").value.trim(),
    city: document.getElementById("wz-city").value.trim(),
    state: document.getElementById("wz-state").value.trim(),
    pincode: document.getElementById("wz-pincode").value.trim(),
    latitude: state.wizardCoords.lat,
    longitude: state.wizardCoords.lng,
  };

  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-[20px] animate-spin">sync</span><span>Launching Shop...</span>`;

    const res = await apiFetch("/api/shop-owner/wizard/complete", {
      method: "POST",
      body: payload,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to finalize shop registration.");

    currentShop = data.shop;
    SHOP_NAME = currentShop.shop_name;
    document.getElementById("shop-name-header").textContent = SHOP_NAME;

    showToast("Shop successfully created & live on Voice Khata!", "success");
    switchView("dashboard");
  } catch (err) {
    console.error("Wizard finalization error:", err);
    showError(err.message || "Failed to create shop.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">store</span><span>Complete & Launch Shop</span>`;
  }
});

// ---------------------------------------------------------------------------
// Google Maps & Leaflet Interactive Map Logic
// ---------------------------------------------------------------------------
function initWizardMap() {
  const container = document.getElementById("wizard-map-canvas");
  if (!container) return;

  const { lat, lng } = state.wizardCoords;

  if (!wizardMap) {
    wizardMap = L.map("wizard-map-canvas", {
      zoomControl: true,
      attributionControl: false,
    }).setView([lat, lng], 13);

    // Dark tile layer (CartoDB Dark Matter)
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(wizardMap);

    wizardMarker = L.marker([lat, lng], { draggable: true }).addTo(wizardMap);

    wizardMarker.on("dragend", (e) => {
      const pos = e.target.getLatLng();
      updateWizardCoords(pos.lat, pos.lng);
    });

    wizardMap.on("click", (e) => {
      wizardMarker.setLatLng(e.latlng);
      updateWizardCoords(e.latlng.lat, e.latlng.lng);
    });
  } else {
    setTimeout(() => {
      wizardMap.invalidateSize();
      wizardMap.setView([lat, lng], 13);
      if (wizardMarker) wizardMarker.setLatLng([lat, lng]);
    }, 200);
  }
}

function updateWizardCoords(lat, lng) {
  state.wizardCoords.lat = lat;
  state.wizardCoords.lng = lng;
  const latEl = document.getElementById("wz-coord-lat");
  const lngEl = document.getElementById("wz-coord-lng");
  if (latEl) latEl.textContent = lat.toFixed(4);
  if (lngEl) lngEl.textContent = lng.toFixed(4);
}

// Geolocation button handler
document.getElementById("btn-wz-current-location")?.addEventListener("click", () => {
  if (!navigator.geolocation) {
    showToast("Geolocation is not supported by your browser.", "warning");
    return;
  }

  showToast("Locating your device...", "info");
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const { latitude, longitude } = pos.coords;
      updateWizardCoords(latitude, longitude);
      if (wizardMap && wizardMarker) {
        wizardMap.setView([latitude, longitude], 15);
        wizardMarker.setLatLng([latitude, longitude]);
      }
      showToast("Location updated from GPS!", "success");

      // Reverse geocode via Nominatim
      try {
        const rev = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
        if (rev.ok) {
          const revData = await rev.json();
          if (revData && revData.address) {
            const a = revData.address;
            if (a.city || a.town || a.village) document.getElementById("wz-city").value = a.city || a.town || a.village;
            if (a.state) document.getElementById("wz-state").value = a.state;
            if (a.postcode) document.getElementById("wz-pincode").value = a.postcode;
            if (a.road || a.suburb) document.getElementById("wz-address").value = [a.road, a.suburb].filter(Boolean).join(", ");
          }
        }
      } catch (err) {
        console.warn("Reverse geocode failed:", err);
      }
    },
    (err) => {
      console.warn("Geolocation error:", err);
      showToast("Could not retrieve current location.", "warning");
    },
    { enableHighAccuracy: true, timeout: 8000 }
  );
});

// Search input in wizard (Address search)
const wzPlacesInput = document.getElementById("wz-places-search");
let searchTimeout = null;
wzPlacesInput?.addEventListener("input", (e) => {
  clearTimeout(searchTimeout);
  const q = e.target.value.trim();
  if (q.length < 3) return;

  searchTimeout = setTimeout(async () => {
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=1`);
      if (res.ok) {
        const results = await res.json();
        if (results && results.length > 0) {
          const target = results[0];
          const lat = parseFloat(target.lat);
          const lon = parseFloat(target.lon);
          updateWizardCoords(lat, lon);
          if (wizardMap && wizardMarker) {
            wizardMap.setView([lat, lon], 14);
            wizardMarker.setLatLng([lat, lon]);
          }
        }
      }
    } catch (err) {
      console.warn("Search location error:", err);
    }
  }, 600);
});

// ---------------------------------------------------------------------------
// Shop Owner Dashboard Controller (5 Tabs)
// ---------------------------------------------------------------------------
async function loadDashboardData() {
  try {
    const res = await apiFetch("/api/shop-owner/shop");
    if (!res.ok) throw new Error("Could not fetch shop profile.");

    const shop = await res.json();
    currentShop = shop;
    SHOP_NAME = shop.shop_name;
    document.getElementById("shop-name-header").textContent = SHOP_NAME;

    // Header banner
    document.getElementById("dash-header-shop-name").textContent = shop.shop_name;
    document.getElementById("dash-header-category-badge").textContent = shop.shop_category;
    document.getElementById("dash-header-owner-name").textContent = currentOwner ? currentOwner.full_name : "Owner";
    document.getElementById("dash-header-hours").textContent = `${shop.opening_time} - ${shop.closing_time}`;
    document.getElementById("dash-header-city").textContent = shop.city;

    const statusBadge = document.getElementById("dash-header-status-badge");
    if (statusBadge) {
      statusBadge.textContent = shop.verification_status.toUpperCase();
      statusBadge.className =
        shop.verification_status === "verified"
          ? "px-2 py-0.5 rounded-full bg-green-950/80 text-green-400 text-[10px] font-semibold border border-green-500/30"
          : "px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-400 text-[10px] font-semibold border border-amber-500/30";
    }

    // Google Maps Links
    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${shop.latitude},${shop.longitude}`;
    const headerMapsLink = document.getElementById("dash-link-google-maps");
    const overviewMapsBtn = document.getElementById("dash-overview-maps-btn");
    if (headerMapsLink) headerMapsLink.href = mapsUrl;
    if (overviewMapsBtn) overviewMapsBtn.href = mapsUrl;

    // Overview Tab
    document.getElementById("dash-metric-status").textContent = shop.verification_status;
    document.getElementById("dash-metric-offday").textContent = shop.weekly_closing_day || "None";
    document.getElementById("dash-overview-address").textContent = [shop.shop_address, shop.landmark, shop.city, shop.state, shop.pincode].filter(Boolean).join(", ");

    initDashboardOverviewMap(shop.latitude, shop.longitude, shop.shop_name);

    // Populate Edit Shop form
    document.getElementById("edit-shop-name").value = shop.shop_name;
    document.getElementById("edit-shop-category").value = shop.shop_category;
    document.getElementById("edit-shop-desc").value = shop.shop_description || "";
    document.getElementById("edit-shop-mobile").value = shop.shop_mobile_number || "";
    document.getElementById("edit-shop-alt-phone").value = shop.alternative_contact_number || "";
    document.getElementById("edit-opening-time").value = shop.opening_time || "09:00";
    document.getElementById("edit-closing-time").value = shop.closing_time || "21:00";
    document.getElementById("edit-weekly-closing").value = shop.weekly_closing_day || "None";

    // Populate Location form
    document.getElementById("edit-address").value = shop.shop_address || "";
    document.getElementById("edit-landmark").value = shop.landmark || "";
    document.getElementById("edit-city").value = shop.city || "";
    document.getElementById("edit-state").value = shop.state || "";
    document.getElementById("edit-pincode").value = shop.pincode || "";

    // Populate Security profile
    if (currentOwner) {
      document.getElementById("edit-owner-name").value = currentOwner.full_name || "";
      document.getElementById("view-owner-email").value = currentOwner.email || "";
    }

    loadActiveSessions();
    loadDashboardFinancialMetrics();
  } catch (err) {
    console.error("Dashboard load error:", err);
    showError(err.message || "Failed to load dashboard data.");
  }
}

async function loadDashboardFinancialMetrics() {
  try {
    const res = await apiFetch("/api/customers");
    if (res.ok) {
      const customers = await res.json();
      const totalUdhaar = customers.reduce((sum, c) => sum + (c.balance || 0), 0);
      document.getElementById("dash-metric-udhaar").textContent = `₹${Math.round(totalUdhaar)}`;
      document.getElementById("dash-metric-customers").textContent = customers.length;
    }
  } catch (err) {
    console.warn("Could not load financial metrics:", err);
  }
}

function initDashboardOverviewMap(lat, lng, shopName) {
  const container = document.getElementById("dash-overview-map-canvas");
  if (!container) return;

  if (!dashOverviewMap) {
    dashOverviewMap = L.map("dash-overview-map-canvas", {
      zoomControl: false,
      attributionControl: false,
    }).setView([lat, lng], 14);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(dashOverviewMap);

    dashOverviewMarker = L.marker([lat, lng]).addTo(dashOverviewMap);
    dashOverviewMarker.bindPopup(`<strong>${escapeHtml(shopName)}</strong>`).openPopup();
  } else {
    setTimeout(() => {
      dashOverviewMap.invalidateSize();
      dashOverviewMap.setView([lat, lng], 14);
      if (dashOverviewMarker) {
        dashOverviewMarker.setLatLng([lat, lng]);
        dashOverviewMarker.setPopupContent(`<strong>${escapeHtml(shopName)}</strong>`);
      }
    }, 200);
  }
}

// Dashboard Tab Switching
const dashTabs = ["overview", "details", "location", "security"];
dashTabs.forEach((tab) => {
  document.getElementById(`dash-tab-${tab}`)?.addEventListener("click", () => {
    dashTabs.forEach((t) => {
      const btn = document.getElementById(`dash-tab-${t}`);
      const pane = document.getElementById(`dash-pane-${t}`);
      if (btn) {
        btn.className = t === tab
          ? "dash-tab-btn px-3.5 py-1.5 rounded-lg font-medium transition-all bg-indigo-600 text-white cursor-pointer flex items-center gap-1.5 shrink-0"
          : "dash-tab-btn px-3.5 py-1.5 rounded-lg font-medium transition-all text-on-surface-variant hover:text-white cursor-pointer flex items-center gap-1.5 shrink-0";
      }
      if (pane) pane.classList.toggle("hidden", t !== tab);
    });

    if (tab === "location") {
      initDashboardEditMap();
    }
  });
});

function initDashboardEditMap() {
  if (!currentShop) return;
  const lat = currentShop.latitude || 28.6139;
  const lng = currentShop.longitude || 77.2090;

  if (!dashEditMap) {
    dashEditMap = L.map("dash-edit-map-canvas", {
      zoomControl: true,
      attributionControl: false,
    }).setView([lat, lng], 14);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(dashEditMap);

    dashEditMarker = L.marker([lat, lng], { draggable: true }).addTo(dashEditMap);

    dashEditMarker.on("dragend", (e) => {
      const pos = e.target.getLatLng();
      currentShop.latitude = pos.lat;
      currentShop.longitude = pos.lng;
    });
  } else {
    setTimeout(() => {
      dashEditMap.invalidateSize();
      dashEditMap.setView([lat, lng], 14);
      if (dashEditMarker) dashEditMarker.setLatLng([lat, lng]);
    }, 200);
  }
}

// Save Shop Details Form
document.getElementById("form-edit-shop-details")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();

  const name = document.getElementById("edit-shop-name").value.trim();
  const cat = document.getElementById("edit-shop-category").value;
  const customCat = document.getElementById("edit-custom-category")?.value.trim();
  const desc = document.getElementById("edit-shop-desc").value.trim();
  const mobile = document.getElementById("edit-shop-mobile").value.trim();
  const alt = document.getElementById("edit-shop-alt-phone").value.trim();
  const openT = document.getElementById("edit-opening-time").value;
  const closeT = document.getElementById("edit-closing-time").value;
  const offDay = document.getElementById("edit-weekly-closing").value;

  try {
    const res = await apiFetch("/api/shop-owner/shop", {
      method: "PUT",
      body: {
        shop_name: name,
        shop_category: cat === "Other" && customCat ? customCat : cat,
        shop_description: desc,
        shop_mobile_number: mobile,
        alternative_contact_number: alt,
        opening_time: openT,
        closing_time: closeT,
        weekly_closing_day: offDay,
      },
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not update shop details.");

    currentShop = data.shop;
    SHOP_NAME = currentShop.shop_name;
    document.getElementById("shop-name-header").textContent = SHOP_NAME;
    showToast("Shop details saved successfully!", "success");
    loadDashboardData();
  } catch (err) {
    showError(err.message || "Failed to save shop details.");
  }
});

// Save Location Form
document.getElementById("form-edit-location")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();

  const address = document.getElementById("edit-address").value.trim();
  const landmark = document.getElementById("edit-landmark").value.trim();
  const city = document.getElementById("edit-city").value.trim();
  const stateVal = document.getElementById("edit-state").value.trim();
  const pincode = document.getElementById("edit-pincode").value.trim();

  try {
    const res = await apiFetch("/api/shop-owner/shop", {
      method: "PUT",
      body: {
        shop_address: address,
        landmark,
        city,
        state: stateVal,
        pincode,
        latitude: currentShop.latitude,
        longitude: currentShop.longitude,
      },
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not update location.");

    currentShop = data.shop;
    showToast("Shop location and map pin updated!", "success");
    loadDashboardData();
  } catch (err) {
    showError(err.message || "Failed to update location.");
  }
});

// Update Owner Name
document.getElementById("form-edit-owner-profile")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("edit-owner-name").value.trim();
  if (!name) return;

  try {
    const res = await apiFetch("/api/shop-owner/profile", {
      method: "PUT",
      body: { full_name: name },
    });
    if (!res.ok) throw new Error("Could not update profile name.");
    currentOwner.full_name = name;
    updateHeaderAuthUI();
    showToast("Owner name updated!", "success");
  } catch (err) {
    showError(err.message || "Failed to update profile.");
  }
});

// Change Password
document.getElementById("form-change-password")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const current = document.getElementById("chg-curr-pwd").value;
  const newPwd = document.getElementById("chg-new-pwd").value;
  const confPwd = document.getElementById("chg-conf-pwd").value;

  if (newPwd !== confPwd) {
    showError("New passwords do not match.");
    return;
  }

  try {
    const res = await apiFetch("/api/shop-owner/change-password", {
      method: "POST",
      body: {
        current_password: current,
        new_password: newPwd,
        confirm_password: confPwd,
      },
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Password change failed.");

    showToast("Password updated successfully!", "success");
    document.getElementById("chg-curr-pwd").value = "";
    document.getElementById("chg-new-pwd").value = "";
    document.getElementById("chg-conf-pwd").value = "";
  } catch (err) {
    showError(err.message || "Failed to change password.");
  }
});

// Active Sessions
async function loadActiveSessions() {
  const container = document.getElementById("active-sessions-list");
  if (!container) return;

  try {
    const res = await apiFetch("/api/shop-owner/sessions");
    if (!res.ok) return;

    const sessions = await res.json();
    if (sessions.length === 0) {
      container.innerHTML = `<div class="p-3 text-center text-on-surface-variant text-[12px]">No active sessions</div>`;
      return;
    }

    container.innerHTML = sessions
      .map(
        (s) => `
      <div class="py-2.5 flex items-center justify-between text-[12px]">
        <div class="flex items-center gap-2.5 min-w-0">
          <span class="material-symbols-outlined text-[18px] text-indigo-400">devices</span>
          <div class="flex flex-col min-w-0">
            <span class="font-medium text-white truncate">${escapeHtml(s.user_agent || "Browser Client")}</span>
            <span class="text-[11px] text-on-surface-variant font-mono">IP: ${escapeHtml(s.ip_address || "127.0.0.1")} • Active: ${new Date(s.last_activity).toLocaleTimeString()}</span>
          </div>
        </div>
        <button type="button" onclick="terminateSession(${s.id})" class="px-2.5 py-1 rounded bg-surface-container hover:bg-red-500/20 hover:text-red-300 text-on-surface-variant text-[11px] transition-colors cursor-pointer">
          Terminate
        </button>
      </div>
    `
      )
      .join("");
  } catch (err) {
    console.warn("Could not load sessions:", err);
  }
}

window.terminateSession = async function (sessionId) {
  try {
    const res = await apiFetch(`/api/shop-owner/sessions/${sessionId}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Session terminated.", "info");
      loadActiveSessions();
    }
  } catch (err) {
    showError("Could not terminate session.");
  }
};

document.getElementById("btn-logout-all-devices")?.addEventListener("click", async () => {
  if (!confirm("Are you sure you want to log out of all devices? You will remain signed in on this browser.")) return;
  try {
    const res = await apiFetch("/api/auth/logout-all", { method: "POST" });
    if (res.ok) {
      showToast("All other sessions logged out.", "success");
      loadActiveSessions();
    }
  } catch (err) {
    showError("Could not log out other devices.");
  }
});

document.getElementById("btn-deactivate-account")?.addEventListener("click", async () => {
  const ok = confirm("DEACTIVATE ACCOUNT: Your shop and account will be deactivated. You will be logged out. Continue?");
  if (!ok) return;

  try {
    const res = await apiFetch("/api/shop-owner/deactivate", { method: "POST" });
    if (res.ok) {
      clearAuthSession();
      showToast("Account deactivated.", "warning");
      switchView("home");
    }
  } catch (err) {
    showError("Failed to deactivate account.");
  }
});

// Shortcuts in Overview tab
document.getElementById("dash-btn-open-khata")?.addEventListener("click", () => switchView("home"));
document.getElementById("dash-quick-new-entry")?.addEventListener("click", () => {
  switchView("confirm");
  openManualEntry("");
});
document.getElementById("dash-quick-edit-profile")?.addEventListener("click", () => {
  document.getElementById("dash-tab-details")?.click();
});

// ---------------------------------------------------------------------------
// System Admin Portal Controller
// ---------------------------------------------------------------------------
async function loadAdminStats() {
  try {
    const res = await apiFetch("/api/admin/stats");
    if (!res.ok) return;
    const stats = await res.json();
    document.getElementById("adm-metric-owners").textContent = stats.total_shop_owners;
    document.getElementById("adm-metric-shops").textContent = stats.total_shops;
    document.getElementById("adm-metric-pending").textContent = stats.pending_verifications;
    document.getElementById("adm-metric-customers").textContent = stats.total_customers;
  } catch (err) {
    console.warn("Could not load admin stats:", err);
  }
}

async function loadAdminOwners() {
  const tbody = document.getElementById("adm-owners-tbody");
  if (!tbody) return;

  const q = document.getElementById("adm-search-input")?.value.trim() || "";
  const status = document.getElementById("adm-filter-status")?.value || "";

  let url = `/api/admin/shop-owners?`;
  if (q) url += `q=${encodeURIComponent(q)}&`;
  if (status) url += `status=${encodeURIComponent(status)}&`;

  try {
    const res = await apiFetch(url);
    if (!res.ok) return;
    const owners = await res.json();

    if (owners.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-on-surface-variant">No shop owners found</td></tr>`;
      return;
    }

    tbody.innerHTML = owners
      .map(
        (o) => `
      <tr class="hover:bg-surface-container/50 transition-colors">
        <td class="p-3">
          <div class="flex flex-col">
            <span class="font-medium text-white">${escapeHtml(o.full_name)}</span>
            <span class="text-[11px] text-on-surface-variant">${escapeHtml(o.email)}</span>
          </div>
        </td>
        <td class="p-3 font-mono text-[12px] text-on-surface-variant">${escapeHtml(o.mobile_number)}</td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${
            o.account_status === "active"
              ? "bg-green-950 text-green-400 border border-green-800"
              : o.account_status === "suspended"
              ? "bg-red-950 text-red-400 border border-red-800"
              : "bg-surface-container text-on-surface-variant"
          }">${o.account_status.toUpperCase()}</span>
        </td>
        <td class="p-3 text-[11px] text-on-surface-variant">${new Date(o.created_at).toLocaleDateString()}</td>
        <td class="p-3 text-right">
          ${
            o.account_status === "active"
              ? `<button type="button" onclick="setOwnerStatus(${o.id}, 'suspended')" class="px-2 py-1 rounded bg-red-600/20 hover:bg-red-600/30 text-red-300 text-[11px] font-medium cursor-pointer">Suspend</button>`
              : `<button type="button" onclick="setOwnerStatus(${o.id}, 'active')" class="px-2 py-1 rounded bg-green-600/20 hover:bg-green-600/30 text-green-300 text-[11px] font-medium cursor-pointer">Activate</button>`
          }
        </td>
      </tr>
    `
      )
      .join("");
  } catch (err) {
    console.warn("Could not load admin owners:", err);
  }
}

window.setOwnerStatus = async function (ownerId, newStatus) {
  try {
    const res = await apiFetch(`/api/admin/shop-owners/${ownerId}/status`, {
      method: "PUT",
      body: { account_status: newStatus },
    });
    if (res.ok) {
      showToast(`Owner status changed to ${newStatus.toUpperCase()}`, "success");
      loadAdminOwners();
    }
  } catch (err) {
    showError("Could not update owner status.");
  }
};

async function loadAdminShops() {
  const tbody = document.getElementById("adm-shops-tbody");
  if (!tbody) return;

  try {
    const res = await apiFetch("/api/admin/shops");
    if (!res.ok) return;
    const shops = await res.json();

    if (shops.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-on-surface-variant">No shops registered</td></tr>`;
      return;
    }

    tbody.innerHTML = shops
      .map(
        (s) => `
      <tr class="hover:bg-surface-container/50 transition-colors">
        <td class="p-3 font-medium text-white">${escapeHtml(s.shop_name)}</td>
        <td class="p-3 text-[12px] text-on-surface-variant">${escapeHtml(s.shop_category)}</td>
        <td class="p-3 text-[12px] text-on-surface-variant">${escapeHtml(s.city || "—")}</td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${
            s.verification_status === "verified"
              ? "bg-green-950 text-green-400 border border-green-800"
              : "bg-amber-950 text-amber-400 border border-amber-800"
          }">${s.verification_status.toUpperCase()}</span>
        </td>
        <td class="p-3 text-right">
          ${
            s.verification_status === "verified"
              ? `<button type="button" onclick="setShopStatus(${s.id}, 'rejected')" class="px-2 py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface-variant text-[11px] cursor-pointer">Reject</button>`
              : `<button type="button" onclick="setShopStatus(${s.id}, 'verified')" class="px-2 py-1 rounded bg-green-600/20 hover:bg-green-600/30 text-green-300 text-[11px] font-medium cursor-pointer">Verify</button>`
          }
        </td>
      </tr>
    `
      )
      .join("");
  } catch (err) {
    console.warn("Could not load admin shops:", err);
  }
}

window.setShopStatus = async function (shopId, newStatus) {
  try {
    const res = await apiFetch(`/api/admin/shops/${shopId}/status`, {
      method: "PUT",
      body: { verification_status: newStatus },
    });
    if (res.ok) {
      showToast(`Shop status updated to ${newStatus.toUpperCase()}`, "success");
      loadAdminShops();
      loadAdminStats();
    }
  } catch (err) {
    showError("Could not update shop verification.");
  }
};

async function loadAdminAuditLogs() {
  const tbody = document.getElementById("adm-logs-tbody");
  if (!tbody) return;

  try {
    const res = await apiFetch("/api/admin/audit-logs");
    if (!res.ok) return;
    const logs = await res.json();

    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-on-surface-variant">No audit logs recorded</td></tr>`;
      return;
    }

    tbody.innerHTML = logs
      .map(
        (l) => `
      <tr class="hover:bg-surface-container/50 transition-colors text-[12px]">
        <td class="p-3 text-on-surface-variant font-mono">${new Date(l.timestamp).toLocaleTimeString()}</td>
        <td class="p-3 font-semibold text-indigo-300">${escapeHtml(l.action)}</td>
        <td class="p-3 text-on-surface-variant">${escapeHtml(l.actor_email || "System")}</td>
        <td class="p-3 font-mono text-[11px] text-on-surface-variant">${escapeHtml(l.ip_address || "127.0.0.1")}</td>
        <td class="p-3 text-on-surface-variant truncate max-w-[200px]">${escapeHtml(l.details || "—")}</td>
      </tr>
    `
      )
      .join("");
  } catch (err) {
    console.warn("Could not load audit logs:", err);
  }
}

// Admin Tab Buttons
document.getElementById("adm-tab-owners")?.addEventListener("click", () => {
  document.getElementById("adm-tab-owners").className = "px-3 py-1.5 rounded-lg bg-indigo-600 text-white font-medium cursor-pointer";
  document.getElementById("adm-tab-shops").className = "px-3 py-1.5 rounded-lg text-on-surface-variant hover:text-white font-medium cursor-pointer";
  document.getElementById("adm-tab-logs").className = "px-3 py-1.5 rounded-lg text-on-surface-variant hover:text-white font-medium cursor-pointer";
  document.getElementById("adm-pane-owners").classList.remove("hidden");
  document.getElementById("adm-pane-shops").classList.add("hidden");
  document.getElementById("adm-pane-logs").classList.add("hidden");
  loadAdminOwners();
});

document.getElementById("adm-tab-shops")?.addEventListener("click", () => {
  document.getElementById("adm-tab-shops").className = "px-3 py-1.5 rounded-lg bg-indigo-600 text-white font-medium cursor-pointer";
  document.getElementById("adm-tab-owners").className = "px-3 py-1.5 rounded-lg text-on-surface-variant hover:text-white font-medium cursor-pointer";
  document.getElementById("adm-tab-logs").className = "px-3 py-1.5 rounded-lg text-on-surface-variant hover:text-white font-medium cursor-pointer";
  document.getElementById("adm-pane-shops").classList.remove("hidden");
  document.getElementById("adm-pane-owners").classList.add("hidden");
  document.getElementById("adm-pane-logs").classList.add("hidden");
  loadAdminShops();
});

document.getElementById("adm-tab-logs")?.addEventListener("click", () => {
  document.getElementById("adm-tab-logs").className = "px-3 py-1.5 rounded-lg bg-indigo-600 text-white font-medium cursor-pointer";
  document.getElementById("adm-tab-owners").className = "px-3 py-1.5 rounded-lg text-on-surface-variant hover:text-white font-medium cursor-pointer";
  document.getElementById("adm-tab-shops").className = "px-3 py-1.5 rounded-lg text-on-surface-variant hover:text-white font-medium cursor-pointer";
  document.getElementById("adm-pane-logs").classList.remove("hidden");
  document.getElementById("adm-pane-owners").classList.add("hidden");
  document.getElementById("adm-pane-shops").classList.add("hidden");
  loadAdminAuditLogs();
});

document.getElementById("adm-search-input")?.addEventListener("input", loadAdminOwners);
document.getElementById("adm-filter-status")?.addEventListener("change", loadAdminOwners);
document.getElementById("btn-exit-admin")?.addEventListener("click", () => switchView("home"));

// ---------------------------------------------------------------------------
// Voice Khata Core Voice Recording & Transaction Logic
// ---------------------------------------------------------------------------
function setVoiceSubState(substate) {
  const idle = document.getElementById("voice-idle-state");
  const rec = document.getElementById("voice-recording-state");
  const proc = document.getElementById("voice-processing-state");

  if (idle) idle.classList.toggle("hidden", substate !== "idle");
  if (rec) rec.classList.toggle("hidden", substate !== "recording");
  if (proc) proc.classList.toggle("hidden", substate !== "processing");
}

const voiceRecordBtn = document.getElementById("voice-record-btn");
const stopRecordingBtn = document.getElementById("stop-recording-btn");

if (voiceRecordBtn) {
  voiceRecordBtn.addEventListener("click", startVoiceRecording);
}
if (stopRecordingBtn) {
  stopRecordingBtn.addEventListener("click", stopVoiceRecording);
}

async function startVoiceRecording() {
  clearError();
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];
    state.mediaRecorder = new MediaRecorder(stream);

    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        state.audioChunks.push(e.data);
      }
    };

    state.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      const mimeType = state.mediaRecorder.mimeType || "audio/webm";
      state.lastAudioBlob = new Blob(state.audioChunks, { type: mimeType });
      await processRecordedAudio(state.lastAudioBlob);
    };

    state.mediaRecorder.start();
    setVoiceSubState("recording");

    state.recordingSeconds = 0;
    const timerEl = document.getElementById("recording-timer");
    if (timerEl) timerEl.textContent = "00:00";

    clearInterval(state.recordingInterval);
    state.recordingInterval = setInterval(() => {
      state.recordingSeconds++;
      const mins = Math.floor(state.recordingSeconds / 60);
      const secs = state.recordingSeconds % 60;
      if (timerEl) {
        timerEl.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      }
    }, 1000);
  } catch (err) {
    console.error("Microphone access error:", err);
    showError("Could not access microphone. Please check browser permissions.");
    setVoiceSubState("idle");
  }
}

function stopVoiceRecording() {
  clearInterval(state.recordingInterval);
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
    setVoiceSubState("processing");
  }
}

async function processRecordedAudio(blob) {
  setVoiceSubState("processing");
  const formData = new FormData();
  formData.append("file", blob, "recording.webm");

  try {
    const res = await apiFetch("/api/transcribe", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Transcription failed.");
    }

    const data = await res.json();
    populateConfirmFormFromParsed(data);
    switchView("confirm");
  } catch (err) {
    console.error("Transcribe error:", err);
    showError(err.message || "Failed to process audio.");
    setVoiceSubState("idle");
  }
}

function populateConfirmFormFromParsed(data) {
  state.rawTranscript = data.transcript || "";
  const transcriptEl = document.getElementById("confirm-transcript-text");
  if (transcriptEl) transcriptEl.textContent = state.rawTranscript || "—";

  const parsed = data.parsed || {};
  document.getElementById("field-customer").value = parsed.customer_name || "";
  document.getElementById("field-item").value = parsed.item_name || "";
  document.getElementById("field-qty").value = parsed.quantity || "";
  document.getElementById("field-unit").value = parsed.unit || "";
  document.getElementById("field-amount").value = parsed.amount || "";

  // Transaction type
  const kind = parsed.transaction_type || "credit";
  setTransactionType(kind);
  validateConfirmForm();
}

function setTransactionType(type) {
  state.selectedKind = type;
  const btnUdhaar = document.getElementById("type-udhaar");
  const btnCash = document.getElementById("type-cash");
  const btnRec = document.getElementById("type-received");

  const activeClass = "h-full rounded flex items-center justify-center font-label-md sm:font-label-lg text-label-md sm:text-label-lg transition-colors bg-primary text-on-primary font-medium truncate px-1";
  const inactiveClass = "h-full rounded flex items-center justify-center font-label-md sm:font-label-lg text-label-md sm:text-label-lg transition-colors bg-transparent text-on-surface-variant hover:text-white truncate px-1";

  if (btnUdhaar) btnUdhaar.className = type === "credit" ? activeClass : inactiveClass;
  if (btnCash) btnCash.className = type === "cash" ? activeClass : inactiveClass;
  if (btnRec) btnRec.className = type === "payment" ? activeClass : inactiveClass;

  const itemBox = document.getElementById("container-field-item");
  const qtyBox = document.getElementById("container-field-qty-unit");
  if (itemBox) itemBox.classList.toggle("hidden", type === "payment");
  if (qtyBox) qtyBox.classList.toggle("hidden", type === "payment");

  validateConfirmForm();
}

document.getElementById("type-udhaar")?.addEventListener("click", () => setTransactionType("credit"));
document.getElementById("type-cash")?.addEventListener("click", () => setTransactionType("cash"));
document.getElementById("type-received")?.addEventListener("click", () => setTransactionType("payment"));

function validateConfirmForm() {
  const cust = document.getElementById("field-customer")?.value.trim();
  const item = document.getElementById("field-item")?.value.trim();
  const amount = parseFloat(document.getElementById("field-amount")?.value || "0");
  const saveBtn = document.getElementById("save-entry-btn");

  const isPayment = state.selectedKind === "payment";
  const valid = Boolean(cust && amount > 0 && (isPayment || item));

  if (saveBtn) {
    saveBtn.disabled = !valid;
    saveBtn.className = valid
      ? "h-11 rounded-lg bg-green-600 hover:bg-green-500 text-white font-label-lg text-label-lg flex items-center justify-center gap-1.5 shadow-lg shadow-green-600/25 active:scale-95 transition-all cursor-pointer"
      : "h-11 rounded-lg bg-surface-container border border-surface-container-high text-on-surface-variant/40 font-label-lg text-label-lg flex items-center justify-center gap-1.5 cursor-not-allowed transition-colors select-none";
  }
}

["field-customer", "field-item", "field-qty", "field-unit", "field-amount"].forEach((id) => {
  document.getElementById(id)?.addEventListener("input", validateConfirmForm);
});

// Save Entry Action
document.getElementById("save-entry-btn")?.addEventListener("click", async () => {
  clearError();
  const custName = document.getElementById("field-customer").value.trim();
  const itemName = document.getElementById("field-item").value.trim();
  const qtyStr = document.getElementById("field-qty").value.trim();
  const unit = document.getElementById("field-unit").value.trim();
  const amount = parseFloat(document.getElementById("field-amount").value || "0");
  const saveBtn = document.getElementById("save-entry-btn");

  const payload = {
    customer_name: custName,
    item_name: state.selectedKind === "payment" ? "Payment Received" : itemName,
    quantity: qtyStr ? parseFloat(qtyStr) : null,
    unit: unit || null,
    amount: amount,
    kind: state.selectedKind,
    raw_transcript: state.rawTranscript || null,
  };

  try {
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">sync</span><span>Saving...</span>`;

    const res = await apiFetch("/api/entries", {
      method: "POST",
      body: payload,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to save entry.");

    showToast(`Entry saved for ${custName}!`, "success");
    openCustomerLedger(data.customer_id, custName);
  } catch (err) {
    console.error("Save entry error:", err);
    showError(err.message || "Failed to save entry.");
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = `<span class="material-symbols-outlined text-[18px]">check</span><span>Save entry</span>`;
  }
});

document.getElementById("btn-re-record")?.addEventListener("click", () => {
  switchView("home");
  startVoiceRecording();
});

// Manual Entry Trigger
function openManualEntry(customerName = "") {
  clearError();
  state.rawTranscript = "";
  const transcriptEl = document.getElementById("confirm-transcript-text");
  if (transcriptEl) transcriptEl.textContent = "Manual transaction entry (no voice audio)";

  document.getElementById("field-customer").value = customerName || "";
  document.getElementById("field-item").value = "";
  document.getElementById("field-qty").value = "";
  document.getElementById("field-unit").value = "";
  document.getElementById("field-amount").value = "";

  setTransactionType("credit");
  validateConfirmForm();
  switchView("confirm");
}

window.openManualEntry = openManualEntry;

// Voice Prompt Chips
document.querySelectorAll(".voice-prompt-chip").forEach((chip) => {
  chip.addEventListener("click", async () => {
    const prompt = chip.getAttribute("data-prompt");
    if (!prompt) return;
    setVoiceSubState("processing");

    try {
      const res = await apiFetch("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: { text: prompt },
      });

      if (!res.ok) throw new Error("Mock transcription failed.");
      const data = await res.json();
      populateConfirmFormFromParsed(data);
      switchView("confirm");
    } catch (err) {
      showError("Could not process voice prompt chip.");
      setVoiceSubState("idle");
    }
  });
});

// Unit Chips
document.querySelectorAll(".unit-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const unit = chip.getAttribute("data-unit");
    const input = document.getElementById("field-unit");
    if (input && unit) {
      input.value = unit;
      validateConfirmForm();
    }
  });
});

// ---------------------------------------------------------------------------
// Customer Directory & Ledger Views
// ---------------------------------------------------------------------------
async function loadCustomers() {
  const container = document.getElementById("customer-list");
  if (!container) return;

  try {
    const res = await apiFetch("/api/customers");
    if (!res.ok) throw new Error("Could not load customers.");

    const customers = await res.json();
    state.customers = customers;
    renderCustomerList(customers);

    // Update Home Metrics
    const totalUdhaar = customers.reduce((sum, c) => sum + (c.balance || 0), 0);
    document.getElementById("metric-total-udhaar").textContent = `₹${Math.round(totalUdhaar)}`;
    document.getElementById("metric-customer-count").textContent = `${customers.length} active`;
  } catch (err) {
    console.error("Load customers error:", err);
    container.innerHTML = `<div class="p-6 text-center text-red-400 text-body-sm">Failed to load customer list</div>`;
  }
}

function renderCustomerList(customers) {
  const container = document.getElementById("customer-list");
  if (!container) return;

  if (customers.length === 0) {
    container.innerHTML = `<div class="p-8 text-center text-on-surface-variant text-body-sm">No customers recorded yet. Say or add a new transaction!</div>`;
    return;
  }

  container.innerHTML = customers
    .map(
      (c) => `
    <div onclick="openCustomerLedger(${c.id}, '${escapeHtml(c.name)}')" class="p-3 sm:p-4 flex items-center justify-between hover:bg-surface-container transition-colors cursor-pointer border-b border-surface-container-high/60 last:border-b-0">
      <div class="flex items-center gap-3 min-w-0">
        <div class="w-10 h-10 rounded-full bg-indigo-600/20 text-indigo-300 font-semibold text-[13px] flex items-center justify-center shrink-0 border border-indigo-500/20">
          ${escapeHtml(c.name.slice(0, 2).toUpperCase())}
        </div>
        <div class="flex flex-col min-w-0">
          <span class="font-medium text-white text-[14px] truncate">${escapeHtml(c.name)}</span>
          <span class="text-[11px] text-on-surface-variant">${c.entries_count || 0} entries</span>
        </div>
      </div>
      <div class="flex flex-col items-end">
        <span class="font-mono font-semibold text-[15px] ${c.balance > 0 ? "text-red-400" : "text-green-400"}">₹${Math.round(c.balance || 0)}</span>
        <span class="text-[10px] text-on-surface-variant">${c.balance > 0 ? "Pending" : "Clear"}</span>
      </div>
    </div>
  `
    )
    .join("");
}

// Search Customers filter
document.getElementById("customer-search-input")?.addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase().trim();
  const filtered = state.customers.filter((c) => c.name.toLowerCase().includes(q));
  renderCustomerList(filtered);
});

// Recent Transactions Feed
async function loadRecentTransactions() {
  const container = document.getElementById("recent-transactions-list");
  if (!container) return;

  try {
    const res = await apiFetch("/api/entries?limit=15");
    if (!res.ok) return;

    const entries = await res.json();
    if (entries.length === 0) {
      container.innerHTML = `<div class="p-6 text-center text-on-surface-variant text-body-sm">No recent transactions recorded</div>`;
      return;
    }

    container.innerHTML = entries
      .map((entry) => {
        const isCredit = entry.kind === "credit";
        const isPayment = entry.kind === "payment";
        const amountColor = isCredit ? "text-red-400" : isPayment ? "text-green-400" : "text-indigo-400";
        const badgeColor = isCredit
          ? "bg-red-950/80 text-red-300 border-red-800/40"
          : isPayment
          ? "bg-green-950/80 text-green-300 border-green-800/40"
          : "bg-surface-container text-on-surface-variant border-surface-container-highest";

        return `
        <div class="p-3 sm:p-4 flex items-center justify-between hover:bg-surface-container/40 transition-colors">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-8 h-8 rounded-lg ${isCredit ? "bg-red-500/10 text-red-400" : isPayment ? "bg-green-500/10 text-green-400" : "bg-indigo-500/10 text-indigo-400"} flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-[18px]">${isCredit ? "trending_up" : isPayment ? "payments" : "receipt"}</span>
            </div>
            <div class="flex flex-col min-w-0">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="font-medium text-white text-[13px] truncate">${escapeHtml(entry.customer_name || "Customer")}</span>
                <span class="text-[10px] font-semibold px-1.5 py-0.2 rounded border ${badgeColor}">${entry.kind.toUpperCase()}</span>
              </div>
              <span class="text-[11px] text-on-surface-variant truncate">${escapeHtml(entry.item_name || "Entry")} ${entry.quantity ? `• ${entry.quantity} ${entry.unit || ""}` : ""}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="font-mono font-semibold text-[14px] ${amountColor}">₹${Math.round(entry.amount)}</span>
            <a href="/api/entries/${entry.id}/invoice" target="_blank" class="text-on-surface-variant/40 hover:text-indigo-400 p-1" title="Download Invoice PDF">
              <span class="material-symbols-outlined text-[16px]">picture_as_pdf</span>
            </a>
          </div>
        </div>
      `;
      })
      .join("");
  } catch (err) {
    console.warn("Could not load recent transactions:", err);
  }
}

// Open Customer Ledger
async function openCustomerLedger(customerId, customerName) {
  state.currentCustomerId = customerId;
  state.currentCustomerName = customerName;
  switchView("ledger");

  const listEl = document.getElementById("ledger-entries-list");
  if (listEl) listEl.innerHTML = `<div class="p-6 text-center text-on-surface-variant text-body-sm">Loading ledger...</div>`;

  try {
    const res = await apiFetch(`/api/customers/${customerId}/entries`);
    if (!res.ok) throw new Error("Failed to load customer entries.");

    const entries = await res.json();
    let balance = 0;
    entries.forEach((e) => {
      if (e.kind === "credit") balance += e.amount;
      else if (e.kind === "payment") balance -= e.amount;
    });

    state.currentCustomerBalance = balance;
    document.getElementById("ledger-balance-val").textContent = `₹${Math.round(balance)}`;
    document.getElementById("ledger-entries-count").textContent = `${entries.length} entries`;

    if (entries.length === 0) {
      listEl.innerHTML = `<div class="p-6 text-center text-on-surface-variant text-body-sm">No entries yet for ${escapeHtml(customerName)}</div>`;
      return;
    }

    listEl.innerHTML = entries
      .map((entry) => {
        const isCredit = entry.kind === "credit";
        const isPayment = entry.kind === "payment";
        const amountColor = isCredit ? "text-red-400" : isPayment ? "text-green-400" : "text-indigo-400";

        return `
        <div class="p-3.5 flex items-center justify-between hover:bg-surface-container/30 transition-colors">
          <div class="flex flex-col min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-medium text-white text-[13px] truncate">${escapeHtml(entry.item_name || "Transaction")}</span>
              <span class="text-[10px] font-semibold px-1.5 rounded bg-surface-container text-on-surface-variant">${entry.kind.toUpperCase()}</span>
            </div>
            <div class="flex items-center gap-1.5 text-[11px] text-on-surface-variant mt-0.5">
              <span>${new Date(entry.created_at).toLocaleDateString()}</span>
              ${entry.quantity ? `<span>• ${entry.quantity} ${entry.unit || ""}</span>` : ""}
            </div>
          </div>
          <div class="flex items-center gap-2.5">
            <span class="font-mono font-semibold text-[15px] ${amountColor}">₹${Math.round(entry.amount)}</span>
            <a href="/api/entries/${entry.id}/invoice" target="_blank" class="text-on-surface-variant/40 hover:text-indigo-400 p-1" title="Download Invoice PDF">
              <span class="material-symbols-outlined text-[16px]">picture_as_pdf</span>
            </a>
            <button type="button" onclick="handleDeleteEntry(${entry.id})" class="text-on-surface-variant/40 hover:text-red-400 p-1 cursor-pointer" title="Delete entry">
              <span class="material-symbols-outlined text-[16px]">delete</span>
            </button>
          </div>
        </div>
      `;
      })
      .join("");
  } catch (err) {
    console.error("Open ledger error:", err);
    showError(err.message || "Failed to load customer ledger.");
  }
}

window.openCustomerLedger = openCustomerLedger;

async function handleDeleteEntry(entryId) {
  if (!confirm("Are you sure you want to delete this entry?")) return;
  try {
    const res = await apiFetch(`/api/entries/${entryId}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Entry deleted.", "info");
      if (state.currentCustomerId && state.currentCustomerName) {
        openCustomerLedger(state.currentCustomerId, state.currentCustomerName);
      }
    }
  } catch (err) {
    showError("Could not delete entry.");
  }
}

window.handleDeleteEntry = handleDeleteEntry;

document.getElementById("btn-delete-customer")?.addEventListener("click", async () => {
  if (!state.currentCustomerId) return;
  const ok = confirm(`Delete customer "${state.currentCustomerName}" and all associated entries?`);
  if (!ok) return;

  try {
    const res = await apiFetch(`/api/customers/${state.currentCustomerId}`, { method: "DELETE" });
    if (res.ok) {
      showToast(`Customer ${state.currentCustomerName} deleted.`, "info");
      switchView("home");
    }
  } catch (err) {
    showError("Could not delete customer.");
  }
});

// ---------------------------------------------------------------------------
// HTML String Escaping Utility
// ---------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ---------------------------------------------------------------------------
// Initialization on App Start
// ---------------------------------------------------------------------------
async function initApp() {
  try {
    // 1. Fetch server config
    const res = await fetch("/api/config");
    if (res.ok) {
      const data = await res.json();
      if (data.shop_name) {
        SHOP_NAME = data.shop_name;
        document.getElementById("shop-name-header").textContent = SHOP_NAME;
      }
    }

    // 2. Check existing session if token exists
    if (authToken) {
      try {
        const meRes = await apiFetch("/api/auth/me");
        if (meRes.ok) {
          const meData = await meRes.json();
          currentOwner = meData.owner;
          currentShop = meData.shop;
          if (currentShop) {
            SHOP_NAME = currentShop.shop_name;
            document.getElementById("shop-name-header").textContent = SHOP_NAME;
          }
        } else {
          clearAuthSession();
        }
      } catch (err) {
        clearAuthSession();
      }
    }

    updateHeaderAuthUI();

    // 3. Manual entry button wiring
    document.getElementById("btn-manual-entry")?.addEventListener("click", (e) => {
      e.preventDefault();
      const cust = state.currentView === "ledger" && state.currentCustomerName ? state.currentCustomerName : "";
      openManualEntry(cust);
    });

    switchView("home");
  } catch (err) {
    console.warn("Init error:", err);
    switchView("home");
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}
