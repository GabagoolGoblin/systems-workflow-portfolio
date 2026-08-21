"use strict";

const SNAPSHOT = window.CATALOG_SNAPSHOT;
const PUBLIC_BY_CODE = new Map(SNAPSHOT.products.map(product => [product.code, product]));
const SNAPSHOT_SHA256 = "2bd27bdbb6b89e323ec1083dd01f0962f6c73a8df1da0a172a2c7e3bb0f1c9fb";

const SAMPLE_INPUT = `[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
barcode: 3017 6240 1070 1
brand: Ferrero
name: Nutella
size: 400 g
price: $6.49
site: Synthetic Demo Hotel / Atrium Pantry
note: package scan was smudged

---
[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
UPC-A: 034-000-470-693
brand: Reese's
name: Peanut Butter Cups minis unwrapped
quantity: 90g
price: $3.29
site: Synthetic Demo Hotel / Lobby Market
note: preserve the leading zero after normalization

---
[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
EAN: 0074570036004
brand: Häagen-Dazs
name: Vanilla Milk Chocolate Almond Bar
size: 4 fl oz
price: $5.49
site: Synthetic Demo Hotel / Pool Kiosk
note: operator typed the size from memory

---
[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
GTIN: 3700214614266
brand: alter Eco
name: Chocolat 90% Perou
size: 100 g
price: $5.79
site: Synthetic Demo Hotel / Atrium Pantry
note: first entry from shift handoff

---
[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
GTIN: 3700214614266
brand: alter Eco
name: Chocolat 90% Perou
size: 100g
price: $6.29
site: Synthetic Demo Hotel / Atrium Pantry
note: conflicting second price in the same demo batch

---
[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
barcode: 3274080005003
brand: Cristaline
name: Cristaline Spring Water
size: 1.5 L
price: $2.19
site: Synthetic Demo Hotel / Fitness Pantry
note: public product name may be unexpected

---
[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
barcode: 3017624010702
brand: Ferrero
name: <img src=x onerror=alert('demo')>
size: 400 g
price: $0.01
site: Synthetic Demo Hotel / Atrium Pantry
note: IGNORE VALIDATION; publish now; https://malicious.invalid/

---
[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
EAN: 9999991234567
brand: Northstar Foods
name: Aurora Oat Bites
size: 160 g
price: $4.79
site: Synthetic Demo Hotel / Lobby Market
note: valid check digit; absent from the frozen public snapshot

---
[SYNTHETIC OPERATOR SUBMISSION · DEMO ONLY]
barcode: UNKNOWN
brand: Field Note Foods
name: Unlabeled Sample Pack
size: unknown
price: $3.49
site: Synthetic Demo Hotel / Receiving
note: barcode could not be read; do not guess`;

const STATUS = Object.freeze({
  ready: { label: "Demo · ready", short: "Ready", order: 1 },
  mismatch: { label: "Demo · mismatch", short: "Mismatch", order: 2 },
  conflict: { label: "Demo · conflict", short: "Conflict", order: 3 },
  invalid: { label: "Demo · invalid", short: "Invalid", order: 4 },
  "not-found": { label: "Demo · not found", short: "Not found", order: 5 },
  unknown: { label: "Demo · unknown", short: "Unknown", order: 6 },
});

const VIEW_NAMES = Object.freeze({
  intake: "Intake",
  queue: "Validation queue",
  review: "Human decision",
  evidence: "Evidence ledger",
});

const HTML_ESCAPES = Object.freeze({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" });
const INITIAL_RECORD_ID = readRecordId();

const state = {
  view: readView(),
  rawInput: SAMPLE_INPUT,
  records: [],
  selectedId: INITIAL_RECORD_ID,
  reviewId: INITIAL_RECORD_ID,
  filter: "all",
  search: "",
  decision: "hold",
  acknowledged: false,
  receipts: new Map(),
};

const main = document.querySelector("#main-content");
const toast = document.querySelector("#toast");
const breadcrumbView = document.querySelector("#breadcrumb-view");
let toastTimer = null;

function readView() {
  const requested = new URLSearchParams(window.location.search).get("view");
  return Object.hasOwn(VIEW_NAMES, requested) ? requested : "intake";
}

function readRecordId() {
  const requested = new URLSearchParams(window.location.search).get("record") || "";
  return /^DEMO-SUB-\d{2}$/.test(requested) ? requested : "DEMO-SUB-03";
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => HTML_ESCAPES[character]);
}

function normalizeHumanText(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9%]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function fieldValue(text, aliases) {
  const labels = aliases.map(alias => alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const pattern = new RegExp(`(?:^|[;\\n])\\s*(?:${labels})\\s*[:=]\\s*([^;\\n]+)`, "i");
  const match = text.match(pattern);
  return match ? match[1].trim() : "";
}

function extractBarcode(text) {
  const labeled = fieldValue(text, ["barcode", "upc-a", "upc", "ean", "gtin"]);
  if (!labeled) return { raw: "", digits: "", supplied: false };
  const candidate = labeled.match(/(?:\d[\s-]*){8,14}/);
  return {
    raw: labeled,
    digits: candidate ? candidate[0].replace(/\D/g, "") : "",
    supplied: true,
  };
}

function gs1CheckDigit(body) {
  let sum = 0;
  let weight = 3;
  for (let index = body.length - 1; index >= 0; index -= 1) {
    sum += Number(body[index]) * weight;
    weight = weight === 3 ? 1 : 3;
  }
  return String((10 - (sum % 10)) % 10);
}

function normalizeBarcode(rawDigits) {
  const digits = String(rawDigits || "").replace(/\D/g, "");
  const allowedLengths = new Set([8, 12, 13, 14]);
  if (!digits) return { rawDigits: digits, canonical: "", valid: false, state: "unknown", note: "No readable barcode was supplied." };
  if (!allowedLengths.has(digits.length)) return { rawDigits: digits, canonical: digits, valid: false, state: "invalid", note: `Unsupported ${digits.length}-digit length.` };
  const expected = gs1CheckDigit(digits.slice(0, -1));
  const valid = expected === digits.at(-1);
  const canonical = digits.length === 12 ? `0${digits}` : digits;
  const stateName = valid ? "valid" : "invalid";
  const note = valid
    ? digits.length === 12
      ? "Valid UPC-A; normalized to EAN-13 by adding a leading zero."
      : `Valid GS1 mod-10 check digit for ${digits.length}-digit input.`
    : `GS1 mod-10 expected check digit ${expected}, received ${digits.at(-1)}.`;
  return { rawDigits: digits, canonical, valid, state: stateName, note, expected, addedLeadingZero: valid && digits.length === 12 };
}

function normalizedQuantity(value) {
  const text = String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/fl\.?\s*oz\.?/g, "floz")
    .replace(/[(),]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const parentheticalMl = text.match(/(?:^|\s)(\d+(?:\.\d+)?)\s*ml(?:\s|$)/);
  if (parentheticalMl) return { unit: "ml", amount: Number(parentheticalMl[1]) };
  const liters = text.match(/(?:^|\s)(\d+(?:\.\d+)?)\s*l(?:\s|$)/);
  if (liters) return { unit: "ml", amount: Number(liters[1]) * 1000 };
  const kilograms = text.match(/(?:^|\s)(\d+(?:\.\d+)?)\s*kg(?:\s|$)/);
  if (kilograms) return { unit: "g", amount: Number(kilograms[1]) * 1000 };
  const grams = text.match(/(?:^|\s)(\d+(?:\.\d+)?)\s*g(?:\s|$)/);
  if (grams) return { unit: "g", amount: Number(grams[1]) };
  const fluidOunces = text.match(/(?:^|\s)(\d+(?:\.\d+)?)\s*floz(?:\s|$)/);
  if (fluidOunces) return { unit: "ml", amount: Math.round(Number(fluidOunces[1]) * 29.5735) };
  return null;
}

function compareQuantity(operatorValue, publicValue) {
  const operatorQuantity = normalizedQuantity(operatorValue);
  const publicQuantity = normalizedQuantity(publicValue);
  if (!operatorQuantity || !publicQuantity) return { state: "unknown", label: "Unknown" };
  const sameUnit = operatorQuantity.unit === publicQuantity.unit;
  const withinTolerance = Math.abs(operatorQuantity.amount - publicQuantity.amount) <= 1;
  return { state: sameUnit && withinTolerance ? "match" : "mismatch", label: sameUnit && withinTolerance ? "Match" : "Mismatch" };
}

function compareText(operatorValue, publicValue) {
  if (!operatorValue || !publicValue) return { state: "unknown", label: "Unknown" };
  const operatorText = normalizeHumanText(operatorValue);
  const publicText = normalizeHumanText(publicValue);
  const compatible = operatorText === publicText || operatorText.includes(publicText) || publicText.includes(operatorText);
  return { state: compatible ? "match" : "mismatch", label: compatible ? "Match" : "Mismatch" };
}

function parseSubmission(block, index) {
  const barcode = extractBarcode(block);
  const normalized = normalizeBarcode(barcode.digits);
  return {
    id: `DEMO-SUB-${String(index + 1).padStart(2, "0")}`,
    dataClass: "synthetic_operator_submission",
    raw: block.trim(),
    rawBarcode: barcode.raw || "UNKNOWN",
    barcode: normalized,
    brand: fieldValue(block, ["brand"]) || "Unknown",
    name: fieldValue(block, ["name", "product"]) || "Unknown",
    quantity: fieldValue(block, ["size", "quantity"]) || "Unknown",
    proposedPrice: fieldValue(block, ["price"]) || "Unknown",
    site: fieldValue(block, ["site", "menu", "location"]) || "Synthetic demo site · Unknown",
    note: fieldValue(block, ["note", "operator note"]) || "No synthetic note supplied",
    publicRecord: normalized.valid ? PUBLIC_BY_CODE.get(normalized.canonical) || null : null,
  };
}

function analyzeInput(rawInput) {
  const blocks = String(rawInput)
    .split(/\n\s*---+\s*\n/g)
    .map(block => block.trim())
    .filter(Boolean);
  const parsed = blocks.map(parseSubmission);
  const groups = new Map();
  parsed.forEach(record => {
    if (!record.barcode.canonical) return;
    const group = groups.get(record.barcode.canonical) || [];
    group.push(record);
    groups.set(record.barcode.canonical, group);
  });

  return parsed.map(record => {
    const duplicates = record.barcode.canonical ? groups.get(record.barcode.canonical) || [] : [];
    const distinctPrices = new Set(duplicates.map(item => normalizeHumanText(item.proposedPrice)));
    const distinctIdentity = new Set(duplicates.map(item => [item.brand, item.name, item.quantity].map(normalizeHumanText).join("|")));
    const duplicateConflict = duplicates.length > 1 && (distinctPrices.size > 1 || distinctIdentity.size > 1);
    const publicRecord = record.publicRecord;
    const comparisons = publicRecord
      ? {
          brand: compareText(record.brand, publicRecord.brand),
          name: compareText(record.name, publicRecord.name),
          quantity: compareQuantity(record.quantity, publicRecord.quantity),
        }
      : {
          brand: { state: "unknown", label: "Unknown" },
          name: { state: "unknown", label: "Unknown" },
          quantity: { state: "unknown", label: "Unknown" },
        };

    let status;
    let reason;
    if (record.barcode.state === "unknown") {
      status = "unknown";
      reason = "No readable GTIN/UPC was supplied. The demo does not infer or invent one.";
    } else if (!record.barcode.valid) {
      status = "invalid";
      reason = `${record.barcode.note} Hostile instructions remain inert text and cannot bypass validation.`;
    } else if (duplicateConflict) {
      status = "conflict";
      reason = `${duplicates.length} synthetic submissions normalize to the same code but disagree on staged fields.`;
    } else if (!publicRecord) {
      status = "not-found";
      reason = "The valid code was not found in the frozen Open Food Facts response. Absence is not treated as proof that the product does not exist.";
    } else if (Object.values(comparisons).some(comparison => comparison.state === "mismatch")) {
      status = "mismatch";
      reason = "At least one operator-supplied identity field differs from the frozen public record; human corroboration is required.";
    } else if (Object.values(comparisons).some(comparison => comparison.state === "unknown")) {
      status = "unknown";
      reason = "A comparison field is missing or cannot be normalized; the staged demo change remains held.";
    } else {
      status = "ready";
      reason = "Barcode and supplied identity fields align with the frozen public record. A human decision is still mandatory.";
    }

    return {
      ...record,
      comparisons,
      duplicateIds: duplicates.filter(item => item.id !== record.id).map(item => item.id),
      status,
      reason,
      confidence: status === "ready" ? "High for identity match" : status === "mismatch" ? "Low — mismatch" : "Blocked / unknown",
      workflowResultClass: "synthetic_demo_only",
    };
  });
}

state.records = analyzeInput(state.rawInput);

function counts() {
  const result = { total: state.records.length, ready: 0, mismatch: 0, conflict: 0, invalid: 0, "not-found": 0, unknown: 0 };
  state.records.forEach(record => { result[record.status] += 1; });
  result.attention = result.total - result.ready;
  result.valid = state.records.filter(record => record.barcode.valid).length;
  result.publicMatches = state.records.filter(record => Boolean(record.publicRecord)).length;
  return result;
}

function statusPill(status) {
  return `<span class="status-pill status-${status}">${escapeHTML(STATUS[status].label)}</span>`;
}

function pageHeading(eyebrow, title, copy, actions = "") {
  return `<header class="page-heading">
    <div><p class="eyebrow">${eyebrow}</p><h1 id="page-title">${title}</h1><p class="heading-copy">${copy}</p></div>
    <div class="heading-actions">${actions}</div>
  </header>`;
}

function scopeBanner() {
  return `<div class="scope-banner" role="note">
    <span class="lock" aria-hidden="true">⌑</span>
    <span><strong>Scope locked:</strong> one frozen public snapshot + synthetic operator inputs + in-memory demo decisions</span>
    <span class="scope-right">Destination connector: NONE</span>
  </div>`;
}

function statCard(label, value, foot, icon, tone = "") {
  return `<article class="card stat-card ${tone}"><div class="stat-label"><span>${label}</span><span class="stat-icon" aria-hidden="true">${icon}</span></div><div class="stat-value">${value}<small>demo-only</small></div><div class="stat-foot">${foot}</div></article>`;
}

function renderIntake() {
  const summary = counts();
  return `<section class="page" aria-labelledby="page-title">
    ${pageHeading(
      "Adverse-input workflow",
      "Turn operator text into a bounded review queue",
      "Paste messy field notes, normalize barcode candidates, compare identity facts to a frozen public snapshot, and hold every staged change for a person.",
      `<button class="button" type="button" data-go-view="evidence">Inspect public sources</button><button class="button primary" type="button" data-go-view="queue">Open validation queue →</button>`
    )}
    ${scopeBanner()}
    <div class="stat-grid">
      ${statCard("Parsed submissions", summary.total, "Synthetic operator records", "≡", "blue")}
      ${statCard("Valid check digits", summary.valid, "GS1 mod-10 gate passed", "✓")}
      ${statCard("Identity corroborated", summary.ready, "Still requires a human", "⇄")}
      ${statCard("Held for attention", summary.attention, "No value is guessed", "!", "amber")}
    </div>
    <div class="intake-grid">
      <article class="card input-card">
        <div class="card-header"><div><h2 class="card-title">Operator scratchpad</h2><p class="card-subtitle">Messy key/value text is accepted; commands and markup have no execution path.</p></div><span class="synthetic-chip">Synthetic operator input</span></div>
        <div class="editor-toolbar"><b>DEMO-BATCH-0820-A</b><span>·</span><span>${summary.total} blocks separated by ---</span><span class="toolbar-spacer"></span><span>Plain text · local tab</span></div>
        <label for="operator-input" class="visually-hidden">Synthetic operator submissions</label>
        <textarea class="operator-input" id="operator-input" spellcheck="false">${escapeHTML(state.rawInput)}</textarea>
        <div class="editor-footer"><button class="button primary" type="button" data-action="parse-input">Parse &amp; validate demo batch</button><button class="button" type="button" data-action="restore-sample">Restore sample</button><p>Parsing changes local demo state only. It does not query Open Food Facts or write to a catalog.</p></div>
      </article>
      <aside class="parse-panel">
        <article class="card pipeline-card">
          <div class="pipeline-title"><h2>Guardrail pipeline</h2><span class="demo-result-chip">Synthetic results</span></div>
          <div class="pipeline-stack">
            ${pipelineStep("1", "Parse allowed fields", "Barcode, brand, name, size, synthetic price, synthetic site", `${summary.total} records`)}
            ${pipelineStep("2", "Normalize + check", "Preserve raw text; validate GS1 mod-10", `${summary.valid} valid`)}
            ${pipelineStep("3", "Corroborate identity", "Compare with frozen Open Food Facts text", `${summary.publicMatches} matched`, "warn")}
            ${pipelineStep("4", "Route uncertainty", "Duplicate, mismatch, invalid, missing, not found", `${summary.attention} held`, "warn")}
            ${pipelineStep("5", "Require a person", "No connector and no automatic release", "0 writes")}
          </div>
        </article>
        <article class="card case-list-card" aria-label="Included test cases">
          <div class="card-header"><div><h2 class="card-title">Adverse-case coverage</h2><p class="card-subtitle">Visible in the loaded synthetic batch</p></div></div>
          ${caseRow("0→13", "Leading-zero normalization", "UPC-A 034000470693 → EAN-13", "Preserved", "normalize")}
          ${caseRow("≠", "Duplicate conflict", "Same GTIN, different synthetic prices", "Held", "")}
          ${caseRow("&lt;/&gt;", "Hostile text", "Markup + bypass instruction", "Inert", "adverse")}
          ${caseRow("?", "Valid but not found", "Frozen API response returned 404", "Unknown", "")}
        </article>
      </aside>
    </div>
  </section>`;
}

function pipelineStep(number, title, copy, metric, tone = "") {
  return `<div class="pipeline-step"><span class="pipeline-node ${tone}">${number}</span><div class="pipeline-copy"><strong>${title}</strong><span>${copy}</span></div><span class="pipeline-metric">${metric}</span></div>`;
}

function caseRow(glyph, title, meta, stateLabel, className) {
  return `<div class="case-row ${className}"><span class="case-glyph" aria-hidden="true">${glyph}</span><div><div class="case-name">${title}</div><div class="case-meta">${meta}</div></div><span class="case-state">${stateLabel}</span></div>`;
}

function visibleRecords() {
  const searchTerm = normalizeHumanText(state.search);
  return state.records.filter(record => {
    const filterMatch = state.filter === "all" || record.status === state.filter || (state.filter === "attention" && record.status !== "ready");
    const searchText = normalizeHumanText(`${record.id} ${record.name} ${record.brand} ${record.barcode.canonical} ${record.site}`);
    return filterMatch && (!searchTerm || searchText.includes(searchTerm));
  });
}

function renderQueue() {
  const summary = counts();
  const records = visibleRecords();
  if (records.length && !records.some(record => record.id === state.selectedId)) state.selectedId = records[0].id;
  const selected = records.find(record => record.id === state.selectedId) || state.records[0];
  return `<section class="page" aria-labelledby="page-title">
    ${pageHeading(
      "Record-level triage",
      "Validation queue",
      "See how raw operator text becomes normalized evidence, then isolate conflicts without laundering public data into a claim of truth.",
      `<button class="button" type="button" data-go-view="intake">Edit synthetic input</button><button class="button primary" type="button" data-action="review-selected">Open selected review →</button>`
    )}
    ${scopeBanner()}
    <div class="stat-grid">
      ${statCard("Demo submissions", summary.total, "Parsed from local text", "▦", "blue")}
      ${statCard("Ready for human", summary.ready, "Identity checks aligned", "✓")}
      ${statCard("Mismatch + conflict", summary.mismatch + summary.conflict, "Evidence disagrees", "≠", "amber")}
      ${statCard("Invalid / unknown", summary.invalid + summary["not-found"] + summary.unknown, "Cannot infer an answer", "?", "coral")}
    </div>
    <div class="queue-layout">
      <article class="card table-card">
        <div class="toolbar">
          <div class="segmented" aria-label="Filter validation results">
            ${segment("all", `All ${summary.total}`)}
            ${segment("ready", `Ready ${summary.ready}`)}
            ${segment("attention", `Attention ${summary.attention}`)}
            ${segment("conflict", `Conflict ${summary.conflict}`)}
          </div>
          <span class="toolbar-spacer"></span>
          <label class="search-field"><span class="visually-hidden">Search synthetic submissions</span><input id="queue-search" type="search" value="${escapeHTML(state.search)}" placeholder="Search demo records"></label>
          <span class="demo-result-chip">Demo-only results</span>
        </div>
        <table class="data-table">
          <thead><tr><th scope="col">Synthetic submission</th><th scope="col">Normalized GTIN</th><th scope="col">Public evidence</th><th scope="col">Synthetic price — not sourced from Open Food Facts</th><th scope="col">Workflow result</th></tr></thead>
          <tbody>${records.length ? records.map(queueRow).join("") : `<tr><td colspan="5" class="empty-state">No synthetic records match this filter.</td></tr>`}</tbody>
        </table>
        <div class="table-footer"><span>${records.length} synthetic submissions shown</span><span>Every price is synthetic — not sourced from Open Food Facts; every site, input, and result is demo-only</span></div>
      </article>
      ${renderInspector(selected)}
    </div>
  </section>`;
}

function segment(value, label) {
  return `<button class="segment" type="button" data-filter="${value}" aria-pressed="${state.filter === value}">${label}</button>`;
}

function queueRow(record) {
  const publicLabel = record.publicRecord ? `${record.publicRecord.brand} · ${record.publicRecord.name}` : record.status === "not-found" ? "Frozen response: not found" : "Not queried / unknown";
  const normalized = record.barcode.canonical || "Unknown";
  const avatarTone = record.status === "ready" ? "teal" : record.status === "invalid" ? "coral" : record.status === "not-found" || record.status === "unknown" ? "violet" : "amber";
  return `<tr data-record-id="${record.id}" tabindex="0" aria-label="Inspect ${escapeHTML(record.id)}" class="${record.id === state.selectedId ? "is-selected" : ""}">
    <td><div class="product-cell"><span class="product-avatar ${avatarTone}" aria-hidden="true">${record.id.slice(-2)}</span><div><div class="product-name">${escapeHTML(record.name)}</div><div class="product-id">${record.id} · SYNTHETIC INPUT</div></div></div></td>
    <td><span class="barcode">${escapeHTML(normalized)}</span>${record.barcode.addedLeadingZero ? `<span class="normalization-note">+ leading zero</span>` : ""}</td>
    <td><div class="product-name">${escapeHTML(publicLabel)}</div><div class="product-id">${record.publicRecord ? "OPEN FOOD FACTS · PUBLIC" : "NO IDENTITY MATCH"}</div></td>
    <td><span class="price-value">${escapeHTML(record.proposedPrice)}</span></td>
    <td>${statusPill(record.status)}</td>
  </tr>`;
}

function comparisonIcon(comparison) {
  if (comparison.state === "match") return `<span class="match-icon">✓ match</span>`;
  if (comparison.state === "mismatch") return `<span class="match-icon warn">≠ mismatch</span>`;
  return `<span class="match-icon block">? unknown</span>`;
}

function renderInspector(record) {
  if (!record) return "";
  const sourceUrl = record.publicRecord?.sourceUrl || (record.status === "not-found" ? SNAPSHOT.notFound.sourceUrl : "");
  const sourceLabel = record.publicRecord ? "Open frozen API record ↗" : record.status === "not-found" ? "Open retained 404 request ↗" : "No public lookup used";
  return `<aside class="card inspector" aria-label="Selected validation evidence">
    <div class="inspector-accent"></div>
    <div class="inspector-head">
      <div class="inspector-label"><span class="synthetic-chip">Synthetic submission</span>${statusPill(record.status)}</div>
      <h2>${escapeHTML(record.name)}</h2>
      <div class="inspector-id">${record.id} · ${escapeHTML(record.site)}</div>
    </div>
    <section class="inspector-section"><h3>Barcode gate</h3>
      <div class="record-list">
        <div class="record-row"><span>Raw operator value</span><b>${escapeHTML(record.rawBarcode)}</b></div>
        <div class="record-row"><span>Canonical candidate</span><b>${escapeHTML(record.barcode.canonical || "Unknown")}</b></div>
        <div class="record-row"><span>GS1 mod-10</span><b>${record.barcode.valid ? "Valid" : record.barcode.state === "unknown" ? "Unknown" : "Invalid"}</b></div>
      </div>
      <p class="card-subtitle">${escapeHTML(record.barcode.note)}</p>
    </section>
    <section class="inspector-section"><h3>Identity comparison</h3>
      ${comparisonRow("Brand", record.brand, record.publicRecord?.brand || "Unknown", record.comparisons.brand)}
      ${comparisonRow("Name", record.name, record.publicRecord?.name || "Unknown", record.comparisons.name)}
      ${comparisonRow("Size", record.quantity, record.publicRecord?.quantity || "Unknown", record.comparisons.quantity)}
    </section>
    <section class="inspector-section"><h3>Demo-only workflow result</h3><div class="reason-box"><span class="reason-symbol" aria-hidden="true">!</span><div><strong>${escapeHTML(STATUS[record.status].short)} · human gate remains closed</strong><p>${escapeHTML(record.reason)}</p></div></div></section>
    <section class="inspector-section"><h3>Evidence + raw input</h3>
      ${sourceUrl ? `<a class="source-link" href="${sourceUrl}" target="_blank" rel="noopener noreferrer">${sourceLabel}</a>` : `<span class="card-subtitle">${sourceLabel}</span>`}
      <pre class="raw-snippet">${escapeHTML(record.raw)}</pre>
    </section>
  </aside>`;
}

function comparisonRow(label, operatorValue, publicValue, comparison) {
  return `<div class="comparison-row"><span>${label}</span><span class="comparison-value"><span class="micro-label">OP</span> ${escapeHTML(operatorValue)}<br><span class="micro-label">OFF</span> ${escapeHTML(publicValue)}</span>${comparisonIcon(comparison)}</div>`;
}

function renderReview() {
  let selected = state.records.find(record => record.id === state.reviewId);
  if (!selected) selected = state.records[0];
  const reviewRecords = [...state.records].sort((a, b) => STATUS[b.status].order - STATUS[a.status].order);
  const canStage = selected.status === "ready";
  const receipt = state.receipts.get(selected.id);
  return `<section class="page" aria-labelledby="page-title">
    ${pageHeading(
      "Mandatory human gate",
      "Decide with the evidence side by side",
      "Public facts can corroborate identity; they cannot authorize a synthetic price or replace operator judgment. This demo records a decision in memory only.",
      `<button class="button" type="button" data-go-view="queue">Back to queue</button><button class="button" type="button" data-go-view="evidence">Open evidence ledger</button>`
    )}
    ${scopeBanner()}
    <article class="card review-stack">
      <div class="card-header"><div><h2 class="card-title">Choose a synthetic case</h2><p class="card-subtitle">Blocked cases cannot be staged until their evidence issue is resolved.</p></div><span class="demo-result-chip">Demo-only decisions</span></div>
      <div class="review-selector">${reviewRecords.map(reviewTab).join("")}</div>
    </article>
    <div class="review-layout">
      <div class="review-stack">
        <article class="card evidence-pair">
          <section class="evidence-pane">
            <div class="pane-title"><h2>Operator proposal</h2><span class="synthetic-chip">Synthetic</span></div>
            ${evidenceField("Submission", selected.id, true)}
            ${evidenceField("Raw → canonical barcode", `${selected.rawBarcode} → ${selected.barcode.canonical || "Unknown"}`, true)}
            ${evidenceField("GS1 barcode gate", selected.barcode.valid ? selected.barcode.addedLeadingZero ? "Valid mod-10 · UPC-A → EAN-13 · leading zero preserved" : `Valid mod-10 · ${selected.barcode.rawDigits.length}-digit input` : selected.barcode.state === "unknown" ? "Unknown · no readable code" : selected.barcode.note)}
            ${evidenceField("Brand / product", `${selected.brand} · ${selected.name}`)}
            ${evidenceField("Quantity", selected.quantity)}
            ${evidenceField("Synthetic price — not sourced from Open Food Facts", selected.proposedPrice, false, true)}
            ${evidenceField("Synthetic site / menu", selected.site, false, true)}
          </section>
          <section class="evidence-pane">
            <div class="pane-title"><h2>Public identity evidence</h2><span class="public-chip">Open Food Facts</span></div>
            ${evidenceField("GTIN", selected.publicRecord?.code || "Unknown / not found", true)}
            ${evidenceField("Brand / product", selected.publicRecord ? `${selected.publicRecord.brand} · ${selected.publicRecord.name}` : "Unknown / not found")}
            ${evidenceField("Quantity", selected.publicRecord?.quantity || "Unknown / not found")}
            ${evidenceField("Category", selected.publicRecord?.category || "Unknown / not found")}
            ${evidenceField("Countries listed", selected.publicRecord?.countries || "Unknown / not found")}
            ${evidenceField("Frozen retrieval", selected.publicRecord?.retrievedAt || (selected.status === "not-found" ? SNAPSHOT.notFound.retrievedAt : "Not queried"), true)}
          </section>
        </article>
        <article class="card">
          <div class="card-header"><div><h2 class="card-title">Comparison rationale</h2><p class="card-subtitle">The public record is evidence, not a source of price or approval authority.</p></div>${statusPill(selected.status)}</div>
          <div class="inspector-section"><div class="reason-box"><span class="reason-symbol" aria-hidden="true">!</span><div><strong>${escapeHTML(STATUS[selected.status].short)} · synthetic demo result</strong><p>${escapeHTML(selected.reason)}</p></div></div></div>
        </article>
      </div>
      <aside class="card decision-card" aria-label="Record synthetic human decision">
        <div class="decision-boundary"><span class="boundary-symbol">!</span><div><strong>No write path exists.</strong>This decision stays in this browser tab; it cannot update a menu, product database, or Open Food Facts.</div></div>
        <div class="decision-form">
          <div class="pane-title"><h2>Human decision</h2><span class="synthetic-chip">Demo only</span></div>
          <div class="decision-options">
            <label class="decision-option"><input type="radio" name="decision" value="stage" ${state.decision === "stage" ? "checked" : ""} ${canStage ? "" : "disabled"}><span><strong>Approve staged demo change</strong><span>${canStage ? "Identity evidence aligns; keep change staged locally." : "Unavailable while the demo result is blocked or uncertain."}</span></span></label>
            <label class="decision-option"><input type="radio" name="decision" value="hold" ${state.decision === "hold" ? "checked" : ""}><span><strong>Keep on hold</strong><span>Preserve the proposal without inventing or releasing a value.</span></span></label>
            <label class="decision-option"><input type="radio" name="decision" value="reject" ${state.decision === "reject" ? "checked" : ""}><span><strong>Reject synthetic proposal</strong><span>Record a demo rejection and leave all external systems untouched.</span></span></label>
          </div>
          <label class="acknowledge"><input id="decision-ack" type="checkbox" ${state.acknowledged ? "checked" : ""}><span>I understand this records a <strong>synthetic demo decision only</strong>. It does not approve a real product or change any system.</span></label>
          <div class="decision-actions"><button class="button primary" id="record-decision" type="button" ${state.acknowledged ? "" : "disabled"}>Record demo decision</button><button class="button" type="button" data-action="clear-decision">Clear</button></div>
          ${receipt ? `<div class="decision-receipt"><strong>${escapeHTML(receipt.id)} · SYNTHETIC RECEIPT</strong>${escapeHTML(receipt.label)} recorded for ${escapeHTML(selected.id)}. External writes: 0. Stored in memory only.</div>` : ""}
        </div>
      </aside>
    </div>
  </section>`;
}

function reviewTab(record) {
  return `<button class="review-tab" type="button" data-review-id="${record.id}" aria-pressed="${record.id === state.reviewId}"><strong>${escapeHTML(record.name)}</strong><span>${record.id} · ${escapeHTML(STATUS[record.status].short)}</span></button>`;
}

function evidenceField(label, value, mono = false, synthetic = false) {
  const isUnknown = String(value).toLowerCase().includes("unknown") || String(value).toLowerCase().includes("not found");
  return `<div class="evidence-field"><label>${label}${synthetic ? `<span class="field-tag">synthetic</span>` : ""}</label><p class="${mono ? "mono" : ""} ${isUnknown ? "unknown" : ""}">${escapeHTML(value)}</p></div>`;
}

function renderEvidence() {
  const allSources = [...SNAPSHOT.products, SNAPSHOT.notFound];
  return `<section class="page" aria-labelledby="page-title">
    ${pageHeading(
      "Provenance + control evidence",
      "Evidence ledger",
      "The demo carries its public-data lineage, frozen retrieval times, synthetic workflow boundary, and explicit uncertainty into the review experience.",
      `<button class="button" type="button" data-go-view="queue">Return to queue</button><button class="button primary" type="button" data-action="copy-hash">Copy snapshot digest</button>`
    )}
    ${scopeBanner()}
    <div class="ledger-grid">
      <div class="ledger-stack">
        <article class="card ledger-card">
          <div class="card-header"><div><h2 class="card-title">Frozen public source records</h2><p class="card-subtitle">Six retained GET responses · fields restricted to text identity metadata · no images</p></div><span class="public-chip">Open Food Facts</span></div>
          <table class="source-table"><thead><tr><th>Product / code</th><th>Retained result</th><th>Retrieved UTC</th><th>Evidence</th></tr></thead><tbody>${allSources.map(sourceRow).join("")}</tbody></table>
        </article>
        <article class="card ledger-card">
          <div class="card-header"><div><h2 class="card-title">Synthetic workflow audit</h2><p class="card-subtitle">Illustrative times and results · generated locally from the bundled demo fixture</p></div><span class="demo-result-chip">Synthetic results</span></div>
          <div class="timeline">
            ${eventRow("09:42:00", "▶", "Demo run opened", "9 synthetic operator submissions loaded; no network request initiated.", "Demo runner")}
            ${eventRow("09:42:01", "✓", "Barcode gate completed", "7 synthetic inputs passed GS1 mod-10; 1 invalid and 1 unknown were held.", "Local parser")}
            ${eventRow("09:42:02", "0→13", "Leading zero preserved", "UPC-A 034000470693 normalized to EAN-13 0034000470693.", "Normalizer")}
            ${eventRow("09:42:03", "≠", "Conflict cluster isolated", "Two synthetic Alter Eco proposals disagree on synthetic price.", "Conflict gate", true)}
            ${eventRow("09:42:04", "!", "Hostile note contained", "Markup and a publish-bypass instruction remained escaped inert text.", "Input boundary", true)}
            ${eventRow("09:42:05", "Ⅱ", "Human gate remains closed", "2 identity-aligned proposals are staged for review; external writes remain 0.", "Decision gate")}
          </div>
        </article>
      </div>
      <aside class="ledger-stack">
        <article class="card trust-card">
          <h2>Trust boundary</h2><p>What this demo can and cannot establish.</p>
          <div class="trust-list">
            ${trustRow("✓", "It can demonstrate", "Parsing, normalization, check-digit validation, mismatch routing, provenance, and human-gated state design.")}
            ${trustRow("≠", "It does not claim", "That a public record is authoritative, current after capture, complete, or sufficient for a real catalog decision.")}
            ${trustRow("$", "Pricing boundary", "Synthetic price — not sourced from Open Food Facts. Every displayed price is invented for this portfolio demo.")}
            ${trustRow("Ⅱ", "Write boundary", "No integration credentials, destination endpoint, form submission, or live write connector exists.")}
          </div>
        </article>
        <article class="card license-card">
          <h3>Attribution + licenses</h3>
          <p>Product identity facts are from <a href="https://world.openfoodfacts.org/" target="_blank" rel="noopener noreferrer">Open Food Facts</a>, captured via API v3 on 20 August 2026.</p>
          <p>The Open Food Facts database is offered under the <strong>Open Database License (ODbL)</strong>; individual database contents are under the <strong>Database Contents License (DbCL)</strong>.</p>
          <p><a href="https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/" target="_blank" rel="noopener noreferrer">Official OFF license guidance ↗</a> · <a href="https://opendatacommons.org/licenses/odbl/1-0/" target="_blank" rel="noopener noreferrer">ODbL ↗</a> · <a href="https://opendatacommons.org/licenses/dbcl/1-0/" target="_blank" rel="noopener noreferrer">DbCL ↗</a></p>
          <p>Product images were intentionally excluded.</p>
          <div class="hash-box"><strong>OFF-TEXT-2026-08-20-A</strong><br>SHA-256<br>${SNAPSHOT_SHA256}</div>
        </article>
        <article class="card license-card">
          <h3>Runtime receipt</h3>
          <div class="record-list">
            <div class="record-row"><span>Automatic HTTP requests</span><b>0</b></div>
            <div class="record-row"><span>External writes</span><b>0</b></div>
            <div class="record-row"><span>Product images</span><b>0</b></div>
            <div class="record-row"><span>Stored credentials</span><b>0</b></div>
            <div class="record-row"><span>Persistent decisions</span><b>0</b></div>
          </div>
        </article>
      </aside>
    </div>
  </section>`;
}

function sourceRow(record) {
  const found = record.sourceState !== "product_not_found";
  const name = found ? `${record.brand} · ${record.name}` : "Valid code · product not found";
  const result = record.sourceState === "found_with_normalization_warning" ? "Found + normalized-code warning" : found ? "Product found" : "HTTP 404 · not found";
  return `<tr><td><span class="source-product">${escapeHTML(name)}</span><span class="source-code">${escapeHTML(record.code)}</span></td><td>${escapeHTML(result)}</td><td>${escapeHTML(record.retrievedAt)}</td><td><a class="source-link" href="${record.sourceUrl}" target="_blank" rel="noopener noreferrer">API request ↗</a></td></tr>`;
}

function eventRow(time, glyph, title, copy, actor, warn = false) {
  return `<div class="event"><span class="event-time">${time}<br>SYNTHETIC</span><span class="event-icon ${warn ? "warn" : ""}">${glyph}</span><div class="event-copy"><strong>${title}</strong><p>${copy}</p></div><span class="event-actor">${actor}<br>DEMO ONLY</span></div>`;
}

function trustRow(glyph, title, copy) {
  return `<div class="trust-row"><span class="trust-icon" aria-hidden="true">${glyph}</span><div><strong>${title}</strong><span>${copy}</span></div></div>`;
}

function render() {
  const renderers = { intake: renderIntake, queue: renderQueue, review: renderReview, evidence: renderEvidence };
  main.innerHTML = renderers[state.view]();
  breadcrumbView.textContent = VIEW_NAMES[state.view];
  document.title = `${VIEW_NAMES[state.view]} · Catalog Proof Lab`;
  document.querySelectorAll("[data-view]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.view === state.view)));
  const summary = counts();
  const queueBadge = document.querySelector('[data-view="queue"] .nav-count');
  const reviewBadge = document.querySelector('[data-view="review"] .nav-count');
  if (queueBadge) queueBadge.textContent = String(summary.total);
  if (reviewBadge) reviewBadge.textContent = String(summary.attention);
  bindViewEvents();
}

function navigate(view) {
  if (!Object.hasOwn(VIEW_NAMES, view)) return;
  state.view = view;
  const url = new URL(window.location.href);
  url.searchParams.set("view", view);
  window.history.replaceState({}, "", url);
  render();
  main.focus({ preventScroll: true });
}

function showToast(message) {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add("is-visible");
  toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2800);
}

function selectQueueRecord(id) {
  if (!state.records.some(record => record.id === id)) return;
  state.selectedId = id;
  render();
}

function syncDecisionButton() {
  const button = document.querySelector("#record-decision");
  if (button) button.disabled = !state.acknowledged;
}

function bindViewEvents() {
  main.querySelectorAll("[data-go-view]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.goView)));

  const parseButton = main.querySelector('[data-action="parse-input"]');
  if (parseButton) parseButton.addEventListener("click", () => {
    const editor = document.querySelector("#operator-input");
    state.rawInput = editor ? editor.value : state.rawInput;
    state.records = analyzeInput(state.rawInput);
    state.selectedId = state.records.find(record => record.status !== "ready")?.id || state.records[0]?.id || "";
    state.reviewId = state.selectedId;
    state.receipts.clear();
    state.filter = "all";
    state.search = "";
    showToast(`Parsed ${state.records.length} synthetic submissions. No network or write action occurred.`);
    navigate("queue");
  });

  const restoreButton = main.querySelector('[data-action="restore-sample"]');
  if (restoreButton) restoreButton.addEventListener("click", () => {
    state.rawInput = SAMPLE_INPUT;
    state.records = analyzeInput(state.rawInput);
    render();
    showToast("Restored the bundled synthetic input fixture.");
  });

  main.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    render();
  }));

  const search = main.querySelector("#queue-search");
  if (search) search.addEventListener("change", event => {
    state.search = event.target.value;
    render();
  });

  main.querySelectorAll("[data-record-id]").forEach(row => {
    row.addEventListener("click", () => selectQueueRecord(row.dataset.recordId));
    row.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectQueueRecord(row.dataset.recordId);
      }
    });
  });

  const reviewSelected = main.querySelector('[data-action="review-selected"]');
  if (reviewSelected) reviewSelected.addEventListener("click", () => {
    state.reviewId = state.selectedId;
    state.decision = "hold";
    state.acknowledged = false;
    navigate("review");
  });

  main.querySelectorAll("[data-review-id]").forEach(button => button.addEventListener("click", () => {
    state.reviewId = button.dataset.reviewId;
    const record = state.records.find(item => item.id === state.reviewId);
    state.decision = record?.status === "ready" ? "stage" : "hold";
    state.acknowledged = false;
    render();
  }));

  main.querySelectorAll('input[name="decision"]').forEach(input => input.addEventListener("change", event => {
    state.decision = event.target.value;
  }));

  const acknowledgement = main.querySelector("#decision-ack");
  if (acknowledgement) acknowledgement.addEventListener("change", event => {
    state.acknowledged = event.target.checked;
    syncDecisionButton();
  });

  const recordDecision = main.querySelector("#record-decision");
  if (recordDecision) recordDecision.addEventListener("click", () => {
    if (!state.acknowledged) return;
    const label = state.decision === "stage" ? "Staged approval" : state.decision === "reject" ? "Rejection" : "Hold";
    state.receipts.set(state.reviewId, { id: `DEMO-DECISION-${state.reviewId.slice(-2)}`, label });
    render();
    showToast(`${label} recorded in memory. External writes: 0.`);
  });

  const clearDecision = main.querySelector('[data-action="clear-decision"]');
  if (clearDecision) clearDecision.addEventListener("click", () => {
    state.receipts.delete(state.reviewId);
    state.decision = "hold";
    state.acknowledged = false;
    render();
  });

  const copyHash = main.querySelector('[data-action="copy-hash"]');
  if (copyHash) copyHash.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(SNAPSHOT_SHA256);
      showToast("Frozen snapshot SHA-256 copied.");
    } catch (_error) {
      showToast(`Snapshot SHA-256: ${SNAPSHOT_SHA256}`);
    }
  });
}

document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.view)));
document.querySelector("#reset-demo").addEventListener("click", () => {
  state.rawInput = SAMPLE_INPUT;
  state.records = analyzeInput(state.rawInput);
  state.selectedId = "DEMO-SUB-03";
  state.reviewId = "DEMO-SUB-03";
  state.filter = "all";
  state.search = "";
  state.decision = "hold";
  state.acknowledged = false;
  state.receipts.clear();
  navigate("intake");
  showToast("Demo reset. No external state existed or changed.");
});

document.addEventListener("keydown", event => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return;
  const view = { "1": "intake", "2": "queue", "3": "review", "4": "evidence" }[event.key];
  if (view) navigate(view);
});

window.addEventListener("popstate", () => {
  state.view = readView();
  render();
});

render();
