"use strict";

const VIEW_ORDER = ["overview", "discovery", "readiness", "exceptions", "enablement", "acceptance"];
const SCENARIOS = ["baseline", "recovery", "review-ready"];

const FIXTURE = {
  program: {
    id: "SYN-LAUNCH-024",
    customer: "Northstar Grid Services",
    program: "Meter exchange visibility rollout",
    target: "Sep 18",
    firstValue: "A customer operator validates one synthetic exception from intake through reviewed resolution.",
    scope: "One invented service territory, 2,400 simulated service points, and one operator cohort.",
    excluded: "Production credentials, live utility data, billing, hardware control, and automated go-live.",
  },
  phases: [
    { id: "PH-01", label: "Discover", date: "Aug 24", detail: "Outcome + owners" },
    { id: "PH-02", label: "Configure", date: "Sep 02", detail: "Mapping + access" },
    { id: "PH-03", label: "Validate", date: "Sep 09", detail: "UAT + exceptions" },
    { id: "PH-04", label: "Enable", date: "Sep 15", detail: "Practice + handoff" },
    { id: "PH-05", label: "Accept", date: "Sep 18", detail: "Human decision" },
  ],
  decisions: [
    {
      id: "DS-01",
      title: "Define the first-value event",
      detail: "One synthetic exception is received, triaged, corrected, and reviewed by the customer operator.",
      owner: "Customer program owner",
    },
    {
      id: "DS-02",
      title: "Freeze the source roster",
      detail: "Use the invented 2,400-row territory fixture and reject undeclared columns.",
      owner: "Customer data owner",
    },
    {
      id: "DS-03",
      title: "Set exception severity rules",
      detail: "Identity conflicts stop the rehearsal; display-only defects enter the review queue.",
      owner: "Implementation lead",
    },
    {
      id: "DS-04",
      title: "Name the receiving owner",
      detail: "Support operations receives the runbook, known exceptions, and first-week cadence.",
      owner: "Support operations owner",
    },
  ],
  readiness: [
    {
      id: "RD-01",
      workstream: "Access + roles",
      owner: "Mira Chen · customer sponsor",
      initials: "MC",
      evidence: "Invented role matrix v3",
      dependency: "None",
      exit: "Named operators can enter only their synthetic workspace.",
      next: "Capture sponsor confirmation.",
    },
    {
      id: "RD-02",
      workstream: "Source handshake",
      owner: "Alex Rios · data owner",
      initials: "AR",
      evidence: "Synthetic roster checksum",
      dependency: "DS-02 roster freeze",
      exit: "Declared fixture lands with row count and schema checks intact.",
      next: "Resolve the duplicate service-point key.",
    },
    {
      id: "RD-03",
      workstream: "Field mapping",
      owner: "Implementation lead",
      initials: "IL",
      evidence: "Invented mapping workbook v5",
      dependency: "Source handshake",
      exit: "Required fields map; ambiguous values remain in the exception queue.",
      next: "Review exception behavior with the customer data owner.",
    },
    {
      id: "RD-04",
      workstream: "Configuration",
      owner: "Implementation lead",
      initials: "IL",
      evidence: "Synthetic setup checklist",
      dependency: "Field mapping",
      exit: "The demo workspace reflects approved program decisions.",
      next: "Attach review notes after configuration rehearsal.",
    },
    {
      id: "RD-05",
      workstream: "Integration rehearsal",
      owner: "Devon Hale · technical owner",
      initials: "DH",
      evidence: "Invented handshake log",
      dependency: "Access + configuration",
      exit: "A synthetic payload completes the declared non-production path.",
      next: "Re-run UAT-04 after EX-17 review.",
    },
    {
      id: "RD-06",
      workstream: "Customer validation",
      owner: "Jamie Park · operator lead",
      initials: "JP",
      evidence: "Synthetic UAT record",
      dependency: "Integration rehearsal",
      exit: "Named operators record expected results for every UAT case.",
      next: "Finish the exception recovery case.",
    },
    {
      id: "RD-07",
      workstream: "Enablement",
      owner: "Priya Shah · training owner",
      initials: "PS",
      evidence: "Invented practice roster",
      dependency: "Customer validation",
      exit: "Operators complete guided practice and know the escalation path.",
      next: "Complete exception ownership practice.",
    },
    {
      id: "RD-08",
      workstream: "Acceptance packet",
      owner: "Mira Chen · customer sponsor",
      initials: "MC",
      evidence: "Synthetic decision packet",
      dependency: "All readiness gates",
      exit: "Decision inputs are complete and the sponsor can decide; no acceptance is inferred.",
      next: "Run gates, then request the separate human acceptance decision.",
    },
  ],
  exceptions: [
    {
      id: "EX-17",
      title: "Duplicate service-point key",
      severity: "High",
      owner: "Alex Rios · data owner",
      impact: "12 invented records stop before the rehearsal; no data is silently merged.",
      linked: "RD-02 · UAT-04",
      expected: "Each declared service point has one stable synthetic key.",
      observed: "Two source rows reuse a key while carrying different territory values.",
      steps: [
        "Load the invented Territory West fixture.",
        "Run the declared uniqueness check on service_point_key.",
        "Open the stopped-record queue and compare the two territory values.",
      ],
      review: "Customer data owner confirms the corrected fixture and the operator reruns UAT-04.",
    },
    {
      id: "EX-22",
      title: "Status timestamp offset",
      severity: "Medium",
      owner: "Devon Hale · technical owner",
      impact: "The synthetic status card displays one hour late; source values remain unchanged.",
      linked: "RD-05 · UAT-03",
      expected: "The rehearsal renders the declared Mountain time value.",
      observed: "The display fixture uses a UTC label for a local timestamp.",
      steps: ["Open the invented status event.", "Compare the declared zone and rendered label.", "Capture the mismatch in the review queue."],
      review: "Implementation lead validates the corrected label in the non-production fixture.",
    },
    {
      id: "EX-29",
      title: "Escalation owner not acknowledged",
      severity: "Low",
      owner: "Sam Lee · support owner",
      impact: "First-week escalation would lack an accepted receiving owner.",
      linked: "RD-07 · HO-03",
      expected: "Support operations acknowledges the runbook and first-week cadence.",
      observed: "The handoff packet is present but its receiving-owner acknowledgment is absent.",
      steps: ["Open the invented handoff packet.", "Review the first-week cadence.", "Record the receiving owner's explicit acknowledgment."],
      review: "Support owner acknowledgment appears in the demo audit trail.",
    },
  ],
  uat: [
    { id: "UAT-01", title: "Operator access boundary", owner: "Jamie Park", expected: "Operator reaches only the invented workspace." },
    { id: "UAT-02", title: "Declared roster intake", owner: "Alex Rios", expected: "2,400 fixture rows reconcile." },
    { id: "UAT-03", title: "Status event display", owner: "Devon Hale", expected: "Declared timestamp label renders." },
    { id: "UAT-04", title: "Exception recovery", owner: "Jamie Park", expected: "Duplicate key stops, is corrected, and reruns." },
  ],
  training: [
    { id: "TRN-01", title: "Operator walkthrough", audience: "6 synthetic operators", signal: "6 / 6 attended", detail: "Navigate the queue and explain each state." },
    { id: "TRN-02", title: "Guided first-value practice", audience: "6 synthetic operators", signal: "5 / 6 passed", detail: "Resolve the safe practice record without skipping review." },
    { id: "TRN-03", title: "Exception ownership practice", audience: "2 synthetic owner roles", signal: "1 / 2 acknowledged", detail: "Reproduce, escalate, review, and communicate a blocker." },
  ],
  handoffs: [
    { id: "HO-01", title: "Program ownership", owner: "Mira Chen · customer sponsor", artifact: "Invented outcome + milestone brief", initials: "MC" },
    { id: "HO-02", title: "Operational ownership", owner: "Jamie Park · operator lead", artifact: "Invented operator checklist", initials: "JP" },
    { id: "HO-03", title: "Support ownership", owner: "Sam Lee · support owner", artifact: "Invented runbook + escalation map", initials: "SL" },
    { id: "HO-04", title: "Delivery closeout", owner: "Implementation lead", artifact: "Invented risks + acceptance packet", initials: "IL" },
  ],
};

const SCENARIO_STATE = {
  baseline: {
    decisions: { "DS-01": true, "DS-02": false, "DS-03": true, "DS-04": false },
    readiness: { "RD-01": "ready", "RD-02": "working", "RD-03": "working", "RD-04": "review_ready", "RD-05": "planned", "RD-06": "planned", "RD-07": "scheduled", "RD-08": "planned" },
    exceptions: { "EX-17": "open", "EX-22": "review_ready", "EX-29": "open" },
    uat: { "UAT-01": "pass", "UAT-02": "blocked", "UAT-03": "pass", "UAT-04": "blocked" },
    training: { "TRN-01": "complete", "TRN-02": "scheduled", "TRN-03": "scheduled" },
    handoffs: { "HO-01": true, "HO-02": false, "HO-03": false, "HO-04": false },
    statusUpdateSent: false,
  },
  recovery: {
    decisions: { "DS-01": true, "DS-02": true, "DS-03": true, "DS-04": true },
    readiness: { "RD-01": "ready", "RD-02": "working", "RD-03": "review_ready", "RD-04": "ready", "RD-05": "working", "RD-06": "working", "RD-07": "scheduled", "RD-08": "planned" },
    exceptions: { "EX-17": "working", "EX-22": "accepted", "EX-29": "review_ready" },
    uat: { "UAT-01": "pass", "UAT-02": "pass", "UAT-03": "pass", "UAT-04": "blocked" },
    training: { "TRN-01": "complete", "TRN-02": "complete", "TRN-03": "scheduled" },
    handoffs: { "HO-01": true, "HO-02": true, "HO-03": false, "HO-04": false },
    statusUpdateSent: true,
  },
  "review-ready": {
    decisions: { "DS-01": true, "DS-02": true, "DS-03": true, "DS-04": true },
    readiness: { "RD-01": "ready", "RD-02": "ready", "RD-03": "ready", "RD-04": "ready", "RD-05": "ready", "RD-06": "ready", "RD-07": "ready", "RD-08": "ready" },
    exceptions: { "EX-17": "review_ready", "EX-22": "accepted", "EX-29": "accepted" },
    uat: { "UAT-01": "pass", "UAT-02": "pass", "UAT-03": "pass", "UAT-04": "pass" },
    training: { "TRN-01": "complete", "TRN-02": "complete", "TRN-03": "complete" },
    handoffs: { "HO-01": true, "HO-02": true, "HO-03": false, "HO-04": true },
    statusUpdateSent: true,
  },
};

const INITIAL_AUDIT = [
  { id: "SIM-004", actor: "Implementation lead", action: "Customer status note drafted", detail: "Invented milestone, owner, risk, and next-decision summary prepared." },
  { id: "SIM-003", actor: "Customer operator", action: "UAT-03 result recorded", detail: "Synthetic status display matched the expected non-production fixture." },
  { id: "SIM-002", actor: "Technical owner", action: "Integration rehearsal evidence attached", detail: "Invented handshake record linked to RD-05." },
  { id: "SIM-001", actor: "Implementation lead", action: "Launch workspace created", detail: "Synthetic scope, owners, target, and first-value definition recorded." },
];

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function initialScenario() {
  const value = new URLSearchParams(window.location.search).get("scenario");
  return SCENARIOS.includes(value) ? value : "baseline";
}

function initialView() {
  const value = new URLSearchParams(window.location.search).get("view");
  return VIEW_ORDER.includes(value) ? value : "overview";
}

function buildState(scenario) {
  const seed = clone(SCENARIO_STATE[scenario]);
  return {
    scenario,
    view: initialView(),
    decisions: seed.decisions,
    readinessStatuses: seed.readiness,
    exceptionStatuses: seed.exceptions,
    uatStatuses: seed.uat,
    trainingStatuses: seed.training,
    handoffAcks: seed.handoffs,
    statusUpdateSent: seed.statusUpdateSent,
    selectedReadiness: "RD-02",
    selectedException: "EX-17",
    readinessFilter: "all",
    discoveryNote: "Confirm the corrected fixture owner before the next customer status update.",
    checksRun: false,
    goLiveAccepted: false,
    audit: clone(INITIAL_AUDIT),
    eventCounter: 4,
  };
}

let state = buildState(initialScenario());
let toastTimer = 0;

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function label(value) {
  const labels = {
    ready: "Ready",
    working: "In progress",
    review_ready: "Review-ready",
    planned: "Planned",
    scheduled: "Scheduled",
    open: "Open",
    accepted: "Accepted",
    pass: "Pass",
    blocked: "Blocked",
    complete: "Complete",
    pending: "Pending",
    fail: "Needs action",
  };
  return labels[value] || value;
}

function pill(value) {
  return `<span class="pill pill-${escapeHTML(value)}">${escapeHTML(label(value))}</span>`;
}

function pageHead(eyebrow, title, description, actions = "") {
  return `
    <div class="page-head">
      <div>
        <span class="eyebrow">${escapeHTML(eyebrow)}</span>
        <h1>${escapeHTML(title)}</h1>
        <p>${escapeHTML(description)}</p>
      </div>
      <div class="head-actions"><span class="tag tag-invented">Invented fixture</span>${actions}</div>
    </div>`;
}

function addAudit(actor, action, detail) {
  state.eventCounter += 1;
  state.audit.unshift({
    id: `SIM-${String(state.eventCounter).padStart(3, "0")}`,
    actor,
    action,
    detail,
  });
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 2200);
}

function updateLocation() {
  const url = new URL(window.location.href);
  url.searchParams.set("view", state.view);
  url.searchParams.set("scenario", state.scenario);
  window.history.replaceState({}, "", url);
}

function setView(view) {
  if (!VIEW_ORDER.includes(view)) return;
  state.view = view;
  updateLocation();
  render();
  document.querySelector("#app").focus({ preventScroll: true });
}

function revealActiveNavigation() {
  const nav = document.querySelector(".primary-nav");
  const active = nav?.querySelector("[data-view].active");
  if (!nav || !active || !window.matchMedia("(max-width: 1050px)").matches) return;
  const centered = active.offsetLeft - ((nav.clientWidth - active.offsetWidth) / 2);
  nav.scrollLeft = Math.max(0, centered);
}

function scenarioProgress() {
  const checks = acceptanceChecks().slice(0, -1);
  return Math.round((checks.filter((check) => check.pass).length / checks.length) * 100);
}

function renderOverview() {
  const ready = Object.values(state.readinessStatuses).filter((value) => value === "ready").length;
  const unresolved = Object.values(state.exceptionStatuses).filter((value) => value !== "accepted").length;
  const trained = Object.values(state.trainingStatuses).filter((value) => value === "complete").length;
  const handoffs = Object.values(state.handoffAcks).filter(Boolean).length;
  const progress = scenarioProgress();
  const phaseIndex = state.scenario === "baseline" ? 1 : state.scenario === "recovery" ? 2 : 3;

  return `
    ${pageHead("Implementation command center", "A launch story everyone can act on", "Synthetic milestone health, risk, ownership, and first-value criteria in one decision surface.", '<button class="button-secondary" type="button" data-send-update>Record status update</button>')}
    <section class="metric-strip" aria-label="Synthetic launch metrics">
      <div class="metric" style="--metric-color: var(--teal)"><span>Readiness</span><strong>${progress}%</strong><small>${ready} of ${FIXTURE.readiness.length} workstreams ready</small></div>
      <div class="metric" style="--metric-color: var(--red)"><span>Exceptions</span><strong>${unresolved}</strong><small>${unresolved === 1 ? "one item awaits review" : "items need named owners"}</small></div>
      <div class="metric" style="--metric-color: var(--amber)"><span>Enablement</span><strong>${trained}/${FIXTURE.training.length}</strong><small>practice modules complete</small></div>
      <div class="metric" style="--metric-color: var(--blue)"><span>Handoffs</span><strong>${handoffs}/${FIXTURE.handoffs.length}</strong><small>owner acknowledgments recorded</small></div>
    </section>
    <div class="layout-overview">
      <div class="stack">
        <section class="card">
          <div class="card-head"><div><h2>Launch arc</h2><p>Contract-to-first-value sequence represented as an invented program fixture</p></div><span class="tag">${escapeHTML(FIXTURE.program.id)}</span></div>
          <div class="phase-track">
            ${FIXTURE.phases.map((phase, index) => `
              <div class="phase ${index < phaseIndex ? "complete" : index === phaseIndex ? "current" : ""}">
                <span class="phase-number">${phase.id}</span>
                <strong>${escapeHTML(phase.label)}</strong>
                <small>${escapeHTML(phase.date)} · ${escapeHTML(phase.detail)}</small>
              </div>`).join("")}
          </div>
        </section>
        <div class="grid-2">
          <section class="card">
            <div class="card-head"><div><h2>Next customer moments</h2><p>Owner, decision, and intended outcome</p></div></div>
            <div class="card-body milestone-list">
              <div class="milestone"><span class="milestone-date">09<br>SEP</span><div><strong>Exception recovery review</strong><small>Alex Rios + operator lead · decide whether EX-17 is accepted</small></div>${pill(state.exceptionStatuses["EX-17"])}</div>
              <div class="milestone"><span class="milestone-date">15<br>SEP</span><div><strong>Ownership rehearsal</strong><small>Support owner · practice the first-week escalation path</small></div>${pill(state.trainingStatuses["TRN-03"])}</div>
              <div class="milestone"><span class="milestone-date">18<br>SEP</span><div><strong>Go-live acceptance</strong><small>Customer sponsor · explicit synthetic decision after gates</small></div>${pill(state.goLiveAccepted ? "accepted" : "pending")}</div>
            </div>
          </section>
          <section class="card">
            <div class="card-head"><div><h2>Readiness focus</h2><p>Workstreams that deserve delivery attention</p></div><button class="button-quiet" type="button" data-view-jump="readiness">Open matrix →</button></div>
            <div class="card-body milestone-list">
              ${FIXTURE.readiness.filter((item) => state.readinessStatuses[item.id] !== "ready").slice(0, 3).map((item) => `
                <div class="milestone"><span class="owner-badge">${item.initials}</span><div><strong>${escapeHTML(item.workstream)}</strong><small>${escapeHTML(item.next)}</small></div>${pill(state.readinessStatuses[item.id])}</div>`).join("") || '<div class="empty-state"><strong>All workstreams are ready</strong><span>Keep the human acceptance decision separate.</span></div>'}
            </div>
          </section>
        </div>
      </div>
      <aside class="stack">
        <section class="card signal-card">
          <div class="card-pad">
            <span class="eyebrow">First-value definition</span>
            <h2>${escapeHTML(FIXTURE.program.firstValue)}</h2>
            <p>Scope: ${escapeHTML(FIXTURE.program.scope)}</p>
            <div class="signal-definition"><div><span>Target window</span><strong>${escapeHTML(FIXTURE.program.target)}</strong></div><span>Human reviewed<br>synthetic event</span></div>
          </div>
        </section>
        <section class="card card-pad">
          <div class="risk-callout">
            <span class="risk-icon" aria-hidden="true">!</span>
            <div><strong>${unresolved ? "A visible blocker stays visible" : "No unresolved exception in this fixture"}</strong><p>${unresolved ? "EX-17 cannot become accepted through workflow automation; a named reviewer must acknowledge its evidence." : "Go-live still requires a separate human acceptance click."}</p></div>
          </div>
          <div style="margin-top: 15px">
            <span class="field-label">Latest customer status</span>
            <div class="progress" aria-label="Synthetic implementation progress"><i style="--progress: ${progress}%"></i></div>
            <p style="margin: 8px 0 0; color: var(--muted); font-size: 10px">${state.statusUpdateSent ? "Update recorded: milestone, risk, owner, and next decision are current." : "Draft ready; no update has been recorded in this session."}</p>
          </div>
        </section>
      </aside>
    </div>`;
}

function renderDiscovery() {
  const confirmed = Object.values(state.decisions).filter(Boolean).length;
  return `
    ${pageHead("Discovery + scope", "Turn kickoff conversation into owned decisions", "Every object below is invented for the demo; decisions persist only in this page session.", `<span class="tag">${confirmed}/${FIXTURE.decisions.length} confirmed</span>`)}
    <div class="layout-split">
      <section class="card">
        <div class="card-head"><div><h2>Decision register</h2><p>Outcome, fixture boundary, severity model, and receiving owner</p></div><span class="tag">Customer-reviewable</span></div>
        <div class="card-body decision-list">
          ${FIXTURE.decisions.map((decision, index) => `
            <div class="decision ${state.decisions[decision.id] ? "confirmed" : ""}">
              <span class="decision-index">0${index + 1}</span>
              <div><strong>${escapeHTML(decision.title)}</strong><p>${escapeHTML(decision.detail)} · Owner: ${escapeHTML(decision.owner)}</p></div>
              <button class="${state.decisions[decision.id] ? "button-secondary" : "button"}" type="button" data-toggle-decision="${decision.id}">${state.decisions[decision.id] ? "Confirmed" : "Confirm"}</button>
            </div>`).join("")}
        </div>
      </section>
      <aside class="stack">
        <section class="card">
          <div class="card-head"><div><h2>Program frame</h2><p>Invented implementation contract</p></div></div>
          <div class="card-body">
            <div class="scope-box">
              <div class="scope-cell"><span>Customer outcome</span><strong>Review one exception end to end</strong></div>
              <div class="scope-cell"><span>Target</span><strong>${escapeHTML(FIXTURE.program.target)}</strong></div>
              <div class="scope-cell"><span>In scope</span><strong>One synthetic territory fixture</strong></div>
              <div class="scope-cell"><span>Out of scope</span><strong>Production systems + credentials</strong></div>
            </div>
            <p style="margin: 12px 0 0; color: var(--muted); font-size: 10px">${escapeHTML(FIXTURE.program.excluded)}</p>
          </div>
        </section>
        <section class="card">
          <div class="card-head"><div><h2>Delivery note</h2><p>Local, transient, and escaped before rendering</p></div></div>
          <div class="card-body">
            <label class="field-label" for="discovery-note">Next customer decision</label>
            <textarea class="note-field" id="discovery-note" data-discovery-note maxlength="280">${escapeHTML(state.discoveryNote)}</textarea>
            <div class="button-row" style="margin-top: 9px"><button class="button" type="button" data-save-note>Record note in demo audit</button><span style="color: var(--muted); font-size: 9px">Nothing is transmitted or persisted.</span></div>
          </div>
        </section>
      </aside>
    </div>`;
}

function readinessMatches(item) {
  const status = state.readinessStatuses[item.id];
  if (state.readinessFilter === "all") return true;
  if (state.readinessFilter === "attention") return status !== "ready";
  if (state.readinessFilter === "customer") return item.owner.includes("customer") || item.owner.includes("Mira") || item.owner.includes("Alex") || item.owner.includes("Jamie");
  return true;
}

function renderReadiness() {
  const items = FIXTURE.readiness.filter(readinessMatches);
  const selected = FIXTURE.readiness.find((item) => item.id === state.selectedReadiness) || items[0] || FIXTURE.readiness[0];
  const status = state.readinessStatuses[selected.id];
  const action = status === "planned" || status === "scheduled" ? "Start simulated work" : status === "working" ? "Mark review-ready" : status === "review_ready" ? "Reviewer mark ready" : "Ready";
  return `
    ${pageHead("Integration readiness", "Expose dependencies before they become launch surprises", "Select a workstream to inspect its evidence, owner, exit criteria, and next decision.", '<button class="button-secondary" type="button" data-view-jump="exceptions">Open UAT + exceptions →</button>')}
    <div class="layout-split">
      <section class="card">
        <div class="card-head"><div><h2>Readiness matrix</h2><p>Invented workstreams mapped from signed scope to explicit acceptance</p></div><div class="filter-row"><button class="filter-button ${state.readinessFilter === "all" ? "active" : ""}" type="button" data-readiness-filter="all">All</button><button class="filter-button ${state.readinessFilter === "attention" ? "active" : ""}" type="button" data-readiness-filter="attention">Needs attention</button><button class="filter-button ${state.readinessFilter === "customer" ? "active" : ""}" type="button" data-readiness-filter="customer">Customer-owned</button></div></div>
        <div style="overflow-x: auto">
          <table class="matrix">
            <thead><tr><th>Workstream</th><th>Named owner</th><th>Evidence</th><th>Dependency</th><th>Status</th></tr></thead>
            <tbody>
              ${items.map((item) => `
                <tr class="${selected.id === item.id ? "selected" : ""}" data-readiness-id="${item.id}" tabindex="0">
                  <td><span class="row-title">${escapeHTML(item.workstream)}</span><span class="row-id">${item.id}</span></td>
                  <td><span class="owner"><span class="owner-badge">${item.initials}</span>${escapeHTML(item.owner)}</span></td>
                  <td>${escapeHTML(item.evidence)}</td>
                  <td>${escapeHTML(item.dependency)}</td>
                  <td>${pill(state.readinessStatuses[item.id])}</td>
                </tr>`).join("")}
            </tbody>
          </table>
          ${items.length ? "" : '<div class="empty-state"><strong>No workstreams match this filter.</strong><span>Choose another readiness slice.</span></div>'}
        </div>
      </section>
      <aside class="card detail-card">
        <div class="card-head"><div><span class="eyebrow">${selected.id} · selected workstream</span><h2>${escapeHTML(selected.workstream)}</h2></div>${pill(status)}</div>
        <div class="card-body">
          <p>Transitions are deliberate: simulated work can reach review-ready, but only the reviewer action can mark the workstream ready.</p>
          <div class="detail-grid">
            <div class="detail-field"><span>Exit criterion</span><p>${escapeHTML(selected.exit)}</p></div>
            <div class="detail-field"><span>Evidence locator</span><strong>${escapeHTML(selected.evidence)}</strong></div>
            <div class="detail-field"><span>Next delivery move</span><p>${escapeHTML(selected.next)}</p></div>
          </div>
          <button class="button" type="button" data-advance-readiness="${selected.id}" ${status === "ready" ? "disabled" : ""}>${escapeHTML(action)}</button>
        </div>
      </aside>
    </div>`;
}

function renderExceptions() {
  const selected = FIXTURE.exceptions.find((item) => item.id === state.selectedException) || FIXTURE.exceptions[0];
  const status = state.exceptionStatuses[selected.id];
  const action = status === "open" ? "Start investigation" : status === "working" ? "Mark review-ready" : status === "review_ready" ? "Reviewer accept evidence" : "Accepted";
  return `
    ${pageHead("UAT + exceptions", "Keep reproduction, impact, and review ownership together", "Exceptions never disappear into a green rollup; review-ready is not the same as accepted.", '<button class="button-secondary" type="button" data-view-jump="enablement">Open enablement →</button>')}
    <div class="layout-split">
      <div class="stack">
        <section class="card">
          <div class="card-head"><div><h2>UAT evidence board</h2><p>Expected results and operator-recorded outcomes for the invented rehearsal</p></div><span class="tag">4 cases</span></div>
          <div class="card-body uat-board">
            ${FIXTURE.uat.map((item) => `
              <div class="uat-case"><span class="row-id">${item.id}${item.id === "UAT-04" ? " · LINKED EX-17" : ""}</span><strong>${escapeHTML(item.title)}</strong>${pill(state.uatStatuses[item.id])}<small>${escapeHTML(item.owner)} · ${escapeHTML(item.expected)}</small></div>`).join("")}
          </div>
        </section>
        <section class="card">
          <div class="card-head"><div><h2>Exception queue</h2><p>Impact and named owner remain visible through resolution</p></div></div>
          <div class="card-body exception-list">
            ${FIXTURE.exceptions.map((item) => `
              <button class="exception-row ${selected.id === item.id ? "selected" : ""}" type="button" data-exception-id="${item.id}">
                <div><span class="row-id">${item.id} · ${escapeHTML(item.severity)} severity</span><strong>${escapeHTML(item.title)}</strong><small>${escapeHTML(item.impact)}</small></div>${pill(state.exceptionStatuses[item.id])}
              </button>`).join("")}
          </div>
        </section>
      </div>
      <aside class="card detail-card">
        <div class="card-head"><div><span class="eyebrow">${selected.id} · ${escapeHTML(selected.severity)} severity</span><h2>${escapeHTML(selected.title)}</h2></div>${pill(status)}</div>
        <div class="card-body">
          <div class="detail-grid">
            <div class="detail-field"><span>Observed</span><p>${escapeHTML(selected.observed)}</p></div>
            <div class="detail-field"><span>Expected</span><p>${escapeHTML(selected.expected)}</p></div>
            <div class="detail-field"><span>Owner + linked gates</span><strong>${escapeHTML(selected.owner)}</strong><p>${escapeHTML(selected.linked)}</p></div>
          </div>
          <span class="field-label">Reproduction steps</span>
          <ol class="repro-steps">${selected.steps.map((step) => `<li>${escapeHTML(step)}</li>`).join("")}</ol>
          <div class="risk-callout" style="margin: 14px 0"><span class="risk-icon" aria-hidden="true">✓</span><div><strong>Review condition</strong><p>${escapeHTML(selected.review)}</p></div></div>
          <button class="button" type="button" data-advance-exception="${selected.id}" ${status === "accepted" ? "disabled" : ""}>${escapeHTML(action)}</button>
        </div>
      </aside>
    </div>`;
}

function renderEnablement() {
  const complete = Object.values(state.trainingStatuses).filter((value) => value === "complete").length;
  const acknowledgments = Object.values(state.handoffAcks).filter(Boolean).length;
  return `
    ${pageHead("Training + adoption", "Make the receiving team capable, not merely informed", "Practice signals, named owners, and handoff artifacts use entirely invented participants and records.", `<span class="tag">${complete}/${FIXTURE.training.length} practice modules</span>`)}
    <div class="grid-2">
      <section class="card">
        <div class="card-head"><div><h2>Enablement plan</h2><p>Attendance is context; demonstrated practice is the stronger signal</p></div><span class="tag">Synthetic cohort</span></div>
        <div class="card-body training-list">
          ${FIXTURE.training.map((item) => {
            const status = state.trainingStatuses[item.id];
            return `<div class="training-row"><span class="training-score ${status === "complete" ? "" : "pending"}">${status === "complete" ? "✓" : "…"}</span><div><span class="row-id">${item.id} · ${escapeHTML(item.audience)}</span><strong>${escapeHTML(item.title)}</strong><small>${escapeHTML(item.detail)} · Current signal: ${escapeHTML(item.signal)}</small></div><button class="${status === "complete" ? "button-secondary" : "button"}" type="button" data-complete-training="${item.id}" ${status === "complete" ? "disabled" : ""}>${status === "complete" ? "Complete" : "Record practice"}</button></div>`;
          }).join("")}
        </div>
      </section>
      <section class="card">
        <div class="card-head"><div><h2>Customer-owner handoffs</h2><p>Receiving owners acknowledge the artifact and operating responsibility</p></div><span class="tag">${acknowledgments}/${FIXTURE.handoffs.length} acknowledged</span></div>
        <div class="card-body owner-list">
          ${FIXTURE.handoffs.map((item) => `
            <div class="owner-row"><span class="owner-badge">${item.initials}</span><div><span class="row-id">${item.id}</span><strong>${escapeHTML(item.title)}</strong><small>${escapeHTML(item.owner)} · ${escapeHTML(item.artifact)}</small></div><button class="${state.handoffAcks[item.id] ? "button-secondary" : "button"}" type="button" data-ack-handoff="${item.id}" ${state.handoffAcks[item.id] ? "disabled" : ""}>${state.handoffAcks[item.id] ? "Acknowledged" : "Acknowledge"}</button></div>`).join("")}
        </div>
      </section>
    </div>
    <div class="grid-3" style="margin-top: 14px">
      <section class="card card-pad"><span class="eyebrow">Adoption signal 01</span><h2 style="margin: 6px 0; font-size: 17px">6 / 6 attended</h2><p style="margin: 0; color: var(--muted); font-size: 10px">Invented walkthrough attendance; presence alone does not establish readiness.</p></section>
      <section class="card card-pad"><span class="eyebrow">Adoption signal 02</span><h2 style="margin: 6px 0; font-size: 17px">5 / 6 practiced</h2><p style="margin: 0; color: var(--muted); font-size: 10px">Synthetic operators who completed the first-value recovery exercise.</p></section>
      <section class="card card-pad"><span class="eyebrow">First-week support</span><h2 style="margin: 6px 0; font-size: 17px">Daily · 09:15</h2><p style="margin: 0; color: var(--muted); font-size: 10px">Invented review cadence; handoff must name its receiving owner.</p></section>
    </div>`;
}

function acceptanceChecks() {
  const unresolved = Object.entries(state.exceptionStatuses).filter(([, status]) => status !== "accepted");
  const notReady = Object.entries(state.readinessStatuses).filter(([, status]) => status !== "ready");
  const failedUat = Object.entries(state.uatStatuses).filter(([, status]) => status !== "pass");
  const incompleteTraining = Object.entries(state.trainingStatuses).filter(([, status]) => status !== "complete");
  const missingHandoffs = Object.entries(state.handoffAcks).filter(([, acknowledged]) => !acknowledged);
  const unconfirmed = Object.entries(state.decisions).filter(([, confirmed]) => !confirmed);
  return [
    { id: "discovery", title: "Discovery decisions confirmed", pass: unconfirmed.length === 0, detail: unconfirmed.length ? `${unconfirmed.map(([id]) => id).join(", ")} still need confirmation.` : "Outcome, fixture, severity, and receiving owner are explicit." },
    { id: "readiness", title: "Readiness workstreams ready", pass: notReady.length === 0, detail: notReady.length ? `${notReady.map(([id]) => id).join(", ")} have not reached reviewer-ready state.` : "All eight invented workstreams have named evidence and exit criteria." },
    { id: "uat", title: "UAT expected results recorded", pass: failedUat.length === 0, detail: failedUat.length ? `${failedUat.map(([id]) => id).join(", ")} remain blocked.` : "All four synthetic cases have operator-recorded pass outcomes." },
    { id: "exceptions", title: "No unaccepted launch exception", pass: unresolved.length === 0, detail: unresolved.length ? `${unresolved.map(([id]) => `${id} is ${label(state.exceptionStatuses[id]).toLowerCase()}`).join("; ")}. Review-ready is not accepted.` : "Every synthetic exception has a named reviewer acceptance." },
    { id: "training", title: "Guided practice complete", pass: incompleteTraining.length === 0, detail: incompleteTraining.length ? `${incompleteTraining.map(([id]) => id).join(", ")} still need a recorded practice result.` : "All three invented practice modules are complete." },
    { id: "handoff", title: "Receiving owners acknowledged", pass: missingHandoffs.length === 0, detail: missingHandoffs.length ? `${missingHandoffs.map(([id]) => id).join(", ")} still lack explicit acknowledgment.` : "Program, operations, support, and delivery owners acknowledged their artifacts." },
    { id: "status", title: "Customer status update recorded", pass: state.statusUpdateSent, detail: state.statusUpdateSent ? "Milestone, risk, owner, and next decision are present." : "Record the synthetic customer status update from the command center." },
    { id: "first_value", title: "First-value event remains bounded", pass: true, detail: "The event uses one invented exception, human review, and no production system." },
    { id: "acceptance", title: "Named human acceptance recorded", pass: state.goLiveAccepted, detail: state.goLiveAccepted ? "Synthetic customer sponsor acceptance is in this session's audit." : "A deliberate acceptance click remains required after the first eight gates pass." },
  ];
}

function renderAcceptance() {
  const checks = acceptanceChecks();
  const passed = checks.filter((check) => check.pass).length;
  const prerequisitesPass = checks.slice(0, -1).every((check) => check.pass);
  const scoreText = state.checksRun ? `${passed}/${checks.length}` : "-/9";
  const scorePercent = state.checksRun ? Math.round((passed / checks.length) * 100) : 0;
  return `
    ${pageHead("Go-live acceptance", "Make the decision auditable, scoped, and human", "Passing checks supports a synthetic portfolio decision; it never authorizes a production launch.", '<button class="button-secondary" type="button" data-view-jump="overview">Return to command center</button>')}
    <div class="layout-split">
      <section class="card">
        <div class="card-head"><div><h2>Acceptance gates</h2><p>Deterministic checks over this session's invented state</p></div><button class="button-secondary" type="button" data-run-checks>Run acceptance checks</button></div>
        <div class="card-body checklist">
          ${checks.map((check) => {
            const visibleState = !state.checksRun ? "pending" : check.pass ? "pass" : "fail";
            return `<div class="check-item check-${visibleState}" data-check-id="${check.id}"><span class="check-icon">${visibleState === "pass" ? "✓" : visibleState === "fail" ? "!" : "…"}</span><div><strong>${escapeHTML(check.title)}</strong><small>${state.checksRun ? escapeHTML(check.detail) : "Run checks to evaluate this session."}</small></div>${pill(visibleState)}</div>`;
          }).join("")}
        </div>
      </section>
      <aside class="stack">
        <section class="acceptance-hero">
          <span class="eyebrow">Synthetic acceptance status</span>
          <div class="acceptance-score"><strong data-acceptance-score>${scoreText}</strong><span>gates passed</span></div>
          <p>${state.goLiveAccepted ? "A human acceptance event is recorded for the invented demo program." : prerequisitesPass ? "Prerequisites pass. The named customer sponsor still owns the explicit decision." : "Prerequisites remain incomplete. The demo keeps the acceptance action unavailable."}</p>
          <div class="progress"><i style="--progress: ${scorePercent}%"></i></div>
          <button class="button" style="width: 100%; margin-top: 16px" type="button" data-record-acceptance ${!state.checksRun || !prerequisitesPass || state.goLiveAccepted ? "disabled" : ""}>${state.goLiveAccepted ? "Synthetic acceptance recorded" : "Record synthetic go-live acceptance"}</button>
        </section>
        <section class="card">
          <div class="card-head"><div><h2>Decision boundary</h2><p>What this interaction does, and does not, mean</p></div></div>
          <div class="card-body">
            <div class="risk-callout"><span class="risk-icon" aria-hidden="true">!</span><div><strong>No production authority</strong><p>This click changes only in-memory demo state. It is not a vendor action, deployment, certification, customer instruction, or authorization.</p></div></div>
            <div class="detail-grid">
              <div class="detail-field"><span>Decision owner</span><strong>Mira Chen · invented customer sponsor</strong></div>
              <div class="detail-field"><span>Decision scope</span><p>One synthetic first-value event in a non-production fixture.</p></div>
            </div>
            <div class="button-row"><button class="button-secondary" type="button" data-export-audit>Export local audit JSON</button><button class="button-quiet" type="button" data-show-audit>View audit trail</button></div>
          </div>
        </section>
      </aside>
    </div>
    <section class="card" style="margin-top: 14px">
      <div class="audit-toolbar"><p><strong>Session audit preview:</strong> invented events only · deterministic SIM identifiers · no telemetry</p><span class="tag">${state.audit.length} events</span></div>
      <div class="card-body event-list">
        ${state.audit.slice(0, 4).map(renderAuditEvent).join("")}
      </div>
    </section>`;
}

function renderAuditEvent(event) {
  return `<div class="event-row"><span class="event-code">${escapeHTML(event.id)}</span><span class="event-node" aria-hidden="true">↳</span><div><strong>${escapeHTML(event.action)}</strong><small>${escapeHTML(event.detail)}</small></div><span class="tag">${escapeHTML(event.actor)}</span></div>`;
}

function renderAuditPage() {
  return `
    ${pageHead("Session audit", "Inspect every simulated decision in order", "The export is created locally only after a user click and contains invented demo state.", '<button class="button-secondary" type="button" data-export-audit>Export local audit JSON</button>')}
    <section class="card">
      <div class="audit-toolbar"><p><strong>${state.audit.length} synthetic events.</strong> No network, storage, analytics, account, or background export.</p><span class="tag tag-invented">Session memory only</span></div>
      <div class="card-body event-list">${state.audit.map(renderAuditEvent).join("")}</div>
    </section>`;
}

function render() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    const active = button.dataset.view === state.view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-current", active ? "page" : "false");
  });
  document.querySelector("#scenario-select").value = state.scenario;

  const renderers = {
    overview: renderOverview,
    discovery: renderDiscovery,
    readiness: renderReadiness,
    exceptions: renderExceptions,
    enablement: renderEnablement,
    acceptance: renderAcceptance,
  };
  document.querySelector("#app").innerHTML = state.view === "audit" ? renderAuditPage() : renderers[state.view]();
  revealActiveNavigation();
}

function advanceReadiness(id) {
  const current = state.readinessStatuses[id];
  if (current === "planned" || current === "scheduled") {
    state.readinessStatuses[id] = "working";
    addAudit("Implementation lead", `${id} simulated work started`, "The workstream moved to in progress; no readiness conclusion was recorded.");
    showToast(`${id} is in progress.`);
  } else if (current === "working") {
    state.readinessStatuses[id] = "review_ready";
    addAudit("Implementation lead", `${id} marked review-ready`, "Evidence is prepared for human review; no automatic readiness occurred.");
    showToast(`${id} is review-ready, not ready.`);
  } else if (current === "review_ready") {
    state.readinessStatuses[id] = "ready";
    addAudit("Named reviewer", `${id} readiness acknowledged`, "A simulated human reviewer evaluated the exit criterion and marked the workstream ready.");
    showToast(`${id} reviewer acknowledgment recorded.`);
  }
  state.checksRun = false;
  render();
}

function advanceException(id) {
  const current = state.exceptionStatuses[id];
  if (current === "open") {
    state.exceptionStatuses[id] = "working";
    addAudit("Exception owner", `${id} investigation started`, "The invented exception remains unresolved and visible to the launch team.");
    showToast(`${id} investigation started.`);
  } else if (current === "working") {
    state.exceptionStatuses[id] = "review_ready";
    addAudit("Exception owner", `${id} marked review-ready`, "Reproduction and correction evidence are ready; no automatic acceptance occurred.");
    showToast(`${id} is review-ready, not accepted.`);
  } else if (current === "review_ready") {
    state.exceptionStatuses[id] = "accepted";
    if (id === "EX-17") state.uatStatuses["UAT-04"] = "pass";
    if (id === "EX-29") state.handoffAcks["HO-03"] = true;
    addAudit("Named customer reviewer", `${id} evidence accepted`, "The reviewer acknowledged the invented evidence and its linked UAT or handoff state was updated.");
    showToast(`${id} human review recorded.`);
  }
  state.checksRun = false;
  render();
}

function exportAudit() {
  const payload = {
    schema: "first-value-launch-lab.synthetic-audit.v1",
    generated_by_user_action: true,
    runtime_network_used: false,
    persistence_used: false,
    boundary: {
      independent_portfolio_demo: true,
      synthetic_customer_and_program_data: true,
      no_affiliation: true,
      not_production_authority: true,
    },
    fixture: clone(FIXTURE.program),
    scenario: state.scenario,
    state: {
      decisions: clone(state.decisions),
      readiness: clone(state.readinessStatuses),
      exceptions: clone(state.exceptionStatuses),
      uat: clone(state.uatStatuses),
      training: clone(state.trainingStatuses),
      handoffs: clone(state.handoffAcks),
      status_update_recorded: state.statusUpdateSent,
      synthetic_go_live_accepted: state.goLiveAccepted,
    },
    audit: clone(state.audit),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = "synthetic-first-value-launch-audit.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
  showToast("Synthetic audit exported locally.");
}

function resetDemo() {
  const view = state.view === "audit" ? "acceptance" : state.view;
  state = buildState(state.scenario);
  state.view = view;
  updateLocation();
  render();
  showToast("In-memory demo state reset.");
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("button, [data-readiness-id]");
  if (!target) return;

  if (target.dataset.view) setView(target.dataset.view);
  if (target.dataset.viewJump) setView(target.dataset.viewJump);

  if (target.dataset.toggleDecision) {
    const id = target.dataset.toggleDecision;
    state.decisions[id] = !state.decisions[id];
    addAudit("Implementation lead", `${id} ${state.decisions[id] ? "confirmed" : "reopened"}`, "Synthetic discovery decision changed by a user in this session.");
    state.checksRun = false;
    render();
  }

  if (target.dataset.saveNote !== undefined) {
    const field = document.querySelector("[data-discovery-note]");
    state.discoveryNote = field.value.trim().slice(0, 280);
    addAudit("Implementation lead", "Discovery note recorded", state.discoveryNote || "A blank synthetic note was recorded.");
    showToast("Note added to the in-memory audit.");
  }

  if (target.dataset.readinessFilter) {
    state.readinessFilter = target.dataset.readinessFilter;
    render();
  }

  if (target.dataset.readinessId) {
    state.selectedReadiness = target.dataset.readinessId;
    render();
  }

  if (target.dataset.advanceReadiness) advanceReadiness(target.dataset.advanceReadiness);

  if (target.dataset.exceptionId) {
    state.selectedException = target.dataset.exceptionId;
    render();
  }

  if (target.dataset.advanceException) advanceException(target.dataset.advanceException);

  if (target.dataset.completeTraining) {
    const id = target.dataset.completeTraining;
    state.trainingStatuses[id] = "complete";
    addAudit("Training owner", `${id} guided practice recorded`, "A synthetic practice result was recorded; no real participant data is present.");
    state.checksRun = false;
    render();
    showToast(`${id} practice recorded.`);
  }

  if (target.dataset.ackHandoff) {
    const id = target.dataset.ackHandoff;
    state.handoffAcks[id] = true;
    addAudit("Named receiving owner", `${id} handoff acknowledged`, "The invented artifact and operating responsibility were explicitly acknowledged.");
    state.checksRun = false;
    render();
    showToast(`${id} acknowledgment recorded.`);
  }

  if (target.dataset.sendUpdate !== undefined) {
    state.statusUpdateSent = true;
    addAudit("Implementation lead", "Customer status update recorded", "Synthetic milestone, current risk, named owner, and next decision were included.");
    state.checksRun = false;
    render();
    showToast("Synthetic customer update recorded.");
  }

  if (target.dataset.runChecks !== undefined) {
    state.checksRun = true;
    addAudit("Implementation lead", "Acceptance checks run", `${acceptanceChecks().filter((check) => check.pass).length} of ${acceptanceChecks().length} synthetic gates passed.`);
    render();
    showToast("Acceptance checks evaluated locally.");
  }

  if (target.dataset.recordAcceptance !== undefined) {
    const checks = acceptanceChecks();
    const prerequisitesPass = checks.slice(0, -1).every((check) => check.pass);
    if (state.checksRun && prerequisitesPass) {
      state.goLiveAccepted = true;
      addAudit("Mira Chen · invented customer sponsor", "Synthetic go-live acceptance recorded", "Acceptance applies only to this invented portfolio fixture and grants no production authority.");
      render();
      showToast("Synthetic human acceptance recorded.");
    }
  }

  if (target.dataset.exportAudit !== undefined) exportAudit();
  if (target.dataset.showAudit !== undefined) {
    state.view = "audit";
    render();
  }
  if (target.dataset.resetDemo !== undefined) resetDemo();
  if (target.dataset.openHelp !== undefined) document.querySelector("#help-dialog").showModal();
  if (target.dataset.closeHelp !== undefined) document.querySelector("#help-dialog").close();
});

document.addEventListener("keydown", (event) => {
  if (event.target.matches("input, textarea, select") || event.ctrlKey || event.metaKey || event.altKey) return;
  const keyMap = { "1": "overview", "2": "discovery", "3": "readiness", "4": "exceptions", "5": "enablement", "6": "acceptance" };
  if (keyMap[event.key]) setView(keyMap[event.key]);
  if (event.key === "?") document.querySelector("#help-dialog").showModal();
});

document.querySelector("#scenario-select").addEventListener("change", (event) => {
  const scenario = event.target.value;
  if (!SCENARIOS.includes(scenario)) return;
  const view = state.view === "audit" ? "overview" : state.view;
  state = buildState(scenario);
  state.view = view;
  updateLocation();
  render();
  showToast(`Loaded ${scenario.replace("-", " ")} synthetic state.`);
});

document.querySelector("#help-dialog").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) event.currentTarget.close();
});

render();
