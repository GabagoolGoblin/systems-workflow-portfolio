"use strict";

const fixture = {
  customer: "Aster Vale Robotics",
  framework: "Orion Implementation Baseline v0.8",
  frameworkNote: "Fictional operational baseline",
  controls: [
    {
      id: "IR-01",
      name: "Account review handoff",
      owner: "Rowan Pike",
      evidenceIds: ["EV-101", "EV-102"],
      gapIds: ["GAP-07"],
      actionIds: ["ACT-204"],
      intent: "Keep the review owner, source roster, and review-period statement traceable during implementation."
    },
    {
      id: "IR-02",
      name: "Change authorization trace",
      owner: "Lina Park",
      evidenceIds: ["EV-104"],
      gapIds: [],
      actionIds: ["ACT-197"],
      intent: "Connect a fictional change sample to its declared approver and implementation note."
    },
    {
      id: "IR-03",
      name: "Recovery exercise follow-up",
      owner: "Milo Hart",
      evidenceIds: ["EV-108", "EV-109"],
      gapIds: ["GAP-12"],
      actionIds: ["ACT-211"],
      intent: "Retain contradictory exercise dates until a fictional owner resolves the record."
    },
    {
      id: "IR-04",
      name: "Vendor offboarding evidence",
      owner: "Tess Noor",
      evidenceIds: ["EV-112"],
      gapIds: ["GAP-18"],
      actionIds: ["ACT-219"],
      intent: "Track the evidence locator and reviewer acknowledgment for a fictional offboarding sample."
    },
    {
      id: "IR-05",
      name: "Incident contact routing",
      owner: "Inez Cole",
      evidenceIds: ["EV-115"],
      gapIds: [],
      actionIds: [],
      intent: "Make the declared escalation owner and exact synthetic source line easy to inspect."
    },
    {
      id: "IR-06",
      name: "Retention decision record",
      owner: "Unassigned",
      evidenceIds: ["EV-118"],
      gapIds: ["GAP-22"],
      actionIds: ["ACT-223"],
      intent: "Hold an implementation decision when both accountable ownership and supporting material are absent."
    }
  ],
  evidence: [
    {
      id: "EV-101",
      controlId: "IR-01",
      title: "Account review procedure",
      kind: "Synthetic procedure",
      locator: "Section 3.2 · lines 14–22",
      state: "accepted",
      note: "Owner and review steps are directly located in the invented source."
    },
    {
      id: "EV-102",
      controlId: "IR-01",
      title: "Privileged account roster",
      kind: "Synthetic CSV extract",
      locator: "Rows 2–18 · column owner_id",
      state: "qualified",
      note: "Roster is located, but the declared review period is still unresolved."
    },
    {
      id: "EV-104",
      controlId: "IR-02",
      title: "Change request sample",
      kind: "Synthetic ticket export",
      locator: "Record CHG-DEMO-014 · fields 5–9",
      state: "accepted",
      note: "Invented approver and implementation note are both present."
    },
    {
      id: "EV-108",
      controlId: "IR-03",
      title: "Exercise summary A",
      kind: "Synthetic meeting note",
      locator: "Paragraph 4 · date 08 May",
      state: "conflict",
      note: "Date disagrees with EV-109; neither value is selected automatically."
    },
    {
      id: "EV-109",
      controlId: "IR-03",
      title: "Exercise summary B",
      kind: "Synthetic follow-up note",
      locator: "Paragraph 2 · date 09 May",
      state: "conflict",
      note: "Conflicting declaration is preserved for human resolution."
    },
    {
      id: "EV-112",
      controlId: "IR-04",
      title: "Vendor access closure sample",
      kind: "Synthetic checklist",
      locator: "Item 7 · closure acknowledgment",
      state: "qualified",
      note: "Exact item exists; named reviewer acknowledgment has not been recorded."
    },
    {
      id: "EV-115",
      controlId: "IR-05",
      title: "Escalation roster",
      kind: "Synthetic contact matrix",
      locator: "Route INCIDENT-DEMO · revision 3",
      state: "accepted",
      note: "Fictional route, owner, and revision are traceable."
    },
    {
      id: "EV-118",
      controlId: "IR-06",
      title: "Retention decision support",
      kind: "Not supplied",
      locator: "Not supplied",
      state: "missing",
      note: "No artifact is invented to fill the gap."
    }
  ],
  gaps: [
    {
      id: "GAP-07",
      controlId: "IR-01",
      severity: "high",
      title: "Review period is not declared",
      detail: "The synthetic roster has owners but no field that establishes when the review occurred.",
      owner: "Rowan Pike",
      status: "open",
      due: "Demo week 2",
      actionId: "ACT-204"
    },
    {
      id: "GAP-12",
      controlId: "IR-03",
      severity: "blocker",
      title: "Exercise dates conflict",
      detail: "Two invented notes declare different dates. The workflow retains both and requires an owner decision.",
      owner: "Milo Hart",
      status: "triage",
      due: "Demo week 1",
      actionId: "ACT-211"
    },
    {
      id: "GAP-18",
      controlId: "IR-04",
      severity: "medium",
      title: "Reviewer acknowledgment is absent",
      detail: "The fictional closure item is located, but no reviewer acknowledgment is represented.",
      owner: "Tess Noor",
      status: "open",
      due: "Demo week 3",
      actionId: "ACT-219"
    },
    {
      id: "GAP-22",
      controlId: "IR-06",
      severity: "high",
      title: "Owner and source are both missing",
      detail: "The demo does not infer accountability or fabricate a document when neither was supplied.",
      owner: "Unassigned",
      status: "open",
      due: "Not scheduled",
      actionId: "ACT-223"
    }
  ],
  actions: [
    {
      id: "ACT-197",
      controlId: "IR-02",
      gapId: null,
      title: "Confirm change sample locator",
      owner: "Lina Park",
      status: "done",
      next: "No further demo action"
    },
    {
      id: "ACT-204",
      controlId: "IR-01",
      gapId: "GAP-07",
      title: "Verify review-period field",
      owner: "Rowan Pike",
      status: "queued",
      next: "Inspect the synthetic roster definition"
    },
    {
      id: "ACT-211",
      controlId: "IR-03",
      gapId: "GAP-12",
      title: "Resolve exercise date conflict",
      owner: "Milo Hart",
      status: "in_progress",
      next: "Record the selected declaration and rationale"
    },
    {
      id: "ACT-219",
      controlId: "IR-04",
      gapId: "GAP-18",
      title: "Collect reviewer acknowledgment",
      owner: "Tess Noor",
      status: "queued",
      next: "Request a fictional reviewer decision"
    },
    {
      id: "ACT-223",
      controlId: "IR-06",
      gapId: "GAP-22",
      title: "Assign decision owner",
      owner: "Unassigned",
      status: "queued",
      next: "Route to the fictional implementation lead"
    }
  ],
  audit: [
    { id: "EVT-001", time: "09:12:04", actor: "Demo import", title: "Synthetic baseline loaded", detail: "Six fictional controls and eight invented evidence records were added." },
    { id: "EVT-002", time: "09:12:11", actor: "Rule engine", title: "Four implementation gaps retained", detail: "No missing value was inferred or silently accepted." },
    { id: "EVT-003", time: "09:13:02", actor: "Milo Hart", title: "Action moved to in progress", detail: "ACT-211 remains linked to conflicting evidence EV-108 and EV-109." },
    { id: "EVT-004", time: "09:14:20", actor: "Lina Park", title: "Change sample locator confirmed", detail: "ACT-197 completed against fictional record CHG-DEMO-014." },
    { id: "EVT-005", time: "09:15:08", actor: "Demo system", title: "Workspace boundary recorded", detail: "Operational implementation state only; no compliance conclusion." }
  ]
};

const viewMeta = {
  overview: {
    label: "Readiness board",
    eyebrow: "Implementation workspace",
    title: "Turn ambiguity into owned next steps.",
    subtitle: "A fictional baseline is decomposed into evidence, gaps, owners, and acceptance conditions, without claiming compliance."
  },
  gaps: {
    label: "Gap triage",
    eyebrow: "Exception workflow",
    title: "Keep every unresolved fact visible.",
    subtitle: "Filter and inspect gaps while preserving source uncertainty, severity, ownership, and the next bounded action."
  },
  evidence: {
    label: "Evidence map",
    eyebrow: "Traceability",
    title: "Map records without overstating them.",
    subtitle: "Each fictional artifact carries an exact locator, a qualification state, and a link to one invented control."
  },
  actions: {
    label: "Owner actions",
    eyebrow: "Implementation follow-through",
    title: "Move work forward without hiding the gap.",
    subtitle: "Advance synthetic tasks through queued, in-progress, and done states; linked gaps become review-ready, never auto-accepted."
  },
  acceptance: {
    label: "Acceptance desk",
    eyebrow: "Deterministic guardrails",
    title: "Make readiness checks explain themselves.",
    subtitle: "Run explicit implementation checks and record a reviewer acknowledgment only after every prerequisite passes."
  },
  audit: {
    label: "Audit trail",
    eyebrow: "Decision history",
    title: "Leave a trail a reviewer can question.",
    subtitle: "See imported state, simulated decisions, and acceptance events in one local, exportable record."
  }
};

const allowedViews = Object.keys(viewMeta);
const params = new URLSearchParams(window.location.search);
const initialView = allowedViews.includes(params.get("view")) ? params.get("view") : "overview";
const initialScenario = ["default", "activity", "ready"].includes(params.get("scenario")) ? params.get("scenario") : "default";

function createInitialState(scenario = "default") {
  const next = {
    view: initialView,
    gapFilter: "all",
    search: "",
    selectedGapId: "GAP-12",
    selectedEvidenceId: "EV-108",
    selectedControlId: "IR-01",
    actionStatuses: Object.fromEntries(fixture.actions.map(action => [action.id, action.status])),
    gapStatuses: Object.fromEntries(fixture.gaps.map(gap => [gap.id, gap.status])),
    evidenceStates: Object.fromEntries(fixture.evidence.map(item => [item.id, item.state])),
    acknowledgments: new Set(["IR-02", "IR-05"]),
    lastCheckControlId: null,
    audit: fixture.audit.map(event => ({ ...event })),
    eventSequence: fixture.audit.length
  };

  if (scenario === "activity" || scenario === "ready") {
    next.actionStatuses["ACT-204"] = scenario === "ready" ? "done" : "in_progress";
    next.gapStatuses["GAP-07"] = scenario === "ready" ? "review_accepted" : "triage";
    next.audit.push({
      id: "EVT-006",
      time: "09:16:14",
      actor: "Rowan Pike",
      title: scenario === "ready" ? "Review-period action completed" : "Review-period action started",
      detail: scenario === "ready" ? "GAP-07 moved to review-ready; acceptance still requires an explicit check." : "ACT-204 moved to in progress; GAP-07 remains unresolved."
    });
    next.eventSequence += 1;
  }

  if (scenario === "ready") {
    next.evidenceStates["EV-102"] = "accepted";
    next.acknowledgments.add("IR-01");
    next.lastCheckControlId = "IR-01";
    next.audit.push({
      id: "EVT-007",
      time: "09:17:03",
      actor: "Synthetic reviewer",
      title: "IR-01 implementation checks accepted",
      detail: "Seven of seven local prerequisites passed; this is not a compliance determination."
    });
    next.eventSequence += 1;
  }

  return next;
}

let state = createInitialState(initialScenario);

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
    accepted: "Accepted",
    qualified: "Qualified",
    conflict: "Conflict",
    missing: "Missing",
    open: "Open",
    triage: "In triage",
    review_ready: "Review-ready",
    review_accepted: "Review accepted",
    queued: "Queued",
    in_progress: "In progress",
    done: "Done",
    blocker: "Blocker",
    high: "High",
    medium: "Medium"
  };
  return labels[value] || value;
}

function controlById(id) {
  return fixture.controls.find(control => control.id === id);
}

function evidenceById(id) {
  return fixture.evidence.find(item => item.id === id);
}

function gapById(id) {
  return fixture.gaps.find(gap => gap.id === id);
}

function actionById(id) {
  return fixture.actions.find(action => action.id === id);
}

function unresolvedGap(gap) {
  return ["open", "triage"].includes(state.gapStatuses[gap.id]);
}

function evidenceState(item) {
  return state.evidenceStates[item.id];
}

function evidenceNote(item) {
  if (evidenceState(item) === "accepted" && item.state === "qualified") {
    return "The prior qualification was resolved by the linked demo action and reviewer acknowledgment.";
  }
  return item.note;
}

function controlState(control) {
  const evidence = control.evidenceIds.map(evidenceById);
  const linkedGaps = control.gapIds.map(gapById);
  const unresolved = linkedGaps.filter(unresolvedGap);
  if (evidence.some(item => ["missing", "conflict"].includes(evidenceState(item))) || unresolved.some(gap => ["blocker", "high"].includes(gap.severity))) {
    return "blocked";
  }
  if (unresolved.length || evidence.some(item => evidenceState(item) === "qualified") || !state.acknowledgments.has(control.id)) {
    return "review";
  }
  return "ready";
}

function screenHeader(view, actions = "") {
  const meta = viewMeta[view];
  return `
    <header class="screen-head">
      <div>
        <p class="eyebrow">${escapeHTML(meta.eyebrow)}</p>
        <h1 class="screen-title">${escapeHTML(meta.title)}</h1>
        <p class="screen-subtitle">${escapeHTML(meta.subtitle)}</p>
      </div>
      ${actions ? `<div class="head-actions">${actions}</div>` : ""}
    </header>
  `;
}

function scopeBanner() {
  return `
    <div class="scope-banner" role="note">
      <span class="scope-icon" aria-hidden="true">!</span>
      <div><strong>“Locally ready” is an operational demo label only.</strong> It means all seven listed prerequisites passed for a fictional record. It is not legal advice, an assessment, certification, production readiness, third-party acceptance, or a statement about any vendor product behavior.</div>
    </div>
  `;
}

function renderOverview() {
  const counts = fixture.controls.reduce((summary, control) => {
    summary[controlState(control)] += 1;
    return summary;
  }, { ready: 0, review: 0, blocked: 0 });
  const openGaps = fixture.gaps.filter(unresolvedGap).length;
  const mapped = fixture.evidence.filter(item => item.state !== "missing").length;

  return `
    ${screenHeader("overview", '<button class="button primary" type="button" data-go="gaps">Triage open gaps</button>')}
    ${scopeBanner()}
    <section class="metric-grid" aria-label="Synthetic readiness summary">
      <article class="metric-card">
        <p class="metric-label">Mapped evidence records</p>
        <p class="metric-value">${mapped}<span class="visually-hidden"> of ${fixture.evidence.length}</span></p>
        <p class="metric-detail">${fixture.evidence.length - mapped} deliberately missing • exact locators shown</p>
      </article>
      <article class="metric-card coral">
        <p class="metric-label">Unresolved gaps</p>
        <p class="metric-value">${openGaps}</p>
        <p class="metric-detail">${fixture.gaps.filter(gap => gap.severity === "blocker").length} blocker • no inferred resolutions</p>
      </article>
      <article class="metric-card amber">
        <p class="metric-label">Controls needing review</p>
        <p class="metric-value">${counts.review + counts.blocked}</p>
        <p class="metric-detail">${counts.ready} locally ready • ${counts.blocked} blocked</p>
      </article>
      <article class="metric-card violet">
        <p class="metric-label">Named owners</p>
        <p class="metric-value">${fixture.controls.filter(control => control.owner !== "Unassigned").length}<span class="visually-hidden"> of ${fixture.controls.length}</span></p>
        <p class="metric-detail">1 intentionally unassigned for triage</p>
      </article>
    </section>

    <section class="dashboard-grid">
      <article class="card">
        <div class="card-head">
          <div><h2 class="card-title">Control implementation board</h2><p class="card-copy">${escapeHTML(fixture.framework)} • all labels invented</p></div>
          <span class="badge mapped">6 controls</span>
        </div>
        <div class="card-body control-stack">
          ${fixture.controls.map(control => `
            <button class="control-row" type="button" data-open-control="${control.id}" aria-label="Inspect ${escapeHTML(control.id)} ${escapeHTML(control.name)}">
              <span class="control-code">${escapeHTML(control.id)}</span>
              <span><span class="control-name">${escapeHTML(control.name)}</span></span>
              <span class="control-owner"><strong>${escapeHTML(control.owner)}</strong>${control.evidenceIds.length} evidence link${control.evidenceIds.length === 1 ? "" : "s"}</span>
              <span class="badge ${controlState(control)}">${label(controlState(control))}</span>
            </button>
          `).join("")}
        </div>
      </article>

      <aside class="card">
        <div class="card-head">
          <div><h2 class="card-title">Implementation signal</h2><p class="card-copy">Descriptive counts, not a score</p></div>
        </div>
        <div class="card-body">
          <p class="section-label">Current distribution</p>
          <div class="coverage-bar" aria-hidden="true"><span></span><span></span><span></span></div>
          <div class="legend-row">
            <span class="legend-item"><span class="legend-dot"></span>${counts.ready} locally ready</span>
            <span class="legend-item"><span class="legend-dot amber"></span>${counts.review} review</span>
            <span class="legend-item"><span class="legend-dot coral"></span>${counts.blocked} blocked</span>
          </div>
          <div class="callout">
            <strong>Why the board stops here</strong>
            <p>The interface makes implementation prerequisites inspectable. A qualified professional would still determine what any real framework requires.</p>
          </div>
          <div class="detail-section">
            <p class="section-label">Suggested demo path</p>
            <ol class="plain-list">
              <li>Open GAP-07 and inspect its exact missing fact.</li>
              <li>Advance ACT-204 through its simulated states.</li>
              <li>Run the IR-01 acceptance checks.</li>
              <li>Inspect the resulting audit event.</li>
            </ol>
          </div>
        </div>
      </aside>
    </section>
  `;
}

function filteredGaps() {
  const query = state.search.trim().toLowerCase();
  return fixture.gaps.filter(gap => {
    const status = state.gapStatuses[gap.id];
    const matchesFilter = state.gapFilter === "all"
      || (state.gapFilter === "critical" && ["blocker", "high"].includes(gap.severity))
      || (state.gapFilter === "unassigned" && gap.owner === "Unassigned")
      || (state.gapFilter === "review_ready" && status === "review_ready");
    const corpus = `${gap.id} ${gap.title} ${gap.owner} ${gap.controlId}`.toLowerCase();
    return matchesFilter && (!query || corpus.includes(query));
  });
}

function renderGapDetail(gap) {
  const control = controlById(gap.controlId);
  const action = actionById(gap.actionId);
  const gapStatus = state.gapStatuses[gap.id];
  return `
    <aside class="detail-card" aria-label="Selected gap details">
      <div class="detail-hero">
        <span class="control-code">${escapeHTML(gap.id)} • ${escapeHTML(control.id)}</span>
        <h2>${escapeHTML(gap.title)}</h2>
        <p>${escapeHTML(gap.detail)}</p>
      </div>
      <div class="detail-body">
        <dl class="definition-grid">
          <div><dt>Severity</dt><dd><span class="badge ${gap.severity}">${label(gap.severity)}</span></dd></div>
          <div><dt>State</dt><dd><span class="badge ${gapStatus}">${label(gapStatus)}</span></dd></div>
          <div><dt>Owner</dt><dd>${escapeHTML(gap.owner)}</dd></div>
          <div><dt>Target</dt><dd>${escapeHTML(gap.due)}</dd></div>
        </dl>
        <section class="detail-section">
          <p class="section-label">Bounded next action</p>
          <p class="list-title">${escapeHTML(action.title)}</p>
          <p class="list-meta">${escapeHTML(action.next)}</p>
        </section>
        <section class="detail-section">
          <p class="section-label">Preserved boundary</p>
          <ul class="plain-list">
            <li>The source uncertainty remains visible.</li>
            <li>Changing task state does not accept the control.</li>
            <li>No real framework conclusion is represented.</li>
          </ul>
        </section>
        <div class="button-row detail-section">
          <button class="button primary" type="button" data-go-action="${escapeHTML(action.id)}">Open owner action</button>
          <button class="button" type="button" data-go-evidence="${escapeHTML(control.evidenceIds[0])}">Inspect evidence</button>
        </div>
      </div>
    </aside>
  `;
}

function renderGaps() {
  const gaps = filteredGaps();
  if (!gaps.some(gap => gap.id === state.selectedGapId) && gaps.length) {
    state.selectedGapId = gaps[0].id;
  }
  const selected = gaps.length ? gapById(state.selectedGapId) : null;
  const filterButtons = [
    ["all", "All gaps"],
    ["critical", "Blocker + high"],
    ["unassigned", "Needs owner"],
    ["review_ready", "Review-ready"]
  ];

  return `
    ${screenHeader("gaps")}
    ${scopeBanner()}
    <div class="toolbar">
      <div class="filter-row" aria-label="Gap filters">
        ${filterButtons.map(([value, copy]) => `<button class="filter-button ${state.gapFilter === value ? "active" : ""}" type="button" data-gap-filter="${value}" aria-pressed="${state.gapFilter === value}">${copy}</button>`).join("")}
      </div>
      <label class="search-wrap"><span aria-hidden="true">⌕</span><span class="visually-hidden">Search gaps</span><input id="gap-search" type="search" value="${escapeHTML(state.search)}" placeholder="Search gap, owner, or control"></label>
    </div>
    <section class="split-view">
      <article class="card">
        <div class="card-head"><div><h2 class="card-title">Triage queue</h2><p class="card-copy">${gaps.length} of ${fixture.gaps.length} fictional gaps shown</p></div><span class="badge open">${fixture.gaps.filter(unresolvedGap).length} unresolved</span></div>
        <div class="card-body gap-list">
          ${gaps.length ? gaps.map(gap => `
            <button class="gap-item ${gap.severity} ${state.selectedGapId === gap.id ? "selected" : ""}" type="button" data-gap-id="${gap.id}">
              <span class="gap-glyph" aria-hidden="true">${escapeHTML(gap.id.split("-")[1])}</span>
              <span><span class="list-title">${escapeHTML(gap.title)}</span><span class="list-meta">${escapeHTML(gap.controlId)} • ${escapeHTML(gap.owner)} • ${escapeHTML(gap.due)}</span></span>
              <span class="inline-cluster"><span class="badge ${gap.severity}">${label(gap.severity)}</span><span class="badge ${state.gapStatuses[gap.id]}">${label(state.gapStatuses[gap.id])}</span></span>
            </button>
          `).join("") : `
            <div class="empty-state"><div><div class="empty-glyph" aria-hidden="true">0</div><p class="empty-title">No matching gaps</p><p class="empty-copy">Change the filter or search. No records were deleted.</p></div></div>
          `}
        </div>
      </article>
      ${selected ? renderGapDetail(selected) : '<aside class="detail-card empty-state"><div><p class="empty-title">Nothing selected</p><p class="empty-copy">Choose a different filter to inspect a gap.</p></div></aside>'}
    </section>
  `;
}

function renderEvidenceDetail(item) {
  const control = controlById(item.controlId);
  const currentState = evidenceState(item);
  return `
    <aside class="detail-card" aria-label="Selected evidence details">
      <div class="detail-hero">
        <span class="control-code">${escapeHTML(item.id)} • ${escapeHTML(control.id)}</span>
        <h2>${escapeHTML(item.title)}</h2>
        <p>${escapeHTML(item.kind)}</p>
      </div>
      <div class="detail-body">
        <dl class="definition-grid">
          <div><dt>Declared state</dt><dd><span class="badge ${currentState}">${label(currentState)}</span></dd></div>
          <div><dt>Control owner</dt><dd>${escapeHTML(control.owner)}</dd></div>
        </dl>
        <section class="detail-section">
          <p class="section-label">Exact synthetic locator</p>
          <div class="source-box">${escapeHTML(item.locator)}</div>
        </section>
        <section class="detail-section">
          <p class="section-label">Qualification note</p>
          <p class="list-meta">${escapeHTML(evidenceNote(item))}</p>
        </section>
        <div class="callout"><strong>Mapping is not acceptance</strong><p>A located artifact can remain qualified or conflicting. The acceptance desk checks those states separately.</p></div>
        <div class="button-row detail-section"><button class="button primary" type="button" data-go-acceptance="${escapeHTML(control.id)}">Open acceptance checks</button></div>
      </div>
    </aside>
  `;
}

function renderEvidence() {
  const selected = evidenceById(state.selectedEvidenceId) || fixture.evidence[0];
  return `
    ${screenHeader("evidence", '<span class="badge mapped">8 invented records</span>')}
    ${scopeBanner()}
    <section class="evidence-grid">
      <article class="card">
        <div class="card-head"><div><h2 class="card-title">Declared evidence relationships</h2><p class="card-copy">One record → one fictional control • no automatic conclusion</p></div></div>
        <div class="card-body gap-list">
          ${fixture.evidence.map(item => `
            <button class="evidence-row ${state.selectedEvidenceId === item.id ? "selected" : ""}" type="button" data-evidence-id="${item.id}">
              <span class="evidence-node ${evidenceState(item)}" aria-hidden="true">${escapeHTML(item.id.split("-")[1])}</span>
              <span><span class="list-title">${escapeHTML(item.title)}</span><span class="list-meta">${escapeHTML(item.controlId)} • ${escapeHTML(item.kind)} • ${escapeHTML(item.locator)}</span></span>
              <span class="badge ${evidenceState(item)}">${label(evidenceState(item))}</span>
            </button>
          `).join("")}
        </div>
      </article>
      ${renderEvidenceDetail(selected)}
    </section>
  `;
}

function actionCard(action) {
  const status = state.actionStatuses[action.id];
  const control = controlById(action.controlId);
  const initials = action.owner === "Unassigned" ? "?" : action.owner.split(" ").map(part => part[0]).join("");
  const nextLabel = status === "queued" ? "Start simulated work" : status === "in_progress" ? "Mark review-ready" : "Completed in demo";
  return `
    <article class="action-item">
      <div class="inline-cluster"><span class="control-code">${escapeHTML(action.id)}</span><span class="badge ${status}">${label(status)}</span></div>
      <p class="list-title">${escapeHTML(action.title)}</p>
      <p class="list-meta">${escapeHTML(control.id)} • ${escapeHTML(action.next)}</p>
      <div class="action-owner"><span class="avatar" aria-hidden="true">${escapeHTML(initials)}</span><span>${escapeHTML(action.owner)}</span></div>
      <button class="button ${status === "done" ? "" : "primary"}" type="button" data-advance-action="${action.id}" ${status === "done" ? "disabled" : ""}>${nextLabel}</button>
    </article>
  `;
}

function renderActions() {
  const groups = [
    ["queued", "Queued", "Waiting for an owner"],
    ["in_progress", "In progress", "Simulated work underway"],
    ["done", "Done", "Still requires acceptance"]
  ];
  return `
    ${screenHeader("actions", '<button class="button" type="button" data-reset-demo>Reset demo state</button>')}
    ${scopeBanner()}
    <section class="action-board" aria-label="Synthetic owner action board">
      ${groups.map(([status, title, copy]) => {
        const actions = fixture.actions.filter(action => state.actionStatuses[action.id] === status);
        return `
          <section class="action-column" aria-labelledby="column-${status}">
            <div class="column-head"><div><h2 id="column-${status}">${title}</h2><span>${copy}</span></div><span>${actions.length}</span></div>
            <div class="action-list">${actions.length ? actions.map(actionCard).join("") : '<div class="empty-state"><div><div class="empty-glyph" aria-hidden="true">✓</div><p class="empty-title">No actions here</p></div></div>'}</div>
          </section>
        `;
      }).join("")}
    </section>
  `;
}

function acceptanceChecks(control) {
  const evidence = control.evidenceIds.map(evidenceById);
  const gaps = control.gapIds.map(gapById);
  const actions = control.actionIds.map(actionById);
  const blockingGaps = gaps.filter(gap => unresolvedGap(gap) && ["blocker", "high"].includes(gap.severity));
  const reviewReadyGaps = gaps.filter(gap => state.gapStatuses[gap.id] === "review_ready");
  const acceptedGaps = gaps.filter(gap => state.gapStatuses[gap.id] === "review_accepted");
  const gapDetail = blockingGaps.length
    ? `${blockingGaps.map(gap => gap.id).join(", ")} remains blocking`
    : reviewReadyGaps.length
      ? `${reviewReadyGaps.map(gap => gap.id).join(", ")} is review-ready, not accepted`
      : acceptedGaps.length
        ? `${acceptedGaps.map(gap => gap.id).join(", ")} reviewer-accepted in this demo`
        : "No blocking gap remains";
  return [
    { id: "owner", title: "Named implementation owner", detail: control.owner === "Unassigned" ? "No owner supplied" : control.owner, pass: control.owner !== "Unassigned" },
    { id: "mapping", title: "At least one evidence record mapped", detail: `${evidence.length} record${evidence.length === 1 ? "" : "s"} declared`, pass: evidence.length > 0 },
    { id: "locator", title: "Every mapped record has an exact locator", detail: evidence.some(item => item.locator === "Not supplied") ? "A locator is missing" : "All locators present", pass: evidence.every(item => item.locator !== "Not supplied") },
    { id: "conflict", title: "No conflicting or missing evidence state", detail: evidence.some(item => ["conflict", "missing"].includes(evidenceState(item))) ? "Conflict or missing record retained" : "No blocking evidence state", pass: evidence.every(item => !["conflict", "missing"].includes(evidenceState(item))) },
    { id: "gaps", title: "No unresolved blocker or high gap", detail: gapDetail, pass: blockingGaps.length === 0 },
    { id: "actions", title: "Every linked owner action is complete", detail: actions.length ? `${actions.filter(action => state.actionStatuses[action.id] === "done").length} of ${actions.length} complete` : "No linked actions required", pass: actions.every(action => state.actionStatuses[action.id] === "done") },
    { id: "ack", title: "Reviewer acknowledgment recorded", detail: state.acknowledgments.has(control.id) ? "Synthetic reviewer acknowledgment present" : "Explicit acknowledgment still required", pass: state.acknowledgments.has(control.id) }
  ];
}

function prerequisitesPass(control) {
  return acceptanceChecks(control).slice(0, 6).every(check => check.pass);
}

function renderAcceptance() {
  const control = controlById(state.selectedControlId) || fixture.controls[0];
  const checks = acceptanceChecks(control);
  const hasRun = state.lastCheckControlId === control.id;
  const passed = checks.filter(check => check.pass).length;
  const resultLabel = !hasRun ? "Not run" : passed === checks.length ? "Locally ready" : "Not ready";
  const resultClass = !hasRun ? "not_run" : passed === checks.length ? "ready" : "blocked";
  return `
    ${screenHeader("acceptance", '<button class="button primary" type="button" data-run-checks>Run acceptance checks</button>')}
    ${scopeBanner()}
    <section class="acceptance-layout">
      <article class="card">
        <div class="card-head"><div><h2 class="card-title">Choose a fictional control</h2><p class="card-copy">Checks are evaluated from current in-memory state</p></div></div>
        <div class="card-body control-picker">
          ${fixture.controls.map(item => `
            <button class="select-control ${item.id === control.id ? "active" : ""}" type="button" data-select-control="${item.id}">
              <span><span class="control-code">${escapeHTML(item.id)}</span><span class="control-name">${escapeHTML(item.name)}</span></span>
              <span class="badge ${controlState(item)}">${label(controlState(item))}</span>
            </button>
          `).join("")}
        </div>
      </article>
      <article class="acceptance-summary" aria-label="Acceptance check results">
        <div class="acceptance-result-head">
          <div><p class="control-code">${escapeHTML(control.id)}</p><h2 class="card-title">${escapeHTML(control.name)}</h2></div>
          <div class="inline-cluster"><span class="badge ${resultClass}">${resultLabel}</span><span class="result-score"><strong>${hasRun ? passed : "-"}</strong><span>/ 7</span></span></div>
        </div>
        <div class="check-list">
          ${checks.map(check => {
            const stateClass = !hasRun ? "pending" : check.pass ? "pass" : "fail";
            const symbol = !hasRun ? "·" : check.pass ? "✓" : "!";
            return `
              <div class="check-item ${stateClass}">
                <span class="check-icon" aria-hidden="true">${symbol}</span>
                <span><span class="list-title">${escapeHTML(check.title)}</span><span class="list-meta">${hasRun ? escapeHTML(check.detail) : "Run checks to evaluate current state"}</span></span>
                <span class="badge ${!hasRun ? "not_run" : check.pass ? "good" : "open"}">${!hasRun ? "Not run" : check.pass ? "Pass" : "Stop"}</span>
              </div>
            `;
          }).join("")}
        </div>
        <div class="button-row" style="padding: 0 18px 4px">
          <button class="button" type="button" data-acknowledge ${prerequisitesPass(control) && !state.acknowledgments.has(control.id) ? "" : "disabled"}>Record reviewer acknowledgment</button>
          ${control.actionIds.some(id => state.actionStatuses[id] !== "done") ? '<button class="button" type="button" data-go="actions">Open linked actions</button>' : ""}
        </div>
        <p class="acceptance-note"><strong>Meaning of “locally ready”:</strong> all seven demo prerequisites passed for the current fictional record. It does not mean compliant, certified, production-ready, or accepted by any third party.</p>
      </article>
    </section>
  `;
}

function renderAudit() {
  const reversed = [...state.audit].reverse();
  return `
    ${screenHeader("audit", '<button class="button primary" type="button" data-export-audit>Download synthetic JSON</button><button class="button" type="button" data-reset-demo>Reset demo</button>')}
    ${scopeBanner()}
    <section class="audit-layout">
      <article class="card">
        <div class="card-head"><div><h2 class="card-title">Local decision history</h2><p class="card-copy">Newest first • changes exist only in this browser tab</p></div><span class="badge mapped">${state.audit.length} events</span></div>
        <div class="card-body event-list">
          ${reversed.map(event => `
            <article class="event-item">
              <span class="event-glyph" aria-hidden="true"></span>
              <div><p class="event-title">${escapeHTML(event.title)}</p><p class="event-meta">${escapeHTML(event.actor)} • ${escapeHTML(event.detail)}</p></div>
              <time class="event-time">${escapeHTML(event.time)}</time>
            </article>
          `).join("")}
        </div>
      </article>
      <aside class="card">
        <div class="card-head"><div><h2 class="card-title">Export boundary</h2><p class="card-copy">Portable demo receipt</p></div></div>
        <div class="card-body">
          <div class="manifest-grid">
            <div class="manifest-row"><span>Workspace</span><strong>Aster Vale Robotics (invented)</strong></div>
            <div class="manifest-row"><span>Framework</span><strong>Orion v0.8 (fictional)</strong></div>
            <div class="manifest-row"><span>Source mode</span><strong>Embedded fixture / offline</strong></div>
            <div class="manifest-row"><span>Persistence</span><strong>None / refresh resets</strong></div>
            <div class="manifest-row"><span>Conclusion</span><strong>Operational state only</strong></div>
          </div>
          <div class="callout"><strong>Download behavior</strong><p>The button creates a JSON file locally after a user click. It does not upload, synchronize, or call an API.</p></div>
        </div>
      </aside>
    </section>
  `;
}

function addAudit(actor, title, detail) {
  state.eventSequence += 1;
  const seconds = 10 + state.eventSequence * 7;
  const minute = 15 + Math.floor(seconds / 60);
  const second = seconds % 60;
  state.audit.push({
    id: `EVT-${String(state.eventSequence).padStart(3, "0")}`,
    time: `09:${String(minute).padStart(2, "0")}:${String(second).padStart(2, "0")}`,
    actor,
    title,
    detail
  });
}

function render() {
  document.querySelectorAll("[data-view]").forEach(button => {
    const active = button.dataset.view === state.view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-current", active ? "page" : "false");
  });
  const renderers = {
    overview: renderOverview,
    gaps: renderGaps,
    evidence: renderEvidence,
    actions: renderActions,
    acceptance: renderAcceptance,
    audit: renderAudit
  };
  document.getElementById("view-root").innerHTML = renderers[state.view]();
  document.getElementById("event-count").textContent = `${state.audit.length} logged events`;
  document.title = `${viewMeta[state.view].label} | Implementation Readiness Lab`;
}

function navigate(view) {
  if (!allowedViews.includes(view)) return;
  state.view = view;
  const next = new URL(window.location.href);
  next.searchParams.set("view", view);
  next.searchParams.delete("scenario");
  window.history.replaceState({}, "", next);
  render();
  document.getElementById("workspace").focus({ preventScroll: true });
}

function advanceAction(actionId) {
  const action = actionById(actionId);
  if (!action) return;
  const current = state.actionStatuses[actionId];
  if (current === "queued") {
    state.actionStatuses[actionId] = "in_progress";
    if (action.gapId) state.gapStatuses[action.gapId] = "triage";
    addAudit(action.owner, `${action.id} moved to in progress`, `${action.gapId || action.controlId} remains unresolved while simulated work is underway.`);
  } else if (current === "in_progress") {
    state.actionStatuses[actionId] = "done";
    if (action.gapId) state.gapStatuses[action.gapId] = "review_ready";
    addAudit(action.owner, `${action.id} marked complete`, `${action.gapId || action.controlId} moved to review-ready; no automatic acceptance occurred.`);
  }
  state.lastCheckControlId = null;
  render();
}

function runChecks() {
  const control = controlById(state.selectedControlId);
  state.lastCheckControlId = control.id;
  const checks = acceptanceChecks(control);
  const passed = checks.filter(check => check.pass).length;
  addAudit("Demo rule engine", `${control.id} acceptance checks run`, `${passed} of ${checks.length} implementation prerequisites passed; no compliance conclusion.`);
  render();
}

function acknowledge() {
  const control = controlById(state.selectedControlId);
  if (!prerequisitesPass(control) || state.acknowledgments.has(control.id)) return;
  state.acknowledgments.add(control.id);
  control.gapIds.forEach(gapId => {
    if (state.gapStatuses[gapId] === "review_ready") state.gapStatuses[gapId] = "review_accepted";
  });
  control.evidenceIds.forEach(evidenceId => {
    if (state.evidenceStates[evidenceId] === "qualified") state.evidenceStates[evidenceId] = "accepted";
  });
  state.lastCheckControlId = control.id;
  addAudit("Synthetic reviewer", `${control.id} reviewer acknowledgment recorded`, "Review-ready gaps and qualified records were accepted inside the demo after all prior prerequisites passed; this remains an invented implementation state.");
  render();
}

function resetDemo() {
  const currentView = state.view;
  state = createInitialState("default");
  state.view = currentView;
  render();
}

function exportAudit() {
  const payload = {
    schema: "synthetic-readiness-audit-v1",
    generatedBy: "offline portfolio demo",
    disclosure: "INDEPENDENT PORTFOLIO DEMO / SYNTHETIC DATA / NO AFFILIATION / NO PRODUCTION ACTION",
    conclusion: "operational implementation state only; not compliance",
    customer: fixture.customer,
    framework: fixture.framework,
    events: state.audit
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "synthetic-readiness-audit.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

document.addEventListener("click", event => {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.dataset.view) navigate(target.dataset.view);
  if (target.dataset.go) navigate(target.dataset.go);
  if (target.dataset.gapFilter) {
    state.gapFilter = target.dataset.gapFilter;
    render();
  }
  if (target.dataset.gapId) {
    state.selectedGapId = target.dataset.gapId;
    render();
  }
  if (target.dataset.evidenceId) {
    state.selectedEvidenceId = target.dataset.evidenceId;
    render();
  }
  if (target.dataset.openControl) {
    const control = controlById(target.dataset.openControl);
    state.selectedControlId = control.id;
    state.selectedEvidenceId = control.evidenceIds[0];
    navigate("evidence");
  }
  if (target.dataset.goAction) navigate("actions");
  if (target.dataset.goEvidence) {
    state.selectedEvidenceId = target.dataset.goEvidence;
    navigate("evidence");
  }
  if (target.dataset.advanceAction) advanceAction(target.dataset.advanceAction);
  if (target.dataset.selectControl) {
    state.selectedControlId = target.dataset.selectControl;
    state.lastCheckControlId = null;
    render();
  }
  if (target.dataset.goAcceptance) {
    state.selectedControlId = target.dataset.goAcceptance;
    state.lastCheckControlId = null;
    navigate("acceptance");
  }
  if (target.hasAttribute("data-run-checks")) runChecks();
  if (target.hasAttribute("data-acknowledge")) acknowledge();
  if (target.hasAttribute("data-reset-demo")) resetDemo();
  if (target.hasAttribute("data-export-audit")) exportAudit();
});

document.addEventListener("input", event => {
  if (event.target.id !== "gap-search") return;
  state.search = event.target.value;
  const cursor = event.target.selectionStart;
  render();
  const replacement = document.getElementById("gap-search");
  replacement.focus();
  replacement.setSelectionRange(cursor, cursor);
});

document.addEventListener("keydown", event => {
  if (event.target.matches("input, textarea, select") || event.altKey || event.ctrlKey || event.metaKey) return;
  const keyMap = { "1": "overview", "2": "gaps", "3": "evidence", "4": "actions", "5": "acceptance", "6": "audit" };
  if (keyMap[event.key]) navigate(keyMap[event.key]);
});

render();
window.scrollTo(0, 0);
window.addEventListener("load", () => window.scrollTo(0, 0), { once: true });
