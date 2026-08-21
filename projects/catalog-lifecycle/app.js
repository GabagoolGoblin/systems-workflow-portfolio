"use strict";

// Every name, identifier, location, value, and event below is deliberately invented.
const DEMO_DATA = Object.freeze({
  run: {
    id: "RUN-24871",
    name: "Regional beverage price refresh",
    scope: "Desert Harbor · Southwest region",
    started: "09:42:16",
    progress: 75,
  },
  records: [
    { id: "SYN-1042", initials: "CP", tone: "coral", name: "Canyon Peach Sparkler", location: "Atrium Market", before: "$4.20", after: "$4.45", delta: "+6.0%", property: "Price", status: "verified", reason: "Matched source value and expected rounding policy.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1057", initials: "NM", tone: "blue", name: "Night Mesa Tonic", location: "Pool Kiosk", before: "$3.80", after: "$3.95", delta: "+3.9%", property: "Price", status: "verified", reason: "Matched source value and location scope.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1061", initials: "JL", tone: "green", name: "Juniper Lime Soda", location: "Lobby Pantry", before: "$4.10", after: "$4.10", delta: "0.0%", property: "Price", status: "verified", reason: "No change required after comparison.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1088", initials: "DS", tone: "gold", name: "Dune Salt Lemonade", location: "Atrium Market", before: "$4.35", after: "Unknown", delta: "—", property: "Price", status: "held", reason: "The proposed value is absent. Policy requires a human decision; the demo never guesses.", source: "Price plan 04", confidence: "Blocked" },
    { id: "SYN-1093", initials: "RM", tone: "violet", name: "Red Mesa Cold Brew", location: "Lobby Pantry", before: "$5.40", after: "$5.85", delta: "+8.3%", property: "Price", status: "review", reason: "Change exceeds the illustrative 8% review threshold.", source: "Price plan 04", confidence: "Medium" },
    { id: "SYN-1104", initials: "AS", tone: "blue", name: "Agave Sky Water", location: "Pool Kiosk", before: "$3.25", after: "$3.10", delta: "−4.6%", property: "Price", status: "verified", reason: "Matched source value and expected rounding policy.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1119", initials: "DR", tone: "coral", name: "Desert Rose Seltzer", location: "Atrium Market", before: "$3.90", after: "$4.05", delta: "+3.8%", property: "Price", status: "verified", reason: "Matched source value and expected rounding policy.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1126", initials: "CR", tone: "gold", name: "Copper Ridge Tea", location: "Lobby Pantry", before: "$4.60", after: "$4.80", delta: "+4.3%", property: "Price", status: "verified", reason: "Matched source value and location scope.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1138", initials: "OB", tone: "green", name: "Ocotillo Berry Fizz", location: "Pool Kiosk", before: "$4.15", after: "$4.25", delta: "+2.4%", property: "Price", status: "verified", reason: "Matched source value and expected rounding policy.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1152", initials: "EC", tone: "violet", name: "Ember Citrus Tonic", location: "Atrium Market", before: "$4.70", after: "$4.95", delta: "+5.3%", property: "Price", status: "verified", reason: "Matched source value and location scope.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1167", initials: "SM", tone: "blue", name: "Sandstone Mint Water", location: "Lobby Pantry", before: "$3.45", after: "$3.55", delta: "+2.9%", property: "Price", status: "verified", reason: "Matched source value and expected rounding policy.", source: "Price plan 04", confidence: "High" },
    { id: "SYN-1174", initials: "SV", tone: "gold", name: "Sun Valley Ginger Ale", location: "Pool Kiosk", before: "$4.05", after: "$4.30", delta: "+6.2%", property: "Price", status: "held", reason: "The source location label is ambiguous. The record remains unchanged until a reviewer confirms scope.", source: "Price plan 04", confidence: "Blocked" },
  ],
  queue: [
    { glyph: "04", name: "Regional beverage price refresh", meta: ["12 records", "Desert Harbor"], side: "9 verified", detail: "1 action required", status: "running" },
    { glyph: "05", name: "Lobby pantry assortment sync", meta: ["8 records", "Juniper House"], side: "Queued", detail: "starts after review", status: "queued" },
    { glyph: "03", name: "Seasonal availability closeout", meta: ["15 records", "Desert Harbor"], side: "Complete", detail: "09:31", status: "verified" },
  ],
  events: [
    { time: "09:42:16", symbol: "▶", title: "Run opened", copy: "12 synthetic records loaded from price plan 04.", actor: "Demo runner", tone: "ok" },
    { time: "09:42:18", symbol: "✓", title: "Scope contract passed", copy: "Region, property, and record-count boundaries matched the run plan.", actor: "Guardrail", tone: "ok" },
    { time: "09:42:21", symbol: "⇄", title: "Batch comparison produced", copy: "Before/after values normalized; no external writes were attempted.", actor: "Diff engine", tone: "ok" },
    { time: "09:42:23", symbol: "!", title: "Unknown value held", copy: "SYN-1088 was routed to human review instead of receiving a guessed price.", actor: "Guardrail", tone: "warn", recordId: "SYN-1088" },
    { time: "09:42:24", symbol: "!", title: "Threshold review opened", copy: "SYN-1093 exceeded the illustrative 8% review threshold.", actor: "Policy check", tone: "warn", recordId: "SYN-1093" },
    { time: "09:42:26", symbol: "#", title: "Evidence snapshot sealed", copy: "Synthetic input, diff, and event manifests received local demo digests.", actor: "Audit recorder", tone: "ok" },
  ],
});

const VIEW_TITLES = Object.freeze({
  control: "Control center",
  diff: "Batch diff",
  approval: "Human review",
  audit: "Audit trail",
});

const HTML_ESCAPES = Object.freeze({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" });

const state = {
  view: readView(),
  filter: "all",
  search: "",
  selectedId: "SYN-1088",
  decision: "hold",
  decisionRecorded: false,
};

const main = document.querySelector("#main-content");
const toast = document.querySelector("#toast");
let toastTimer = null;

function readView() {
  const requested = new URLSearchParams(window.location.search).get("view");
  return Object.hasOwn(VIEW_TITLES, requested) ? requested : "control";
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, character => HTML_ESCAPES[character]);
}

function statusPill(status, label) {
  const safeLabel = label || status;
  return `<span class="status-pill status-${status}">${safeLabel}</span>`;
}

function pageHeading(eyebrow, title, copy, actions = "") {
  return `
    <header class="page-heading">
      <div>
        <p class="eyebrow">${eyebrow}</p>
        <h1>${title}</h1>
        <p class="heading-copy">${copy}</p>
      </div>
      <div class="heading-actions">${actions}</div>
    </header>`;
}

function renderControl() {
  return `
    <section class="page" aria-labelledby="page-title">
      ${pageHeading(
        "Implementation operations",
        `<span id="page-title">Control center</span>`,
        "One screen for run health, exception routing, and scope-aware catalog changes.",
        `<button class="button" type="button" data-action="export-manifest">Export demo snapshot</button>
         <button class="button primary" type="button" data-go-view="diff">Review 3 exceptions →</button>`
      )}

      <div class="stat-grid" aria-label="Current run summary">
        <article class="card stat-card">
          <div class="stat-label"><span>Records in scope</span><span class="stat-icon" aria-hidden="true">▦</span></div>
          <div class="stat-value">12 <span class="stat-note">1 location</span></div>
          <div class="stat-line blue"><span style="width:100%"></span></div>
        </article>
        <article class="card stat-card">
          <div class="stat-label"><span>Verified</span><span class="stat-icon" aria-hidden="true">✓</span></div>
          <div class="stat-value">9 <span class="stat-note">75% complete</span></div>
          <div class="stat-line"><span style="width:75%"></span></div>
        </article>
        <article class="card stat-card">
          <div class="stat-label"><span>Needs review</span><span class="stat-icon" aria-hidden="true">?</span></div>
          <div class="stat-value">1 <span class="stat-note">threshold</span></div>
          <div class="stat-line amber"><span style="width:8%"></span></div>
        </article>
        <article class="card stat-card">
          <div class="stat-label"><span>Held safely</span><span class="stat-icon" aria-hidden="true">Ⅱ</span></div>
          <div class="stat-value">2 <span class="stat-note">no writes</span></div>
          <div class="stat-line amber"><span style="width:17%"></span></div>
        </article>
      </div>

      <div class="control-grid">
        <article class="card pipeline-card">
          <div class="card-header">
            <div><h2 class="card-title">${DEMO_DATA.run.id} · ${DEMO_DATA.run.name}</h2><p class="card-subtitle">${DEMO_DATA.run.scope} · opened ${DEMO_DATA.run.started}</p></div>
            ${statusPill("review", "Awaiting review")}
          </div>
          <div class="pipeline" aria-label="Run workflow progress">
            ${pipelineStep("1", "Scope", "12 records", "done")}
            ${pipelineStep("2", "Preflight", "4 checks passed", "done")}
            ${pipelineStep("3", "Compare", "12 diffs ready", "done")}
            ${pipelineStep("4", "Human review", "1 action needed", "active")}
            ${pipelineStep("5", "Release", "Waiting", "")}
          </div>
        </article>

        <article class="card">
          <div class="card-header">
            <div><h2 class="card-title">Run queue</h2><p class="card-subtitle">Prioritized by dependency and review state</p></div>
            <button class="section-link" type="button" data-go-view="audit">View history</button>
          </div>
          <div class="run-list">
            ${DEMO_DATA.queue.map(runItem).join("")}
          </div>
        </article>

        <article class="card">
          <div class="card-header">
            <div><h2 class="card-title">Guardrail coverage</h2><p class="card-subtitle">Visible boundaries before any simulated release</p></div>
            <span class="status-pill status-verified">4 active</span>
          </div>
          <div class="guardrail-list">
            ${guardrail("✓", "Scope lock", "One location · price only", "Passed", "")}
            ${guardrail("≠", "Before/after check", "12 comparisons generated", "100%", "")}
            ${guardrail("?", "Unknown handling", "Never infer an absent value", "1 held", "amber")}
            ${guardrail("#", "Evidence capture", "Inputs, diffs, decisions", "Ready", "")}
          </div>
        </article>
      </div>
    </section>`;
}

function pipelineStep(number, label, meta, className) {
  const node = className === "done" ? "✓" : number;
  return `<div class="pipeline-step ${className}"><div class="pipeline-node">${node}</div><p class="pipeline-label">${label}</p><p class="pipeline-meta">${meta}</p></div>`;
}

function runItem(item) {
  return `<div class="run-item">
    <div class="run-glyph ${item.status === "running" ? "running" : ""}" aria-hidden="true">${item.glyph}</div>
    <div><p class="run-name">${item.name}</p><div class="run-meta">${item.meta.map(value => `<span>${value}</span>`).join("")}</div></div>
    <div class="run-side"><strong>${item.side}</strong><small>${item.detail}</small></div>
  </div>`;
}

function guardrail(symbol, name, copy, value, tone) {
  return `<div class="guardrail-row"><span class="guardrail-icon ${tone}" aria-hidden="true">${symbol}</span><div><div class="guardrail-name">${name}</div><div class="guardrail-copy">${copy}</div></div><span class="guardrail-value">${value}</span></div>`;
}

function visibleRecords() {
  return DEMO_DATA.records.filter(record => {
    const filterMatch = state.filter === "all" || record.status === state.filter || (state.filter === "attention" && ["held", "review"].includes(record.status));
    const term = state.search.trim().toLowerCase();
    const searchMatch = !term || `${record.id} ${record.name} ${record.location}`.toLowerCase().includes(term);
    return filterMatch && searchMatch;
  });
}

function renderDiff() {
  const records = visibleRecords();
  if (records.length && !records.some(record => record.id === state.selectedId)) {
    state.selectedId = records[0].id;
  }
  const selected = records.find(record => record.id === state.selectedId) || DEMO_DATA.records[0];
  return `
    <section class="page" aria-labelledby="page-title">
      ${pageHeading(
        "Review workspace",
        `<span id="page-title">Batch diff</span>`,
        "Compare proposed catalog values, isolate uncertainty, and inspect evidence before a human decision.",
        `<button class="button" type="button" data-action="export-manifest">Export diff JSON</button>
         <button class="button primary" type="button" data-go-view="approval">Open review case →</button>`
      )}
      <div class="diff-layout">
        <article class="card table-card">
          <div class="toolbar">
            <div class="segmented" aria-label="Filter records">
              ${segmentButton("all", "All 12")}
              ${segmentButton("verified", "Verified 9")}
              ${segmentButton("attention", "Attention 3")}
              ${segmentButton("held", "Held 2")}
            </div>
            <div class="toolbar-spacer"></div>
            <label class="search-field"><span class="visually-hidden">Search records</span><input id="record-search" type="search" value="${escapeHTML(state.search)}" placeholder="Search synthetic records"></label>
          </div>
          <table class="data-table">
            <thead><tr><th class="product-col" scope="col">Product</th><th scope="col">Location</th><th class="value-col" scope="col">Before</th><th class="value-col" scope="col">After</th><th scope="col">Delta</th><th class="status-col" scope="col">State</th></tr></thead>
            <tbody>
              ${records.length ? records.map(recordRow).join("") : `<tr><td colspan="6" class="empty-state">No synthetic records match this view.</td></tr>`}
            </tbody>
          </table>
          <div class="table-footer"><span>Showing ${records.length} demo records</span><span>Values are illustrative · no destination connected</span></div>
        </article>
        ${renderInspector(selected)}
      </div>
    </section>`;
}

function segmentButton(value, label) {
  return `<button class="segment" type="button" data-filter="${value}" aria-pressed="${state.filter === value}">${label}</button>`;
}

function recordRow(record) {
  const unknown = record.after === "Unknown";
  const deltaTone = record.delta.startsWith("−") ? "delta-down" : "delta-up";
  return `<tr data-record-id="${record.id}" tabindex="0" aria-label="Inspect ${record.name}" class="${record.id === state.selectedId ? "is-selected" : ""}">
    <td><div class="product-cell"><span class="product-avatar ${record.tone}" aria-hidden="true">${record.initials}</span><div><div class="product-name">${record.name}</div><div class="product-id">${record.id}</div></div></div></td>
    <td>${record.location}</td>
    <td><span class="old-value">${record.before}</span></td>
    <td><span class="${unknown ? "unknown-value" : "new-value"}">${record.after}</span></td>
    <td><span class="${record.delta === "—" ? "unknown-value" : deltaTone}">${record.delta}</span></td>
    <td>${statusPill(record.status, record.status === "review" ? "Review" : record.status)}</td>
  </tr>`;
}

function renderInspector(record) {
  const unknown = record.after === "Unknown";
  return `<aside class="card inspector" aria-label="Selected record details">
    <div class="inspector-accent"></div>
    <div class="inspector-head">
      <div class="inspector-label">Selected synthetic record</div>
      <h2 class="inspector-title">${record.name}</h2>
      <div class="inspector-id">${record.id} · ${record.location}</div>
    </div>
    <div class="inspector-section">
      <h3>Proposed field change</h3>
      <dl class="field-grid">
        <div class="field"><dt>Property</dt><dd>${record.property}</dd></div>
        <div class="field"><dt>Confidence</dt><dd>${record.confidence}</dd></div>
        <div class="field"><dt>Before</dt><dd>${record.before}</dd></div>
        <div class="field ${unknown ? "is-unknown" : ""}"><dt>After</dt><dd>${record.after}</dd></div>
      </dl>
    </div>
    <div class="inspector-section">
      <h3>Guardrail result</h3>
      <div class="reason-box"><span class="reason-symbol" aria-hidden="true">${record.status === "verified" ? "✓" : "!"}</span><div><strong>${record.status === "verified" ? "Ready for grouped release" : "Human attention required"}</strong><p>${record.reason}</p></div></div>
    </div>
    <div class="inspector-section">
      <h3>Local evidence</h3>
      <div class="record-list">
        <div class="record-row"><span>Source label</span><b>${record.source}</b></div>
        <div class="record-row"><span>Scope contract</span><b>Matched</b></div>
        <div class="record-row"><span>External writes</span><b>None</b></div>
      </div>
    </div>
    <div class="inspector-section inspector-actions">
      <button class="button primary" type="button" data-go-view="approval">Review this exception</button>
      <button class="button" type="button" data-action="show-evidence">Evidence</button>
      <button class="button" type="button" data-action="copy-record-id">Copy ID</button>
    </div>
  </aside>`;
}

function renderApproval() {
  const held = DEMO_DATA.records.find(record => record.id === "SYN-1088");
  const bannerStatus = state.decisionRecorded ? statusPill("verified", "Decision recorded") : statusPill("review", "Action required");
  return `
    <section class="page" aria-labelledby="page-title">
      ${pageHeading(
        "Exception workflow",
        `<span id="page-title">Human review</span>`,
        "Resolve uncertainty with visible evidence and an explicit, attributable decision.",
        `<button class="button" type="button" data-go-view="diff">← Return to diff</button>
         <button class="button" type="button" data-go-view="audit">View audit trail</button>`
      )}
      <div class="approval-layout">
        <div class="approval-stack">
          <div class="case-banner">
            <div class="case-symbol" aria-hidden="true">?</div>
            <div><h2>${state.decisionRecorded ? "Simulated decision captured" : "Unknown proposed value blocked automatically"}</h2><p>${state.decisionRecorded ? "The local demo event log now reflects the reviewer choice. No external action occurred." : "The source plan contains no proposed price for this record. The workflow holds it instead of inventing a value."}</p></div>
            ${bannerStatus}
          </div>

          <article class="card">
            <div class="card-header"><div><h2 class="card-title">Evidence comparison</h2><p class="card-subtitle">Case REV-017 · generated from synthetic fixture SYNTH-04</p></div><span class="status-pill status-unknown">Unknown detected</span></div>
            <div class="evidence-grid">
              <section class="evidence-column" aria-label="Current record">
                <div class="evidence-label">Current record <span>Captured 09:42:21</span></div>
                ${recordEvidence(held, "Current value", held.before, false)}
              </section>
              <section class="evidence-column" aria-label="Proposed record">
                <div class="evidence-label">Proposed record <span>Normalized locally</span></div>
                ${recordEvidence(held, "Proposed value", held.after, true)}
              </section>
            </div>
          </article>

          <article class="card">
            <div class="card-header"><div><h2 class="card-title">Decision context</h2><p class="card-subtitle">The demo surfaces bounded facts, not a recommendation disguised as certainty.</p></div></div>
            <div class="checklist">
              ${checkRow("✓", "Record identity", "ID, name, and location agree", "")}
              ${checkRow("✓", "Change scope", "Only the price property is in scope", "")}
              ${checkRow("!", "Required source value", "No proposed value is present", "warn")}
              ${checkRow("✓", "Default safeguard", "Record remains unchanged while held", "")}
            </div>
          </article>
        </div>

        <aside class="card decision-card" aria-label="Review decision">
          <div class="card-header"><div><h2 class="card-title">Record a demo decision</h2><p class="card-subtitle">Every path is explicit and reversible in this local session.</p></div></div>
          <div class="decision-body">
            ${decisionOption("hold", "Keep held", "Leave the current value unchanged and request source clarification.")}
            ${decisionOption("exclude", "Exclude from this batch", "Release other verified records while omitting this one.")}
            ${decisionOption("replace", "Enter a replacement value", "Requires a separately verified source value; unavailable in this fixture.")}
            <label for="review-note" class="visually-hidden">Review note</label>
            <textarea class="decision-note" id="review-note" placeholder="Optional reviewer note">Source value absent; keep current value and request clarification.</textarea>
          </div>
          <div class="decision-footer">
            <button class="button primary" type="button" data-action="record-decision">${state.decisionRecorded ? "Decision recorded locally ✓" : "Record simulated decision"}</button>
            <small>No destination is connected. This only updates the in-browser portfolio simulation.</small>
          </div>
        </aside>
      </div>
    </section>`;
}

function recordEvidence(record, valueLabel, value, isUnknown) {
  return `<div class="record-card"><div class="record-head"><span class="product-avatar ${record.tone}" aria-hidden="true">${record.initials}</span><div><strong>${record.name}</strong><small>${record.id}</small></div></div><div class="record-list"><div class="record-row"><span>Location</span><b>${record.location}</b></div><div class="record-row"><span>Property</span><b>${record.property}</b></div><div class="record-row"><span>${valueLabel}</span><b class="${isUnknown ? "unknown" : ""}">${value}</b></div><div class="record-row"><span>Source label</span><b>${record.source}</b></div></div></div>`;
}

function decisionOption(value, title, copy) {
  const selected = state.decision === value;
  return `<label class="decision-option ${selected ? "is-selected" : ""}"><input type="radio" name="decision" value="${value}" ${selected ? "checked" : ""} ${value === "replace" ? "disabled" : ""}><span><strong>${title}</strong><p>${copy}</p></span></label>`;
}

function checkRow(symbol, title, copy, tone) {
  return `<div class="check-row"><span class="check-mark ${tone}" aria-hidden="true">${symbol}</span><span><strong>${title}</strong> · ${copy}</span><small>${tone ? "Review" : "Passed"}</small></div>`;
}

function renderAudit() {
  return `
    <section class="page" aria-labelledby="page-title">
      ${pageHeading(
        "Traceability",
        `<span id="page-title">Audit trail</span>`,
        "A recruiter-readable record of boundaries, decisions, and evidence for one fully synthetic run.",
        `<button class="button" type="button" data-action="export-manifest">Export audit JSON</button>
         <button class="button primary" type="button" data-go-view="control">Return to control center</button>`
      )}
      <div class="audit-layout">
        <article class="card">
          <div class="card-header"><div><h2 class="card-title">${DEMO_DATA.run.id} · event log</h2><p class="card-subtitle">Times are fixed illustrative values for reproducible screenshots.</p></div>${statusPill("review", "Review pending")}</div>
          <div class="audit-summary">
            <div><span>Events captured</span><strong>6</strong></div>
            <div><span>Automated checks</span><strong>4 passed</strong></div>
            <div><span>External writes</span><strong>0</strong></div>
          </div>
          <div class="timeline">
            ${DEMO_DATA.events.map(eventRow).join("")}
          </div>
        </article>

        <aside>
          <article class="card">
            <div class="card-header"><div><h2 class="card-title">Evidence manifest</h2><p class="card-subtitle">Short demo digests make each artifact easy to identify.</p></div><span class="status-pill status-verified">Complete</span></div>
            <div class="manifest-list">
              ${manifestRow("Input fixture", "fixture-synth-04.json", "8d6c…42a1")}
              ${manifestRow("Scope contract", "scope-desert-harbor.json", "a927…0fe4")}
              ${manifestRow("Batch diff", "run-24871-diff.json", "c1b4…91dd")}
              ${manifestRow("Decision queue", "review-queue-017.json", "f04e…2c88")}
            </div>
          </article>
          <article class="card boundary-card">
            <h3>Demonstration boundary</h3>
            <ul><li>All records and digests are invented.</li><li>No vendor, employer, or customer system is represented.</li><li>No network request or external write exists in the app.</li><li>Approval updates only this browser session.</li></ul>
          </article>
        </aside>
      </div>
    </section>`;
}

function eventRow(event) {
  const recordLink = event.recordId
    ? `<button class="event-record" type="button" data-audit-record="${event.recordId}" aria-label="Inspect ${event.recordId} in batch diff">${event.recordId} →</button>`
    : "";
  return `<div class="event"><time class="event-time">${event.time}</time><span class="event-node ${event.tone === "warn" ? "warn" : ""}" aria-hidden="true">${event.symbol}</span><div class="event-copy"><strong>${event.title}</strong><p>${event.copy}</p></div><div class="event-meta"><span class="event-actor">${event.actor}</span>${recordLink}</div></div>`;
}

function manifestRow(title, file, digest) {
  return `<div class="manifest-row"><div><strong>${title}</strong><span class="manifest-status">Verified</span></div><code>${file} · sha256:${digest}</code></div>`;
}

function render() {
  const renderers = { control: renderControl, diff: renderDiff, approval: renderApproval, audit: renderAudit };
  main.innerHTML = renderers[state.view]();
  document.title = `${VIEW_TITLES[state.view]} · Catalog Lifecycle Lab`;
  document.querySelectorAll(".nav-item").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.view === state.view));
  });
  requestAnimationFrame(() => main.scrollTo({ top: 0, behavior: "auto" }));
}

function navigate(view, updateHistory = true) {
  if (!Object.hasOwn(VIEW_TITLES, view)) return;
  state.view = view;
  const url = new URL(window.location.href);
  url.searchParams.set("view", view);
  if (updateHistory) window.history.pushState({ view }, "", url);
  render();
  main.focus({ preventScroll: true });
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2400);
}

function exportManifest() {
  const payload = {
    demo: "Catalog Lifecycle Lab",
    synthetic: true,
    externalConnections: 0,
    run: DEMO_DATA.run,
    recordSummary: { total: 12, verified: 9, review: 1, held: 2 },
    exportedView: state.view,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `catalog-lifecycle-lab-${state.view}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  showToast("Synthetic demo snapshot prepared locally.");
}

document.querySelector(".view-nav").addEventListener("click", event => {
  const button = event.target.closest("[data-view]");
  if (button) navigate(button.dataset.view);
});

main.addEventListener("click", event => {
  const auditRecord = event.target.closest("[data-audit-record]");
  if (auditRecord) {
    state.selectedId = auditRecord.dataset.auditRecord;
    state.filter = "all";
    navigate("diff");
    return;
  }
  const goButton = event.target.closest("[data-go-view]");
  if (goButton) {
    navigate(goButton.dataset.goView);
    return;
  }
  const filterButton = event.target.closest("[data-filter]");
  if (filterButton) {
    state.filter = filterButton.dataset.filter;
    render();
    return;
  }
  const row = event.target.closest("[data-record-id]");
  if (row) {
    state.selectedId = row.dataset.recordId;
    render();
    return;
  }
  const actionButton = event.target.closest("[data-action]");
  if (!actionButton) return;
  const action = actionButton.dataset.action;
  if (action === "export-manifest") exportManifest();
  if (action === "show-evidence") showToast("Evidence is represented by the synthetic source label and scope contract.");
  if (action === "copy-record-id") showToast(`${state.selectedId} ready to reference in this demo.`);
  if (action === "record-decision") {
    state.decisionRecorded = true;
    render();
    showToast("Simulated decision recorded locally; no external action occurred.");
  }
});

main.addEventListener("change", event => {
  if (event.target.matches("input[name='decision']")) {
    state.decision = event.target.value;
    state.decisionRecorded = false;
    render();
  }
});

main.addEventListener("input", event => {
  if (event.target.id !== "record-search") return;
  state.search = event.target.value;
  const cursor = event.target.selectionStart;
  render();
  const replacement = document.querySelector("#record-search");
  replacement.focus();
  replacement.setSelectionRange(cursor, cursor);
});

main.addEventListener("keydown", event => {
  const row = event.target.closest("[data-record-id]");
  if (row && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    state.selectedId = row.dataset.recordId;
    render();
  }
});

document.addEventListener("keydown", event => {
  if (event.altKey || event.ctrlKey || event.metaKey || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName)) return;
  const mapping = { "1": "control", "2": "diff", "3": "approval", "4": "audit" };
  if (mapping[event.key]) navigate(mapping[event.key]);
});

document.querySelector("#copy-link-button").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(window.location.href);
    showToast("Screen link copied.");
  } catch (_error) {
    showToast("Screen URL is available in the browser address bar.");
  }
});

window.addEventListener("popstate", () => {
  state.view = readView();
  render();
});

render();
