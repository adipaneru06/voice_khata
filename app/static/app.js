/**
 * Voice Khata — Single Page Application logic
 * Follows SPEC.md (including Section 9 & 13) exactly.
 */

// ---------------------------------------------------------------------------
// Shop Name Constant (Configured from GET /api/config per SPEC.md Section 13)
// ---------------------------------------------------------------------------
let SHOP_NAME = "My Shop";

// ---------------------------------------------------------------------------
// Application State
// ---------------------------------------------------------------------------
const state = {
  customers: [],
  currentView: "home", // "home" | "confirm" | "ledger"
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
};

// ---------------------------------------------------------------------------
// DOM Elements
// ---------------------------------------------------------------------------
const elements = {
  // Navigation / Header
  headerTitle: document.getElementById("header-title"),
  shopNameHeader: document.getElementById("shop-name-header"),
  headerBackBtn: document.getElementById("header-back-btn"),
  btnManualEntry: document.getElementById("btn-manual-entry"),
  btnLedgerAddEntry: document.getElementById("btn-ledger-add-entry"),
  btnDeleteCustomer: document.getElementById("btn-delete-customer"),
  errorBanner: document.getElementById("error-banner"),
  errorMessage: document.getElementById("error-message"),
  errorRetryBtn: document.getElementById("error-retry-btn"),
  errorCloseBtn: document.getElementById("error-close-btn"),

  // Views
  viewHome: document.getElementById("view-home"),
  viewConfirm: document.getElementById("view-confirm"),
  viewLedger: document.getElementById("view-ledger"),

  // Home View Elements
  metricTotalUdhaar: document.getElementById("metric-total-udhaar"),
  metricCustomerCount: document.getElementById("metric-customer-count"),
  voiceIdleState: document.getElementById("voice-idle-state"),
  voiceRecordingState: document.getElementById("voice-recording-state"),
  voiceProcessingState: document.getElementById("voice-processing-state"),
  voiceRecordBtn: document.getElementById("voice-record-btn"),
  stopRecordingBtn: document.getElementById("stop-recording-btn"),
  recordingTimer: document.getElementById("recording-timer"),
  customerSearchInput: document.getElementById("customer-search-input"),
  customerList: document.getElementById("customer-list"),
  recentTransactionsList: document.getElementById("recent-transactions-list"),
  recentTransactionsCount: document.getElementById("recent-transactions-count"),

  // Confirm View Elements
  confirmTranscriptText: document.getElementById("confirm-transcript-text"),
  fieldCustomer: document.getElementById("field-customer"),
  fieldItem: document.getElementById("field-item"),
  fieldQty: document.getElementById("field-qty"),
  fieldUnit: document.getElementById("field-unit"),
  fieldAmount: document.getElementById("field-amount"),
  containerFieldItem: document.getElementById("container-field-item"),
  containerFieldQtyUnit: document.getElementById("container-field-qty-unit"),
  customerMissingTag: document.getElementById("customer-missing-tag"),
  itemMissingTag: document.getElementById("item-missing-tag"),
  qtyMissingTag: document.getElementById("qty-missing-tag"),
  unitMissingTag: document.getElementById("unit-missing-tag"),
  amountMissingTag: document.getElementById("amount-missing-tag"),
  amountValidationMsg: document.getElementById("amount-validation-msg"),
  customerValidationMsg: document.getElementById("customer-validation-msg"),
  itemValidationMsg: document.getElementById("item-validation-msg"),
  typeUdhaar: document.getElementById("type-udhaar"),
  typeCash: document.getElementById("type-cash"),
  typeReceived: document.getElementById("type-received"),
  btnReRecord: document.getElementById("btn-re-record"),
  saveEntryBtn: document.getElementById("save-entry-btn"),

  // Ledger View Elements
  ledgerSyncTime: document.getElementById("ledger-sync-time"),
  ledgerBalanceVal: document.getElementById("ledger-balance-val"),
  ledgerBalanceSubtitle: document.getElementById("ledger-balance-subtitle"),
  ledgerStatusDot: document.getElementById("ledger-status-dot"),
  ledgerStatusTag: document.getElementById("ledger-status-tag"),
  ledgerEntriesCount: document.getElementById("ledger-entries-count"),
  ledgerEntriesList: document.getElementById("ledger-entries-list"),
};

// ---------------------------------------------------------------------------
// Error Notification Helpers (with Retry Support)
// ---------------------------------------------------------------------------
let currentRetryCallback = null;

function showError(message, retryCallback = null) {
  if (!elements.errorBanner) return;
  elements.errorMessage.textContent = message;
  currentRetryCallback = retryCallback;

  if (elements.errorRetryBtn) {
    if (retryCallback && typeof retryCallback === "function") {
      elements.errorRetryBtn.classList.remove("hidden");
    } else {
      elements.errorRetryBtn.classList.add("hidden");
    }
  }

  elements.errorBanner.classList.remove("hidden");
}

function clearError() {
  if (!elements.errorBanner) return;
  elements.errorBanner.classList.add("hidden");
  if (elements.errorRetryBtn) {
    elements.errorRetryBtn.classList.add("hidden");
  }
  currentRetryCallback = null;
}

if (elements.errorCloseBtn) {
  elements.errorCloseBtn.addEventListener("click", clearError);
}

if (elements.errorRetryBtn) {
  elements.errorRetryBtn.addEventListener("click", () => {
    const cb = currentRetryCallback;
    clearError();
    if (cb && typeof cb === "function") {
      cb();
    }
  });
}

// ---------------------------------------------------------------------------
// View Switching (Strictly JS-based per Section 13 — No history.back())
// ---------------------------------------------------------------------------
function switchView(viewName) {
  if (state.currentView !== viewName) {
    state.previousView = state.currentView;
  }
  state.currentView = viewName;
  clearError();
  window.scrollTo({ top: 0, behavior: "smooth" });

  elements.viewHome.classList.add("hidden");
  elements.viewConfirm.classList.add("hidden");
  elements.viewLedger.classList.add("hidden");

  if (viewName === "home") {
    elements.viewHome.classList.remove("hidden");
    elements.headerBackBtn.classList.add("hidden");
    elements.headerTitle.textContent = "Ledger Dashboard";
    elements.shopNameHeader.textContent = SHOP_NAME;
    setVoiceSubState("idle");
    loadCustomers();
  } else if (viewName === "confirm") {
    elements.viewConfirm.classList.remove("hidden");
    elements.headerBackBtn.classList.remove("hidden");
    elements.headerTitle.textContent = "Confirm Entry";
    elements.shopNameHeader.textContent = "Review & Save";
    validateConfirmForm();
  } else if (viewName === "ledger") {
    elements.viewLedger.classList.remove("hidden");
    elements.headerBackBtn.classList.remove("hidden");
    elements.headerTitle.textContent = state.currentCustomerName || "Customer Ledger";
    elements.shopNameHeader.textContent = SHOP_NAME;
  }
}

elements.headerBackBtn.addEventListener("click", () => {
  if (state.currentView === "confirm" && state.previousView === "ledger" && state.currentCustomerId) {
    switchView("ledger");
  } else {
    switchView("home");
  }
});

// ---------------------------------------------------------------------------
// Voice Sub-States on Home (Idle / Recording / Processing)
// ---------------------------------------------------------------------------
function setVoiceSubState(subState) {
  elements.voiceIdleState.classList.add("hidden");
  elements.voiceRecordingState.classList.add("hidden");
  elements.voiceProcessingState.classList.add("hidden");

  if (subState === "idle") {
    elements.voiceIdleState.classList.remove("hidden");
    elements.voiceRecordBtn.removeAttribute("disabled");
  } else if (subState === "recording") {
    elements.voiceRecordingState.classList.remove("hidden");
  } else if (subState === "processing") {
    elements.voiceProcessingState.classList.remove("hidden");
    elements.voiceRecordBtn.setAttribute("disabled", "true");
  }
}

// ---------------------------------------------------------------------------
// Audio Recording Logic (MediaRecorder & Timer)
// ---------------------------------------------------------------------------
async function startRecording() {
  clearError();

  // Handle browser not supporting MediaRecorder
  if (!window.MediaRecorder || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showError("Audio recording is not supported in this browser.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];

    // Select the best supported audio format across Chrome, Safari/iOS, Edge, Firefox
    let selectedMimeType = "";
    let fileExtension = "webm";

    const candidates = [
      { mime: "audio/webm;codecs=opus", ext: "webm" },
      { mime: "audio/webm", ext: "webm" },
      { mime: "audio/mp4", ext: "mp4" },
      { mime: "audio/aac", ext: "aac" },
      { mime: "audio/ogg;codecs=opus", ext: "ogg" },
      { mime: "audio/ogg", ext: "ogg" },
      { mime: "audio/wav", ext: "wav" },
    ];

    for (const c of candidates) {
      if (typeof window.MediaRecorder.isTypeSupported === "function" && window.MediaRecorder.isTypeSupported(c.mime)) {
        selectedMimeType = c.mime;
        fileExtension = c.ext;
        break;
      }
    }

    state.recordingMimeType = selectedMimeType;
    state.recordingExt = fileExtension;

    const options = selectedMimeType ? { mimeType: selectedMimeType } : undefined;
    state.mediaRecorder = new MediaRecorder(stream, options);

    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        state.audioChunks.push(event.data);
      }
    };

    state.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      clearInterval(state.recordingInterval);

      const actualMime = state.mediaRecorder.mimeType || state.recordingMimeType || "audio/webm";
      const audioBlob = new Blob(state.audioChunks, { type: actualMime });

      // Minimum size check to avoid sending empty or truncated recordings
      if (audioBlob.size < 500) {
        showError("Recording was too short. Please speak clearly and try again.", () => startRecording());
        setVoiceSubState("idle");
        return;
      }

      await sendAudioForTranscription(audioBlob);
    };

    // Continuous recording into memory buffer: avoids corrupt/split WebM cluster issues
    state.mediaRecorder.start();

    // Live Timer
    state.recordingSeconds = 0;
    elements.recordingTimer.textContent = "00:00";
    setVoiceSubState("recording");

    state.recordingInterval = setInterval(() => {
      state.recordingSeconds++;
      const mins = String(Math.floor(state.recordingSeconds / 60)).padStart(2, "0");
      const secs = String(state.recordingSeconds % 60).padStart(2, "0");
      elements.recordingTimer.textContent = `${mins}:${secs}`;
    }, 1000);

  } catch (err) {
    console.error("Microphone error:", err);
    if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
      showError("Microphone permission denied. Please allow microphone access.", () => startRecording());
    } else {
      showError("Microphone error. Please check your microphone and try again.", () => startRecording());
    }
    setVoiceSubState("idle");
  }
}

function stopRecording() {
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    setVoiceSubState("processing");
    try {
      state.mediaRecorder.stop();
    } catch (err) {
      console.warn("stopRecording error:", err);
    }
  }
}

elements.voiceRecordBtn.addEventListener("click", startRecording);
elements.stopRecordingBtn.addEventListener("click", stopRecording);

// ---------------------------------------------------------------------------
// Audio Transcription & Parser Integration
// ---------------------------------------------------------------------------
async function sendAudioForTranscription(audioBlob, isRetry = false) {
  state.lastAudioBlob = audioBlob;
  setVoiceSubState("processing");

  const ext = state.recordingExt || "webm";
  const formData = new FormData();
  formData.append("file", audioBlob, `recording.${ext}`);

  try {
    const res = await fetch("/api/transcribe", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const detail = (errData.detail || "").toLowerCase();

      if (res.status === 400 && (detail.includes("no speech") || detail.includes("empty"))) {
        throw { type: "NO_SPEECH", message: "No speech detected. Please speak clearly and try again." };
      } else if (res.status === 502 || detail.includes("transcription failed") || detail.includes("gnani")) {
        throw { type: "GNANI_ERROR", message: "Transcription failed. Please try again." };
      } else {
        throw { type: "SERVER_ERROR", message: errData.detail || "Transcription failed. Please try again." };
      }
    }

    const data = await res.json();
    handleTranscriptionResult(data);
  } catch (err) {
    console.error("Transcription error:", err);
    if (err.type === "NO_SPEECH") {
      showError(err.message, () => startRecording());
    } else if (err.type === "GNANI_ERROR" || err.type === "SERVER_ERROR") {
      showError(err.message, () => sendAudioForTranscription(state.lastAudioBlob));
    } else {
      // Temporary connection drop or server reload: retry once automatically
      if (!isRetry) {
        await new Promise((r) => setTimeout(r, 800));
        return sendAudioForTranscription(audioBlob, true);
      }
      showError("Server disconnected. Tap Retry to reconnect.", () => sendAudioForTranscription(state.lastAudioBlob));
    }
    setVoiceSubState("idle");
  }
}

function handleTranscriptionResult(data) {
  const { transcript, parsed, matched_customer } = data;
  state.rawTranscript = transcript || "";

  // Intent: Balance Query (SPEC.md Section 7 Case 5)
  if (parsed && parsed.intent === "balance_query") {
    handleBalanceQuery(parsed, matched_customer);
    return;
  }

  // Regular transaction entry
  populateConfirmForm(parsed, matched_customer);
  switchView("confirm");
}

function handleBalanceQuery(parsed, matchedCustomer) {
  setVoiceSubState("idle");

  const customerName = matchedCustomer ? matchedCustomer.name : parsed.customer;
  if (!customerName) {
    showError("Could not identify customer for balance query.");
    return;
  }

  // Look up customer in local state
  const target = state.customers.find(
    (c) => c.name.toLowerCase() === customerName.toLowerCase() ||
           c.name.toLowerCase().replace(/\s+ji$/i, "") === customerName.toLowerCase().replace(/\s+ji$/i, "")
  );

  if (target) {
    const spokenText = `${target.name} ke khate mein ${target.balance} rupaye baaki hai`;
    playTtsAudio(spokenText);
    openCustomerLedger(target.id, target.name, target.balance);
  } else {
    showError(`Customer "${customerName}" not found in ledger.`);
  }
}

// ---------------------------------------------------------------------------
// Confirm Entry Form Management & Validation
// ---------------------------------------------------------------------------
function setTransactionType(type) {
  state.selectedKind = type; // "credit" | "cash" | "payment"

  const buttons = [
    { btn: elements.typeUdhaar, key: "credit" },
    { btn: elements.typeCash, key: "cash" },
    { btn: elements.typeReceived, key: "payment" },
  ];

  buttons.forEach(({ btn, key }) => {
    if (key === type) {
      btn.setAttribute("aria-checked", "true");
      if (key === "credit") {
        btn.className = "h-full rounded-md flex items-center justify-center font-label-md sm:font-label-lg text-label-md sm:text-label-lg transition-all bg-red-600/30 text-red-300 border border-red-500/60 font-semibold shadow-sm truncate px-1";
      } else if (key === "cash") {
        btn.className = "h-full rounded-md flex items-center justify-center font-label-md sm:font-label-lg text-label-md sm:text-label-lg transition-all bg-amber-600/30 text-amber-300 border border-amber-500/60 font-semibold shadow-sm truncate px-1";
      } else if (key === "payment") {
        btn.className = "h-full rounded-md flex items-center justify-center font-label-md sm:font-label-lg text-label-md sm:text-label-lg transition-all bg-emerald-600/30 text-emerald-300 border border-emerald-500/60 font-semibold shadow-sm truncate px-1";
      }
    } else {
      btn.setAttribute("aria-checked", "false");
      btn.className = "h-full rounded-md flex items-center justify-center font-label-md sm:font-label-lg text-label-md sm:text-label-lg transition-all bg-transparent text-on-surface-variant hover:text-on-surface truncate px-1";
    }
  });

  // Per Section 13: Item is optional if type is payment received
  if (type === "payment") {
    elements.itemMissingTag.classList.add("hidden");
    elements.itemValidationMsg.classList.add("hidden");
    elements.fieldItem.classList.remove("border-error");
  }

  validateConfirmForm();
}

elements.typeUdhaar.addEventListener("click", () => setTransactionType("credit"));
elements.typeCash.addEventListener("click", () => setTransactionType("cash"));
elements.typeReceived.addEventListener("click", () => setTransactionType("payment"));

function populateConfirmForm(parsed, matchedCustomer) {
  elements.confirmTranscriptText.textContent = `“${state.rawTranscript}”`;

  // Pre-match customer name if matched_customer is set
  const customerVal = matchedCustomer ? matchedCustomer.name : (parsed.customer || "");
  const itemVal = parsed.item_original || parsed.item || "";
  const qtyVal = parsed.quantity != null ? String(parsed.quantity) : "";
  const unitVal = parsed.unit || "";
  const amountVal = (parsed.amount != null && parsed.amount > 0) ? String(parsed.amount) : "";
  const kindVal = parsed.kind || "credit";

  elements.fieldCustomer.value = customerVal;
  elements.fieldItem.value = itemVal;
  elements.fieldQty.value = qtyVal;
  elements.fieldUnit.value = unitVal;
  elements.fieldAmount.value = amountVal;

  setTransactionType(kindVal);

  // Missing fields highlights per Section 13
  const missing = parsed.missing || [];

  // Customer missing
  if (missing.includes("customer") || !customerVal) {
    elements.customerMissingTag.classList.remove("hidden");
    elements.customerValidationMsg.classList.remove("hidden");
    elements.fieldCustomer.classList.add("border-error");
  } else {
    elements.customerMissingTag.classList.add("hidden");
    elements.customerValidationMsg.classList.add("hidden");
    elements.fieldCustomer.classList.remove("border-error");
  }

  // Item missing (only if not payment received)
  if (kindVal !== "payment" && (missing.includes("item") || !itemVal)) {
    elements.itemMissingTag.classList.remove("hidden");
    elements.itemValidationMsg.classList.remove("hidden");
    elements.fieldItem.classList.add("border-error");
  } else {
    elements.itemMissingTag.classList.add("hidden");
    elements.itemValidationMsg.classList.add("hidden");
    elements.fieldItem.classList.remove("border-error");
  }

  // Quantity missing
  if (missing.includes("quantity") && !qtyVal && kindVal !== "payment") {
    elements.qtyMissingTag.classList.remove("hidden");
    elements.fieldQty.classList.add("border-error");
  } else {
    elements.qtyMissingTag.classList.add("hidden");
    elements.fieldQty.classList.remove("border-error");
  }

  // Unit missing
  if (missing.includes("unit") && !unitVal && kindVal !== "payment") {
    elements.unitMissingTag.classList.remove("hidden");
    elements.fieldUnit.classList.add("border-error");
  } else {
    elements.unitMissingTag.classList.add("hidden");
    elements.fieldUnit.classList.remove("border-error");
  }

  // Amount missing or invalid
  const parsedAmtNum = parseFloat(amountVal);
  if (missing.includes("amount") || !amountVal || isNaN(parsedAmtNum) || parsedAmtNum <= 0) {
    elements.amountMissingTag.classList.remove("hidden");
    elements.amountValidationMsg.classList.remove("hidden");
    elements.amountValidationMsg.innerHTML = '<span class="material-symbols-outlined text-[14px]">error</span><span>Amount must be greater than 0.</span>';
    elements.fieldAmount.classList.add("border-error");
  } else {
    elements.amountMissingTag.classList.add("hidden");
    elements.amountValidationMsg.classList.add("hidden");
    elements.fieldAmount.classList.remove("border-error");
  }

  validateConfirmForm();
}

/**
 * Section 13 Validation Rule & Robustness:
 * "Save stays disabled until customer, amount and type are filled, plus item unless the type is payment received."
 * Amount must be strictly greater than 0. Rejects zero or negative amounts.
 */
function validateConfirmForm() {
  const customer = elements.fieldCustomer.value.trim();
  const rawAmount = elements.fieldAmount.value.trim();
  const amount = parseFloat(rawAmount);
  const item = elements.fieldItem.value.trim();
  const kind = state.selectedKind;

  // Amount is valid ONLY if numeric and strictly > 0
  const isAmountValid = rawAmount !== "" && !isNaN(amount) && amount > 0;

  if (rawAmount !== "" && (!isAmountValid || amount <= 0)) {
    elements.amountMissingTag.classList.remove("hidden");
    elements.amountValidationMsg.classList.remove("hidden");
    elements.amountValidationMsg.innerHTML = '<span class="material-symbols-outlined text-[14px]">error</span><span>Amount must be greater than 0.</span>';
    elements.fieldAmount.classList.add("border-error");
  }

  let isValid = Boolean(customer) && isAmountValid && Boolean(kind);
  if (kind !== "payment") {
    isValid = isValid && Boolean(item);
  }

  if (isValid && !state.isSaving) {
    elements.saveEntryBtn.removeAttribute("disabled");
    elements.saveEntryBtn.className = "h-11 rounded-lg bg-primary text-on-primary font-label-lg text-label-lg flex items-center justify-center gap-1.5 active:bg-secondary-fixed cursor-pointer transition-colors select-none font-medium";
  } else {
    elements.saveEntryBtn.setAttribute("disabled", "true");
    elements.saveEntryBtn.className = "h-11 rounded-lg bg-surface-container border border-surface-container-high text-on-surface-variant/40 font-label-lg text-label-lg flex items-center justify-center gap-1.5 cursor-not-allowed transition-colors select-none";
  }

  return isValid;
}

// Live validation & clear error highlights on input
[elements.fieldCustomer, elements.fieldItem, elements.fieldQty, elements.fieldUnit, elements.fieldAmount].forEach((input) => {
  input.addEventListener("input", () => {
    if (input === elements.fieldCustomer && input.value.trim()) {
      elements.customerMissingTag.classList.add("hidden");
      elements.customerValidationMsg.classList.add("hidden");
      input.classList.remove("border-error");
    }
    if (input === elements.fieldItem && input.value.trim()) {
      elements.itemMissingTag.classList.add("hidden");
      elements.itemValidationMsg.classList.add("hidden");
      input.classList.remove("border-error");
    }
    if (input === elements.fieldQty && input.value.trim()) {
      elements.qtyMissingTag.classList.add("hidden");
      input.classList.remove("border-error");
    }
    if (input === elements.fieldUnit && input.value.trim()) {
      elements.unitMissingTag.classList.add("hidden");
      input.classList.remove("border-error");
    }
    if (input === elements.fieldAmount) {
      const amt = parseFloat(input.value);
      if (!isNaN(amt) && amt > 0) {
        elements.amountMissingTag.classList.add("hidden");
        elements.amountValidationMsg.classList.add("hidden");
        input.classList.remove("border-error");
      } else if (input.value.trim() !== "") {
        elements.amountMissingTag.classList.remove("hidden");
        elements.amountValidationMsg.classList.remove("hidden");
        elements.amountValidationMsg.innerHTML = '<span class="material-symbols-outlined text-[14px]">error</span><span>Amount must be greater than 0.</span>';
        input.classList.add("border-error");
      }
    }

    validateConfirmForm();
  });
});

elements.btnReRecord.addEventListener("click", () => {
  if (state.isSaving) return;
  switchView("home");
});

function setConfirmFormDisabled(disabled) {
  [
    elements.fieldCustomer,
    elements.fieldItem,
    elements.fieldQty,
    elements.fieldUnit,
    elements.fieldAmount,
    elements.typeUdhaar,
    elements.typeCash,
    elements.typeReceived,
    elements.btnReRecord,
  ].forEach((el) => {
    if (el) el.disabled = disabled;
  });
}

// ---------------------------------------------------------------------------
// Save Entry: POST /api/entries & Spoken Confirmation (with Double-Tap Prevention)
// ---------------------------------------------------------------------------
elements.saveEntryBtn.addEventListener("click", async () => {
  // Prevent double-tap and reject invalid inputs
  if (state.isSaving || !validateConfirmForm()) return;
  state.isSaving = true;

  const customer = elements.fieldCustomer.value.trim();
  const amount = parseFloat(elements.fieldAmount.value);
  const item = elements.fieldItem.value.trim();
  const qtyStr = elements.fieldQty.value.trim();
  const qty = qtyStr ? parseFloat(qtyStr) : null;
  const unit = elements.fieldUnit.value.trim() || null;
  const kind = state.selectedKind;

  const payload = {
    customer,
    amount,
    kind,
    item: kind === "payment" ? null : item,
    quantity: isNaN(qty) ? null : qty,
    unit: kind === "payment" ? null : unit,
    raw_transcript: state.rawTranscript || null,
  };

  // Immediate Loading and disabled states
  elements.saveEntryBtn.setAttribute("disabled", "true");
  elements.saveEntryBtn.className = "h-11 rounded-lg bg-surface-container border border-surface-container-high text-on-surface-variant/40 font-label-lg text-label-lg flex items-center justify-center gap-1.5 cursor-not-allowed transition-colors select-none";
  elements.saveEntryBtn.innerHTML = `
    <div class="w-4 h-4 rounded-full border-2 border-on-surface-variant border-t-primary animate-spin"></div>
    <span>Saving...</span>
  `;
  setConfirmFormDisabled(true);

  try {
    const res = await fetch("/api/entries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save entry");
    }

    const { entry, balance } = await res.json();

    // Spoken confirmation read-back per SPEC.md Section 9
    const spokenText = buildConfirmationSentence(kind, customer, amount);
    playTtsAudio(spokenText).catch(() => {});

    // Return to customer ledger if opened from ledger view and for that customer, else home
    if (state.previousView === "ledger" && state.currentCustomerId && state.currentCustomerName && state.currentCustomerName.toLowerCase().trim() === customer.toLowerCase().trim()) {
      openCustomerLedger(state.currentCustomerId, state.currentCustomerName, balance);
    } else {
      switchView("home");
    }

  } catch (err) {
    console.error("Save entry error:", err);
    const isNetwork = err instanceof TypeError || (err.message && err.message.toLowerCase().includes("network"));
    if (isNetwork) {
      showError("Server disconnected. Tap Retry to reconnect.", () => {
        elements.saveEntryBtn.click();
      });
    } else {
      showError(`Error saving entry: ${err.message}`);
    }
  } finally {
    state.isSaving = false;
    setConfirmFormDisabled(false);
    if (state.currentView === "confirm") {
      elements.saveEntryBtn.innerHTML = `
        <span class="material-symbols-outlined text-[18px]">check</span>
        Save entry
      `;
      validateConfirmForm();
    }
  }
});

// ---------------------------------------------------------------------------
// Spoken Confirmation Sentence Builder
// ---------------------------------------------------------------------------
function buildConfirmationSentence(kind, customer, amount) {
  if (kind === "credit") {
    return `${customer} ke khate mein ${amount} rupaye jod diye`;
  }
  if (kind === "payment") {
    return `${customer} se ${amount} rupaye mil gaye`;
  }
  if (kind === "cash") {
    return `${customer} ka bill ${amount} rupaye cash mein darj ho gaya`;
  }
  return `${customer} ka record darj ho gaya`;
}

// ---------------------------------------------------------------------------
// Spoken Audio Readback Helper (POST /api/speak)
// ---------------------------------------------------------------------------
async function playTtsAudio(text) {
  if (!text) return;
  try {
    const res = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) return;

    const audioBlob = await res.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.onended = () => URL.revokeObjectURL(audioUrl);
    audio.onerror = () => URL.revokeObjectURL(audioUrl);
    await audio.play().catch(() => {});
  } catch (err) {
    // Silently skip any speech or playback error
  }
}

// ---------------------------------------------------------------------------
// Home View: GET /api/customers, Summary Card, & Client Search Filter
// ---------------------------------------------------------------------------
async function loadCustomers(isRetry = false) {
  try {
    const res = await fetch("/api/customers");
    if (!res.ok) throw new Error("Failed to load customers");

    state.customers = await res.json();
    renderSummaryCard();
    renderCustomerList(state.customers);
    loadRecentTransactions();
  } catch (err) {
    console.error("Load customers error:", err);
    if (!isRetry) {
      await new Promise((r) => setTimeout(r, 800));
      return loadCustomers(true);
    }
    showError("Server disconnected. Tap Retry to reconnect.", () => loadCustomers());
    elements.customerList.innerHTML = `
      <div class="p-6 text-center text-error text-body-sm">
        Failed to load customer list. Check server.
      </div>
    `;
  }
}

function renderSummaryCard() {
  let totalUdhaar = 0;
  state.customers.forEach((c) => {
    if (c.balance > 0) {
      totalUdhaar += c.balance;
    }
  });

  elements.metricTotalUdhaar.textContent = `₹${formatNumber(totalUdhaar)}`;
  elements.metricCustomerCount.textContent = `${state.customers.length} active`;
}

function getInitials(name) {
  if (!name) return "??";
  const trimmed = name.trim();
  const parts = trimmed.split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return trimmed.slice(0, Math.min(2, trimmed.length)).toUpperCase();
}

function getAvatarColor(name) {
  const colors = [
    "bg-indigo-950/80 text-indigo-300 border-indigo-700/50",
    "bg-purple-950/80 text-purple-300 border-purple-700/50",
    "bg-emerald-950/80 text-emerald-300 border-emerald-700/50",
    "bg-amber-950/80 text-amber-300 border-amber-700/50",
    "bg-cyan-950/80 text-cyan-300 border-cyan-700/50",
    "bg-rose-950/80 text-rose-300 border-rose-700/50",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i);
  }
  return colors[Math.abs(hash) % colors.length];
}

function renderCustomerList(list) {
  // Empty state: no customers yet
  if (!list || list.length === 0) {
    elements.customerList.innerHTML = `
      <div class="py-10 px-4 text-center flex flex-col items-center justify-center">
        <span class="material-symbols-outlined text-[36px] text-outline mb-2 select-none">person_off</span>
        <span class="font-headline-sm text-headline-sm text-on-surface font-medium mb-1">No customers yet</span>
        <span class="font-body-sm text-body-sm text-on-surface-variant max-w-[260px]">Tap the mic to record your first entry.</span>
      </div>
    `;
    return;
  }

  elements.customerList.innerHTML = list
    .map((c) => {
      let balanceBadge = `
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 tabular-nums">
          Settled
        </span>
      `;

      if (c.balance > 0) {
        balanceBadge = `
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[12px] font-mono font-medium bg-red-500/10 text-red-400 border border-red-500/20 tabular-nums">
            ₹${formatNumber(c.balance)}
          </span>
        `;
      } else if (c.balance < 0) {
        balanceBadge = `
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[12px] font-mono font-medium bg-teal-500/10 text-teal-400 border border-teal-500/20 tabular-nums">
            ₹${formatNumber(Math.abs(c.balance))} adv
          </span>
        `;
      }

      const activityStr = formatRelativeDate(c.last_activity);
      const initials = getInitials(c.name);
      const avatarClass = getAvatarColor(c.name);

      return `
        <div class="customer-row px-space-md py-3 flex items-center justify-between hover:bg-surface-container active:bg-surface-container-high transition-colors cursor-pointer select-none border-b border-surface-container-high/40 last:border-b-0"
             onclick="openCustomerLedger(${c.id}, '${escapeHtml(c.name)}', ${c.balance})">
          <div class="flex items-center gap-3 min-w-0 pr-space-sm">
            <div class="w-10 h-10 rounded-full border flex items-center justify-center font-medium text-[13px] shrink-0 ${avatarClass}">
              ${escapeHtml(initials)}
            </div>
            <div class="flex flex-col min-w-0">
              <span class="customer-name font-headline-sm text-headline-sm text-on-surface font-medium truncate">${escapeHtml(c.name)}</span>
              <span class="font-body-sm text-body-sm text-on-surface-variant flex items-center gap-1 mt-0.5">
                <span class="material-symbols-outlined text-[13px] text-outline">schedule</span>
                ${activityStr}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            ${balanceBadge}
            <span class="material-symbols-outlined text-[18px] text-outline">chevron_right</span>
          </div>
        </div>
      `;
    })
    .join("");
}

// Client-side search box filtering the customer list
elements.customerSearchInput.addEventListener("input", (event) => {
  const query = event.target.value.toLowerCase().trim();
  if (!query) {
    renderCustomerList(state.customers);
    return;
  }
  const filtered = state.customers.filter((c) =>
    c.name.toLowerCase().includes(query)
  );
  renderCustomerList(filtered);
});

async function loadRecentTransactions() {
  if (!elements.recentTransactionsList) return;

  try {
    const res = await fetch("/api/entries/recent?limit=20");
    if (!res.ok) return;

    const entries = await res.json();
    if (elements.recentTransactionsCount) {
      elements.recentTransactionsCount.textContent = `${entries.length} ${entries.length === 1 ? "entry" : "entries"}`;
    }

    if (entries.length === 0) {
      elements.recentTransactionsList.innerHTML = `
        <div class="py-8 px-4 text-center flex flex-col items-center justify-center">
          <span class="material-symbols-outlined text-[32px] text-outline mb-1 select-none">receipt_long</span>
          <span class="font-headline-sm text-headline-sm text-on-surface font-medium">No transactions yet</span>
          <span class="font-body-sm text-body-sm text-on-surface-variant">Tap the mic or "+ New Entry" to record your first transaction.</span>
        </div>
      `;
      return;
    }

    elements.recentTransactionsList.innerHTML = entries
      .map((entry) => {
        let tagText = "Udhaar";
        let amountPrefix = "";
        let amountColor = "text-red-400";
        let tagBg = "bg-red-500/10 text-red-300 border-red-500/20";

        if (entry.kind === "payment") {
          tagText = "Received";
          amountPrefix = "-";
          amountColor = "text-emerald-400";
          tagBg = "bg-emerald-500/10 text-emerald-300 border-emerald-500/20";
        } else if (entry.kind === "cash") {
          tagText = "Cash";
          amountPrefix = "";
          amountColor = "text-amber-400";
          tagBg = "bg-amber-500/10 text-amber-300 border-amber-500/20";
        }

        const dateStr = formatDateTime(entry.created_at);
        const itemLine = entry.kind === "payment"
          ? "Payment received"
          : `${escapeHtml(entry.item || "General item")}${entry.quantity ? `, ${entry.quantity} ${escapeHtml(entry.unit || "")}` : ""}`;

        const invoiceUrl = `/api/entries/${entry.id}/invoice.pdf`;
        const customerName = escapeHtml(entry.customer_name || "Customer");
        const initials = getInitials(customerName);
        const avatarClass = getAvatarColor(customerName);

        return `
          <div class="p-space-md flex items-center justify-between hover:bg-surface-container active:bg-surface-container-high transition-colors select-none">
            <div class="flex items-center gap-3 min-w-0 pr-space-sm">
              <div class="w-9 h-9 rounded-full border flex items-center justify-center font-medium text-[12px] shrink-0 ${avatarClass}">
                ${escapeHtml(initials)}
              </div>
              <div class="flex flex-col gap-0.5 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-body-md text-body-md text-on-surface font-medium truncate">${customerName}</span>
                  <span class="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border ${tagBg}">${tagText}</span>
                </div>
                <span class="text-[12px] text-on-surface-variant truncate">${itemLine}</span>
                <span class="text-[11px] text-on-surface-variant/70 font-mono">${dateStr}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-[15px] font-semibold font-mono ${amountColor} tabular-nums">
                ${amountPrefix}₹${formatNumber(entry.amount)}
              </span>
              <a href="${invoiceUrl}" target="_blank" rel="noopener noreferrer"
                 aria-label="View Invoice PDF"
                 title="Download PDF Bill"
                 class="w-8 h-8 rounded-lg bg-surface-container border border-surface-container-high flex items-center justify-center text-on-surface-variant hover:text-on-surface active:bg-surface-container-highest transition-colors">
                <span class="material-symbols-outlined text-[17px]">description</span>
              </a>
              <button onclick="handleDeleteEntry(${entry.id}, event)"
                      type="button"
                      aria-label="Delete Entry"
                      title="Delete Entry"
                      class="w-8 h-8 rounded-lg bg-red-500/10 hover:bg-red-500/20 active:scale-95 border border-red-500/20 flex items-center justify-center text-red-400 hover:text-red-300 transition-all cursor-pointer">
                <span class="material-symbols-outlined text-[17px]">delete</span>
              </button>
            </div>
          </div>
        `;
      })
      .join("");
  } catch (err) {
    console.warn("Could not load recent entries:", err);
  }
}


// ---------------------------------------------------------------------------
// Ledger View: GET /api/customers/{id}/entries & Invoice PDF
// ---------------------------------------------------------------------------
async function openCustomerLedger(customerId, customerName, customerBalance) {
  state.currentCustomerId = customerId;
  state.currentCustomerName = customerName;
  state.currentCustomerBalance = customerBalance != null ? customerBalance : 0;

  switchView("ledger");

  // Render Customer Balance Card
  const bal = state.currentCustomerBalance;
  elements.ledgerBalanceVal.textContent = `₹${formatNumber(Math.abs(bal))}`;

  if (bal > 0) {
    elements.ledgerBalanceVal.className = "text-[24px] sm:text-[28px] leading-8 font-medium font-mono text-[#C97B7B] tracking-tight";
    elements.ledgerBalanceSubtitle.textContent = "to collect";
    elements.ledgerStatusDot.className = "w-1.5 h-1.5 rounded-full bg-[#C97B7B]";
    elements.ledgerStatusTag.textContent = "Pending";
  } else if (bal < 0) {
    elements.ledgerBalanceVal.className = "text-[24px] sm:text-[28px] leading-8 font-medium font-mono text-[#7BA68A] tracking-tight";
    elements.ledgerBalanceSubtitle.textContent = "advance";
    elements.ledgerStatusDot.className = "w-1.5 h-1.5 rounded-full bg-[#7BA68A]";
    elements.ledgerStatusTag.textContent = "Advance";
  } else {
    elements.ledgerBalanceVal.className = "text-[24px] sm:text-[28px] leading-8 font-medium font-mono text-outline tracking-tight";
    elements.ledgerBalanceSubtitle.textContent = "settled";
    elements.ledgerStatusDot.className = "w-1.5 h-1.5 rounded-full bg-outline";
    elements.ledgerStatusTag.textContent = "Settled";
  }

  // Load Customer Entries
  elements.ledgerEntriesList.innerHTML = `
    <div class="p-6 text-center text-on-surface-variant text-body-sm">
      Loading entries...
    </div>
  `;

  try {
    const res = await fetch(`/api/customers/${customerId}/entries`);
    if (!res.ok) throw new Error("Failed to load customer entries");

    const entries = await res.json();
    elements.ledgerEntriesCount.textContent = `${entries.length} ${entries.length === 1 ? "entry" : "entries"}`;

    // Empty state: customer with no entries
    if (entries.length === 0) {
      elements.ledgerEntriesList.innerHTML = `
        <div class="py-10 px-4 text-center flex flex-col items-center justify-center">
          <span class="material-symbols-outlined text-[36px] text-outline mb-2 select-none">receipt_long</span>
          <span class="font-headline-sm text-headline-sm text-on-surface font-medium mb-1">No entries yet</span>
          <span class="font-body-sm text-body-sm text-on-surface-variant max-w-[260px]">This customer has no recorded transactions.</span>
        </div>
      `;
      return;
    }

    elements.ledgerEntriesList.innerHTML = entries
      .map((entry) => {
        let tagText = "Udhaar";
        let amountPrefix = "";
        let amountColor = "text-[#C97B7B]";

        if (entry.kind === "payment") {
          tagText = "Received";
          amountPrefix = "-";
          amountColor = "text-[#7BA68A]";
        } else if (entry.kind === "cash") {
          tagText = "Cash";
          amountPrefix = "";
          amountColor = "text-on-surface";
        }

        const dateStr = formatDateTime(entry.created_at);
        const itemLine = entry.kind === "payment"
          ? "Payment received"
          : `${escapeHtml(entry.item || "General item")}${entry.quantity ? `, ${entry.quantity} ${escapeHtml(entry.unit || "")}` : ""}`;

        const invoiceUrl = `/api/entries/${entry.id}/invoice.pdf`;

        return `
          <div class="p-space-md flex items-center justify-between hover:bg-surface-container active:bg-surface-container transition-colors select-none">
            <div class="flex flex-col gap-1 min-w-0 pr-space-sm">
              <span class="font-body-md text-body-md text-on-surface font-normal truncate">${itemLine}</span>
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="text-[10px] text-on-surface-variant uppercase tracking-wider px-1.5 py-0.5 rounded border border-surface-container-high">${tagText}</span>
                <span class="text-[11px] text-on-surface-variant font-mono">${dateStr}</span>
                <span class="text-[11px] text-on-surface-variant/60 font-mono">INV-${entry.id}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-[14px] font-medium font-mono ${amountColor} tabular-nums">
                ${amountPrefix}₹${formatNumber(entry.amount)}
              </span>
              <a href="${invoiceUrl}" target="_blank" rel="noopener noreferrer"
                 aria-label="View Invoice PDF"
                 title="Download PDF Bill"
                 class="w-8 h-8 rounded-lg bg-surface-container border border-surface-container-high flex items-center justify-center text-on-surface-variant hover:text-on-surface active:bg-surface-container-highest transition-colors">
                <span class="material-symbols-outlined text-[17px]">description</span>
              </a>
              <button onclick="handleDeleteEntry(${entry.id}, event)"
                      type="button"
                      aria-label="Delete Entry"
                      title="Delete Entry"
                      class="w-8 h-8 rounded-lg bg-red-500/10 hover:bg-red-500/20 active:scale-95 border border-red-500/20 flex items-center justify-center text-red-400 hover:text-red-300 transition-all cursor-pointer">
                <span class="material-symbols-outlined text-[17px]">delete</span>
              </button>
            </div>
          </div>
        `;
      })
      .join("");

  } catch (err) {
    console.error("Load entries error:", err);
    showError("Server disconnected. Tap Retry to reconnect.", () => openCustomerLedger(customerId, customerName, customerBalance));
    elements.ledgerEntriesList.innerHTML = `
      <div class="p-6 text-center text-error text-body-sm">
        Failed to load entries. Check server.
      </div>
    `;
  }
}

// ---------------------------------------------------------------------------
// Formatting Helpers
// ---------------------------------------------------------------------------
function formatNumber(num) {
  if (num == null || isNaN(num)) return "0";
  return Number(num).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatRelativeDate(isoString) {
  if (!isoString) return "No activity";
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return "Recently";

  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return `Today, ${date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`;
  } else if (diffDays === 1) {
    return "Yesterday";
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  } else {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
}

function formatDateTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
    ", " +
    date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

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
// Manual Entry & Prompt Chips Helpers
// ---------------------------------------------------------------------------
function openManualEntry(customerName = "") {
  clearError();
  state.rawTranscript = "";
  elements.confirmTranscriptText.textContent = "Manual entry (no voice recording)";
  elements.fieldCustomer.value = customerName || "";
  elements.fieldItem.value = "";
  elements.fieldQty.value = "";
  elements.fieldUnit.value = "";
  elements.fieldAmount.value = "";

  // Reset missing tags and error highlights
  elements.customerMissingTag.classList.add("hidden");
  elements.customerValidationMsg.classList.add("hidden");
  elements.fieldCustomer.classList.remove("border-error");

  elements.itemMissingTag.classList.add("hidden");
  elements.itemValidationMsg.classList.add("hidden");
  elements.fieldItem.classList.remove("border-error");

  elements.qtyMissingTag.classList.add("hidden");
  elements.fieldQty.classList.remove("border-error");

  elements.unitMissingTag.classList.add("hidden");
  elements.fieldUnit.classList.remove("border-error");

  elements.amountMissingTag.classList.add("hidden");
  elements.amountValidationMsg.classList.add("hidden");
  elements.fieldAmount.classList.remove("border-error");

  setTransactionType("credit");
  switchView("confirm");
  validateConfirmForm();

  setTimeout(() => {
    if (!customerName) {
      elements.fieldCustomer.focus();
    } else {
      elements.fieldItem.focus();
    }
  }, 100);
}

async function handlePromptChip(promptText) {
  clearError();
  setVoiceSubState("processing");

  try {
    const res = await fetch("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: promptText }),
    });

    if (!res.ok) {
      throw new Error("Failed to parse prompt chip text");
    }

    const data = await res.json();
    handleTranscriptionResult(data);
  } catch (err) {
    console.error("Chip parse error:", err);
    showError("Could not process prompt. Please try again.");
    setVoiceSubState("idle");
  }
}

async function handleDeleteEntry(entryId, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }

  const ok = confirm("Are you sure you want to delete this entry? This will update the customer balance.");
  if (!ok) return;

  try {
    const res = await fetch(`/api/entries/${entryId}`, {
      method: "DELETE",
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to delete entry");
    }

    const data = await res.json();

    // If currently in ledger view, reload current customer ledger
    if (state.currentView === "ledger" && state.currentCustomerId) {
      state.currentCustomerBalance = data.balance;
      openCustomerLedger(state.currentCustomerId, state.currentCustomerName, data.balance);
    }

    loadCustomers();
  } catch (err) {
    console.error("Delete entry error:", err);
    showError(err.message || "Could not delete entry.");
  }
}

async function handleDeleteCustomer(customerId, customerName) {
  const ok = confirm(`Delete customer "${customerName}" and all their records?`);
  if (!ok) return;

  try {
    const res = await fetch(`/api/customers/${customerId}`, {
      method: "DELETE",
    });

    if (!res.ok) {
      throw new Error("Failed to delete customer");
    }

    switchView("home");
  } catch (err) {
    console.error("Delete customer error:", err);
    showError(err.message || "Could not delete customer.");
  }
}

// ---------------------------------------------------------------------------
// Initialization: Config & Initial Load
// ---------------------------------------------------------------------------
async function initApp() {
  try {
    const res = await fetch("/api/config");
    if (res.ok) {
      const data = await res.json();
      if (data.shop_name) {
        SHOP_NAME = data.shop_name;
        elements.shopNameHeader.textContent = SHOP_NAME;
      }
    }
  } catch (err) {
    console.warn("Could not load /api/config:", err);
  }

  // Global helpers exposed on window for inline handlers & debugging
  window.state = state;
  window.elements = elements;
  window.openManualEntry = openManualEntry;
  window.openCustomerLedger = openCustomerLedger;
  window.handleDeleteEntry = handleDeleteEntry;
  window.handleDeleteCustomer = handleDeleteCustomer;
  window.handlePromptChip = handlePromptChip;
  window.switchView = switchView;

  if (elements.btnManualEntry) {
    elements.btnManualEntry.addEventListener("click", (e) => {
      e.preventDefault();
      const cust = (state.currentView === "ledger" && state.currentCustomerName)
        ? state.currentCustomerName
        : "";
      openManualEntry(cust);
    });
  }

  if (elements.btnLedgerAddEntry) {
    elements.btnLedgerAddEntry.addEventListener("click", (e) => {
      e.preventDefault();
      openManualEntry(state.currentCustomerName || "");
    });
  }

  if (elements.btnDeleteCustomer) {
    elements.btnDeleteCustomer.addEventListener("click", (e) => {
      e.preventDefault();
      if (state.currentCustomerId && state.currentCustomerName) {
        handleDeleteCustomer(state.currentCustomerId, state.currentCustomerName);
      }
    });
  }

  // Voice Prompt Chips
  document.querySelectorAll(".voice-prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (prompt) {
        handlePromptChip(prompt);
      }
    });
  });

  // Unit Chips
  document.querySelectorAll(".unit-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const unit = chip.getAttribute("data-unit");
      if (unit && elements.fieldUnit) {
        elements.fieldUnit.value = unit;
        validateConfirmForm();
      }
    });
  });

  switchView("home");
}

// Robust execution: handles cases where DOMContentLoaded already fired
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}
