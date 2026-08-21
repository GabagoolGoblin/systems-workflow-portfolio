"use strict";

(function contractLab() {
  const snapshot = window.API_LAB_SNAPSHOT;
  const report = snapshot.report;
  const contract = snapshot.contract;
  const run = snapshot.run;
  const viewOrder = ["overview", "exchange", "inbox", "quarantine", "gate", "audit"];
  const viewTitles = {
    overview: "Contract map",
    exchange: "Request / response",
    inbox: "Webhook inbox",
    quarantine: "Quarantine",
    gate: "Human gate",
    audit: "Audit receipt"
  };
  const query = new URLSearchParams(window.location.search);
  let activeView = viewOrder.includes(query.get("view")) ? query.get("view") : "overview";
  let selectedDeliveryId = report.deliveries.some((item) => item.delivery_id === query.get("delivery"))
    ? query.get("delivery")
    : "delivery_demo_005";
  let inboxFilter = "all";
  let inboxSearch = "";
  // Query parameters select views and fixture records only. They never advance
  // the human gate or prefill its acknowledgement controls.
  let gateToken = "";
  let gateAcknowledged = false;
  let promoted = false;

  const workspace = document.getElementById("workspace");
  const nav = document.getElementById("view-nav");
  const footerState = document.getElementById("footer-state");

  const fixtureById = new Map(run.deliveries.map((delivery) => [delivery.delivery_id, delivery]));
  const records = report.deliveries.map((result) => {
    const fixture = fixtureById.get(result.delivery_id);
    let payload = null;
    try {
      payload = JSON.parse(fixture.raw_body);
    } catch (_error) {
      payload = null;
    }
    return Object.freeze({ result, fixture, payload });
  });

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function append(parent, ...children) {
    parent.append(...children.filter(Boolean));
    return parent;
  }

  function stateMeta(state) {
    const labels = {
      ready_for_human: ["Ready for human", "ready"],
      suppressed_duplicate: ["Duplicate suppressed", "duplicate"],
      quarantined_signature: ["Signature quarantine", "quarantine"],
      quarantined_replay_window: ["Replay quarantine", "quarantine"],
      quarantined_schema_drift: ["Schema quarantine", "quarantine"],
      quarantined_header_contract: ["Header quarantine", "quarantine"],
      recovered_ready_for_human: ["Recovered · review-ready", "ready"],
      retry_scheduled: ["Retry scheduled", "retry"],
      awaiting_human: ["Awaiting human", "review"],
      simulated_promoted: ["Simulated promotion", "ready"],
      "personal-badge": ["Personal lab", "personal-badge"]
    };
    return labels[state] || [state.replaceAll("_", " "), "neutral"];
  }

  function badge(state, customLabel) {
    const [label, tone] = stateMeta(state);
    return element("span", `badge ${tone}`, customLabel || label);
  }

  function viewHeader(eyebrow, title, lede, actions) {
    const header = element("header", "view-header");
    const copy = element("div");
    append(copy, element("p", "eyebrow", eyebrow), element("h1", "", title), element("p", "lede", lede));
    header.append(copy);
    if (actions && actions.length) {
      const actionBar = element("div", "header-actions");
      actions.forEach((action) => {
        const button = element("button", action.primary ? "primary-action" : "secondary-action", action.label);
        button.type = "button";
        button.dataset.goView = action.view;
        actionBar.append(button);
      });
      header.append(actionBar);
    }
    return header;
  }

  function disclosure(text) {
    const card = element("div", "disclosure-card");
    card.setAttribute("role", "note");
    append(card, element("span", "disclosure-icon", "P"), element("div", "", text));
    return card;
  }

  function metric(label, value, note, icon) {
    const card = element("article", "metric");
    const top = element("div", "metric-top");
    append(top, element("span", "", label), element("span", "metric-icon", icon));
    append(card, top, element("strong", "", String(value)), element("small", "", note));
    return card;
  }

  function metrics(items) {
    const group = element("section", "metrics");
    group.setAttribute("aria-label", "Run summary");
    items.forEach((item) => group.append(metric(...item)));
    return group;
  }

  function panel(title, subtitle, body, trailing) {
    const card = element("section", "panel");
    const header = element("header", "panel-header");
    const copy = element("div");
    append(copy, element("h2", "", title), subtitle ? element("p", "", subtitle) : null);
    append(header, copy, trailing || null);
    append(card, header, body);
    return card;
  }

  function controlItem(title, detail, right) {
    const item = element("li");
    const copy = element("div");
    append(copy, element("strong", "", title), element("small", "", detail));
    append(item, element("span", "check", "✓"), copy, right || badge("ready_for_human", "Bounded"));
    return item;
  }

  function updateRoute() {
    const url = new URL(window.location.href);
    url.searchParams.set("view", activeView);
    if (activeView === "inbox" || activeView === "quarantine") url.searchParams.set("delivery", selectedDeliveryId);
    else url.searchParams.delete("delivery");
    url.searchParams.delete("scenario");
    window.history.replaceState(null, "", url);
  }

  function setView(view, focusWorkspace) {
    if (!viewOrder.includes(view)) return;
    activeView = view;
    updateRoute();
    render();
    if (focusWorkspace) workspace.focus({ preventScroll: true });
  }

  function renderOverview() {
    append(
      workspace,
      viewHeader(
        "Personal integration systems lab",
        "Make every boundary testable.",
        "A deterministic, offline simulation for request contracts, signed webhooks, bounded retry, quarantine, human promotion, and audit evidence, without claiming paid production API experience.",
        [{ label: "Inspect 429 recovery →", view: "exchange", primary: true }]
      ),
      disclosure("PERSONAL PROJECT ONLY: this original lab uses synthetic vendors, paths, tenants, keys, payloads, responses, and timestamps. It demonstrates implementation skill; it is not evidence of a production deployment."),
      metrics([
        ["Webhook deliveries", report.webhook_summary.total, "all synthetic", "↘"],
        ["Ready for a person", report.webhook_summary.states.ready_for_human, "never auto-promoted", "✓"],
        ["Quarantined", 4, "four distinct controls", "!"],
        ["Runtime calls", report.exchange.network_calls, "offline by construction", "∅"]
      ])
    );

    const flowBody = element("div", "panel-body");
    const flow = element("div", "flow-map");
    [
      ["01", "Contract", "Exact keys, types, and allowlisted path"],
      ["02", "Authenticate", "HMAC over timestamp + exact raw bytes"],
      ["03", "Bound", "Replay window and idempotency scope"],
      ["04", "Recover", "Virtual retry budget; no sleep"],
      ["05", "Promote", "Exact token + human acknowledgement"]
    ].forEach(([number, title, detail]) => {
      const step = element("article", "flow-step");
      append(step, element("span", "flow-number", number), element("h3", "", title), element("p", "", detail));
      flow.append(step);
    });
    flowBody.append(flow);

    const controls = element("ul", "control-list");
    controls.append(
      controlItem("Raw-byte HMAC", "SHA-256 compare_digest in Python", badge("ready_for_human", "Verified")),
      controlItem("Replay boundary", `${contract.replay_window_seconds}s fixed clock window`, badge("ready_for_human", "Closed")),
      controlItem("Idempotency suppression", "Accepted key is remembered in-run", badge("suppressed_duplicate", "1 suppressed")),
      controlItem("Retry budget", `${contract.retry_policy.max_retries} max · ${contract.retry_policy.cap_seconds}s cap`, badge("recovered_ready_for_human", "Recovered")),
      controlItem("Promotion authority", "Exact review token + explicit phrase", badge("awaiting_human"))
    );

    const layout = element("div", "layout-two");
    append(
      layout,
      panel("Integration control path", "Inbound and outbound boundaries share one review posture", flowBody, badge("ready_for_human", "Deterministic")),
      panel("Active controls", "What this local run actually exercises", append(element("div", "panel-body"), controls), badge("personal-badge", "Personal lab"))
    );
    workspace.append(layout);
  }

  function renderExchange() {
    const exchange = report.exchange;
    append(
      workspace,
      viewHeader(
        "Deterministic outbound simulation",
        "Request / response contract",
        "Three supplied responses are validated in memory. HTTP 429 produces a virtual schedule; no socket opens and no timer sleeps.",
        [{ label: "Open human gate →", view: "gate", primary: true }]
      ),
      disclosure("SIMULATION BOUNDARY: the endpoint is an allowlisted synthetic path, response attempts are fixture records, elapsed time is virtual, and the recovered 202 stops at review-ready."),
      metrics([
        ["Attempts", exchange.attempts.length, "fixture records", "#"],
        ["429 responses", 2, "bounded, not retried live", "↻"],
        ["Virtual delay", `${exchange.virtual_delay_total_seconds}s`, "2s + 4s schedule", "⌁"],
        ["Final response", exchange.final_status, "contract passed", "✓"]
      ])
    );

    const requestBody = element("div", "panel-body");
    const requestCode = element("pre", "code-block", JSON.stringify(run.exchange.body, null, 2));
    const headers = element("dl", "kv-grid");
    [
      ["Method / path", `${run.exchange.method} ${run.exchange.path}`],
      ["Correlation", run.exchange.headers["x-correlation-id"]],
      ["Idempotency", run.exchange.headers["idempotency-key"]],
      ["Body SHA-256", `${exchange.request_body_sha256.slice(0, 20)}…`]
    ].forEach(([key, value]) => append(headers, element("dt", "", key), element("dd", "", value)));
    append(requestBody, requestCode, headers);

    const attemptBody = element("div", "panel-body");
    const attempts = element("ol", "attempt-list");
    exchange.attempts.forEach((attempt) => {
      const item = element("li", "attempt-card");
      append(
        item,
        badge(attempt.status === 202 ? "ready_for_human" : "retry_scheduled", `Attempt ${attempt.attempt}`),
        element("strong", "", String(attempt.status)),
        element("p", "", attempt.status === 429 ? "Synthetic rate limit; response contract accepted." : "Accepted response schema and correlation echo passed."),
        element("small", "", attempt.delay_seconds ? `virtual retry +${attempt.delay_seconds}s` : "review-ready · no automatic write")
      );
      attempts.append(item);
    });
    attemptBody.append(attempts);
    const strip = element("div", "retry-strip");
    [
      ["Policy", "2 × 2ⁿ"],
      ["Server hints", "2s / 3s"],
      ["Chosen", "2s / 4s"],
      ["Hard cap", "8s"]
    ].forEach(([label, value]) => append(strip, append(element("div"), element("span", "", label), element("strong", "", value))));
    attemptBody.append(strip, element("div", "limit-note", "Recovery is bounded evidence, not delivery authority. A 202 response makes the candidate eligible for a person; it does not promote or write anything."));

    const layout = element("div", "layout-equal");
    append(
      layout,
      panel("Synthetic request", "Exact request and header contract", requestBody, badge("neutral", "No host")),
      panel("Response attempts", "429 → virtual schedule → 202", attemptBody, badge("recovered_ready_for_human"))
    );
    workspace.append(layout);
  }

  function filterRecord(record) {
    const state = record.result.state;
    const categoryMatch = inboxFilter === "all"
      || (inboxFilter === "ready" && state === "ready_for_human")
      || (inboxFilter === "quarantine" && state.startsWith("quarantined_"))
      || (inboxFilter === "duplicate" && state === "suppressed_duplicate");
    const haystack = [record.result.delivery_id, record.result.correlation_id, record.result.idempotency_key, state, record.result.event_id]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return categoryMatch && haystack.includes(inboxSearch.toLowerCase());
  }

  function deliveryDetail(record) {
    const card = element("section", "panel");
    const hero = element("div", "detail-hero");
    const eventTitle = record.payload && record.payload.event_id ? record.payload.event_id : record.result.delivery_id;
    append(hero, badge(record.result.state), element("h2", "", eventTitle), element("p", "", `${record.result.delivery_id} · ${record.result.correlation_id || "invalid correlation"}`));
    card.append(hero);

    const body = element("div", "panel-body");
    const facts = element("dl", "kv-grid");
    [
      ["HMAC", record.result.signature_valid ? "valid" : "failed / not evaluated"],
      ["Timestamp age", record.result.timestamp_age_seconds === null ? "not evaluated" : `${record.result.timestamp_age_seconds}s`],
      ["Idempotency", record.result.idempotency_key || "invalid"],
      ["Raw body hash", `${record.result.raw_body_sha256.slice(0, 20)}…`],
      ["Human eligible", record.result.human_eligible ? "yes" : "no"]
    ].forEach(([key, value]) => append(facts, element("dt", "", key), element("dd", "", value)));
    const reasons = element("ul", "reason-list");
    record.result.reason_codes.forEach((reason) => {
      const item = element("li");
      append(item, element("span", "reason-marker", record.result.human_eligible ? "✓" : "!"), element("span", "", reason.replaceAll("_", " ")));
      reasons.append(item);
    });
    append(body, facts, element("p", "panel-label", "Decision reasons"), reasons);
    card.append(body);
    return card;
  }

  function renderInbox() {
    const visible = records.filter(filterRecord);
    if (!visible.some((record) => record.result.delivery_id === selectedDeliveryId) && visible.length) {
      selectedDeliveryId = visible[0].result.delivery_id;
    }
    const selected = records.find((record) => record.result.delivery_id === selectedDeliveryId) || records[0];
    append(
      workspace,
      viewHeader(
        "Signed inbound fixtures",
        "Webhook inbox",
        "Exact raw bytes are authenticated before timestamp, duplicate, schema, and human-eligibility decisions are made.",
        [{ label: "Review quarantines →", view: "quarantine", primary: true }]
      ),
      disclosure("The HMAC key is deliberately named and stored as a synthetic public demo value. It is not a credential, and this inbox never listens on a port."),
      metrics([
        ["Delivered", 7, "synthetic fixtures", "↓"],
        ["Signature valid", 5, "before downstream checks", "⌁"],
        ["Ready", 2, "human review only", "✓"],
        ["Suppressed", 1, "idempotency duplicate", "≡"]
      ])
    );

    const listPanel = element("section", "panel");
    const toolbar = element("div", "toolbar");
    const filters = element("div", "filters");
    [
      ["all", "All 7"],
      ["ready", "Ready 2"],
      ["quarantine", "Quarantine 4"],
      ["duplicate", "Duplicate 1"]
    ].forEach(([id, label]) => {
      const button = element("button", "filter-button", label);
      button.type = "button";
      button.dataset.inboxFilter = id;
      button.setAttribute("aria-pressed", String(inboxFilter === id));
      filters.append(button);
    });
    const searchLabel = element("label", "search-label");
    searchLabel.setAttribute("aria-label", "Search webhook deliveries");
    const search = element("input");
    search.type = "search";
    search.value = inboxSearch;
    search.placeholder = "Search delivery or correlation";
    search.dataset.inboxSearch = "true";
    append(searchLabel, element("span", "", "⌕"), search);
    append(toolbar, filters, searchLabel);
    listPanel.append(toolbar);
    const list = element("div", "event-list");
    visible.forEach((record, index) => {
      const button = element("button", "event-row");
      button.type = "button";
      button.dataset.deliveryId = record.result.delivery_id;
      button.setAttribute("aria-pressed", String(record.result.delivery_id === selectedDeliveryId));
      const idCell = element("span");
      append(idCell, element("strong", "", record.result.delivery_id), element("small", "", record.result.event_id || "unparsed event"));
      const correlation = element("span");
      append(correlation, element("strong", "", record.result.correlation_id || "invalid"), element("small", "", record.result.idempotency_key || "invalid key"));
      const reasons = element("span");
      append(reasons, element("strong", "", record.result.reason_codes[0].replaceAll("_", " ")), element("small", "", `raw ${record.result.raw_body_sha256.slice(0, 12)}…`));
      append(button, element("span", "row-index", String(index + 1).padStart(2, "0")), idCell, correlation, reasons, badge(record.result.state));
      list.append(button);
    });
    if (!visible.length) list.append(element("p", "panel-body", "No deliveries match this local filter."));
    listPanel.append(list);

    const layout = element("div", "layout-two");
    append(layout, listPanel, deliveryDetail(selected));
    workspace.append(layout);
  }

  function quarantineRecovery(record) {
    const instructions = {
      quarantined_signature: "Reject this delivery. Obtain a new delivery signed over its exact timestamp and raw bytes; never bypass HMAC.",
      quarantined_replay_window: "Require a newly emitted event with a current timestamp. The demo has no replay override.",
      quarantined_schema_drift: "Version and map the changed field deliberately, update contract tests, then submit a new fixture for human review.",
      quarantined_header_contract: "Restore a valid correlation ID and exact header vocabulary before reevaluating a new delivery."
    };
    return instructions[record.result.state] || "No automated recovery is available.";
  }

  function renderQuarantine() {
    const quarantined = records.filter((record) => record.result.state.startsWith("quarantined_"));
    if (!quarantined.some((record) => record.result.delivery_id === selectedDeliveryId)) selectedDeliveryId = quarantined[2].result.delivery_id;
    const selected = quarantined.find((record) => record.result.delivery_id === selectedDeliveryId);
    append(
      workspace,
      viewHeader(
        "Fail-closed exception routing",
        "Quarantine",
        "Authenticated does not mean acceptable. Signature, time, header, and schema failures remain distinct, traceable states with bounded recovery instructions.",
        [{ label: "Inspect human gate →", view: "gate", primary: true }]
      ),
      disclosure("No quarantine can be edited into approval. Recovery requires a new synthetic delivery that passes the complete contract in a fresh evaluation."),
      metrics([
        ["Quarantined", 4, "no promotion path", "!"],
        ["Bad signature", 1, "HMAC mismatch", "⌁"],
        ["Replay / header", 2, "boundary failures", "◷"],
        ["Schema drift", 1, "unknown field isolated", "Δ"]
      ])
    );

    const grid = element("div", "quarantine-grid");
    quarantined.forEach((record) => {
      const button = element("button", "quarantine-card");
      button.type = "button";
      button.dataset.quarantineId = record.result.delivery_id;
      button.setAttribute("aria-pressed", String(record.result.delivery_id === selectedDeliveryId));
      append(
        button,
        badge(record.result.state),
        element("h3", "", record.result.delivery_id),
        element("p", "", quarantineRecovery(record)),
        element("code", "", record.result.reason_codes.join(" · "))
      );
      grid.append(button);
    });
    const gridBody = append(element("div", "panel-body"), grid);

    const detailBody = element("div", "panel-body");
    const factList = element("dl", "kv-grid");
    [
      ["Delivery", selected.result.delivery_id],
      ["Correlation", selected.result.correlation_id || "invalid / absent"],
      ["Signature", selected.result.signature_valid ? "valid" : "failed / not evaluated"],
      ["Timestamp age", selected.result.timestamp_age_seconds === null ? "not evaluated" : `${selected.result.timestamp_age_seconds}s`],
      ["Raw hash", `${selected.result.raw_body_sha256.slice(0, 20)}…`]
    ].forEach(([key, value]) => append(factList, element("dt", "", key), element("dd", "", value)));
    append(
      detailBody,
      badge(selected.result.state),
      factList,
      element("p", "panel-label", "Bounded recovery"),
      element("div", "limit-note", quarantineRecovery(selected)),
      element("p", "panel-label", "Raw synthetic body"),
      element("pre", "code-block", selected.fixture.raw_body)
    );

    const layout = element("div", "layout-two");
    append(
      layout,
      panel("Held deliveries", "Select a distinct failure contract", gridBody, badge("quarantined_signature", "4 held")),
      panel("Selected evidence", "Nothing is inferred or repaired in place", detailBody)
    );
    workspace.append(layout);
  }

  function gateChecklist() {
    const list = element("ul", "checklist");
    [
      ["Request schema and allowlisted path", "passed"],
      ["Correlation ID echoed across every response", "passed"],
      ["429 schedule stayed within retry budget", "2s · 4s"],
      ["Final 202 response contract", "passed"],
      ["Base hash-linked receipt", "verified"],
      ["Production endpoint / write connector", "absent"]
    ].forEach(([label, value]) => {
      const copy = element("span", "", label);
      append(list, append(element("li"), element("span", "check", "✓"), copy, badge("ready_for_human", value)));
    });
    return list;
  }

  function renderGate() {
    const gateState = promoted ? "simulated_promoted" : report.promotion_gate.state;
    append(
      workspace,
      viewHeader(
        "Explicit local authority boundary",
        "Human promotion gate",
        "Deterministic controls can make a candidate eligible. An exact visible review token plus a personal-project acknowledgement advances this browser-memory simulation; the token is a control-flow gate, not authentication.",
        [{ label: "Inspect receipt →", view: "audit", primary: false }]
      ),
      disclosure("PROMOTION IS SIMULATED ONLY: the visible review token is an acknowledgement/control-flow gate, not a secret or authentication. This screen changes browser memory and has no endpoint, credential, persistence, deployment action, tenant mutation, or production authority."),
      metrics([
        ["Prerequisites", "6/6", "scope-limited checks", "✓"],
        ["Review token", "Exact", "digest-derived", "#"],
        ["Acknowledgement", promoted ? "Recorded" : "Required", "explicit human step", "P"],
        ["Production writes", 0, "always false", "∅"]
      ])
    );

    const evidenceBody = element("div", "panel-body");
    const state = element("div", "gate-state");
    const stateCopy = element("div");
    append(
      stateCopy,
      element("strong", "", promoted ? "Simulated promotion recorded" : "Candidate is eligible for a human decision"),
      element("span", "", promoted ? "Browser-memory state only; base receipt preserved." : "Recovery stopped here after the 202 response contract passed.")
    );
    append(state, element("span", "check", "✓"), stateCopy, badge(gateState));
    append(evidenceBody, state, gateChecklist());

    const controlBody = element("div", "panel-body");
    if (promoted) {
      const success = element("div", "promotion-success");
      append(
        success,
        element("h3", "", "Simulated promotion recorded"),
        element("p", "", `Candidate ${report.promotion_gate.candidate_id} advanced in this browser tab only.`),
        element("p", "mono", `acknowledgement=${report.promotion_gate.required_acknowledgement}`),
        element("p", "mono", "production_write=false · persisted=false · network_calls=0")
      );
      append(controlBody, success, element("div", "limit-note", "The base audit receipt remains unchanged. Run the deterministic Python `promote` command with the exact token to produce a new verified promoted receipt on stdout."));
    } else {
      const controls = element("div", "gate-control");
      const tokenLabel = element("label");
      append(tokenLabel, element("strong", "", "Type the exact visible review token (not authentication)"), element("code", "mono", report.promotion_gate.confirm_token));
      const tokenInput = element("input");
      tokenInput.type = "text";
      tokenInput.autocomplete = "off";
      tokenInput.spellcheck = false;
      tokenInput.value = gateToken;
      tokenInput.dataset.gateToken = "true";
      tokenInput.setAttribute("aria-label", "Exact review token");
      tokenLabel.append(tokenInput);

      const ackLabel = element("label", "checkbox-row");
      const checkbox = element("input");
      checkbox.type = "checkbox";
      checkbox.checked = gateAcknowledged;
      checkbox.dataset.gateAck = "true";
      const ackCopy = element("span", "", `I acknowledge ${report.promotion_gate.required_acknowledgement}; this is not a production action.`);
      append(ackLabel, checkbox, ackCopy);

      const promote = element("button", "primary-action", "Record simulated promotion");
      promote.type = "button";
      promote.dataset.promote = "true";
      promote.disabled = !(gateToken === report.promotion_gate.confirm_token && gateAcknowledged);
      append(
        controls,
        tokenLabel,
        ackLabel,
        promote,
        element("p", "gate-help", "Blocked webhook deliveries remain quarantined. This decision applies only to the recovered synthetic API exchange candidate.")
      );
      controlBody.append(controls);
    }

    const layout = element("div", "gate-layout");
    append(
      layout,
      panel("Promotion prerequisites", "All deterministic checks are visible before authority", evidenceBody, badge("ready_for_human", "6 / 6")),
      panel("Human decision", "Exact token and explicit acknowledgement", controlBody, badge(gateState))
    );
    workspace.append(layout);
  }

  function renderAudit() {
    append(
      workspace,
      viewHeader(
        "Tamper-evident synthetic evidence",
        "Audit receipt",
        "Eleven exact events bind webhook decisions, virtual retry, response recovery, and the human gate to one deterministic receipt digest.",
        [{ label: "Return to contract map", view: "overview", primary: false }]
      ),
      disclosure("SHA-256 detects drift inside this local receipt; it is not a signature, external timestamp, immutable ledger, identity proof, compliance artifact, or production audit log."),
      metrics([
        ["Audit events", report.audit.events.length, "sequence-linked", "#"],
        ["Chain breaks", 0, "exact receipt verified", "✓"],
        ["Input digests", 2, "contract + run bytes", "⌁"],
        ["Production claims", 0, "personal project boundary", "P"]
      ])
    );

    const listBody = element("div", "panel-body");
    if (promoted) {
      listBody.append(element("div", "limit-note", "Browser promotion is intentionally not inserted into the base hash chain. The Python CLI can create a new promoted receipt on stdout after exact confirmation."));
    }
    const auditList = element("ol", "audit-list");
    report.audit.events.slice(-7).forEach((event) => {
      const copy = element("span");
      append(copy, element("strong", "", event.event_type.replaceAll("_", " ")), element("small", "", event.subject_id));
      const detail = element("span");
      const detailText = Object.entries(event.details).map(([key, value]) => `${key}=${Array.isArray(value) ? value.join("+") : value}`).join(" · ");
      append(detail, element("strong", "", detailText), element("small", "", `prev ${event.prev_hash.slice(0, 12)}…`));
      append(auditList, append(element("li"), element("span", "audit-seq", String(event.seq)), copy, detail, element("span", "audit-hash", `${event.event_hash.slice(0, 16)}…`)));
    });
    listBody.append(auditList);

    const receiptBody = element("div", "panel-body");
    const digest = element("div", "receipt-box");
    append(digest, element("p", "", "Receipt SHA-256"), element("code", "", report.receipt_digest));
    const chain = element("div", "receipt-box");
    append(chain, element("p", "", "Audit chain head"), element("code", "", report.audit.chain_head));
    const inputs = element("dl", "kv-grid");
    append(
      inputs,
      element("dt", "", "Contract bytes"), element("dd", "", `${report.source_digests.contract_sha256.slice(0, 22)}…`),
      element("dt", "", "Run bytes"), element("dd", "", `${report.source_digests.run_sha256.slice(0, 22)}…`),
      element("dt", "", "Synthetic"), element("dd", "", "true"),
      element("dt", "", "Production claim"), element("dd", "", "false")
    );
    append(
      receiptBody,
      digest,
      element("div", "", ""),
      chain,
      inputs,
      element("div", "limit-note", "Verify locally: python3 -B -m integration_lab verify artifacts/synthetic_receipt.json")
    );

    const layout = element("div", "layout-two");
    append(
      layout,
      panel("Recent chain events", "Last seven of eleven exact-current events", listBody, badge("ready_for_human", "Chain valid")),
      panel("Bound receipt", "Exact source digests and receipt identity", receiptBody, badge("personal-badge", "Personal lab"))
    );
    workspace.append(layout);
  }

  function render() {
    workspace.replaceChildren();
    nav.querySelectorAll("[data-view]").forEach((button) => {
      if (button.dataset.view === activeView) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    document.title = `${viewTitles[activeView]} | Contract Lab`;
    footerState.textContent = promoted
      ? "Browser-only simulated promotion · base receipt preserved"
      : `Base receipt · ${report.audit.events.length} hash-linked events`;
    if (activeView === "overview") renderOverview();
    if (activeView === "exchange") renderExchange();
    if (activeView === "inbox") renderInbox();
    if (activeView === "quarantine") renderQuarantine();
    if (activeView === "gate") renderGate();
    if (activeView === "audit") renderAudit();
  }

  nav.addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (button) setView(button.dataset.view, true);
  });

  workspace.addEventListener("click", (event) => {
    const viewButton = event.target.closest("[data-go-view]");
    if (viewButton) {
      setView(viewButton.dataset.goView, true);
      return;
    }
    const deliveryButton = event.target.closest("[data-delivery-id]");
    if (deliveryButton) {
      selectedDeliveryId = deliveryButton.dataset.deliveryId;
      updateRoute();
      render();
      return;
    }
    const quarantineButton = event.target.closest("[data-quarantine-id]");
    if (quarantineButton) {
      selectedDeliveryId = quarantineButton.dataset.quarantineId;
      updateRoute();
      render();
      return;
    }
    const filterButton = event.target.closest("[data-inbox-filter]");
    if (filterButton) {
      inboxFilter = filterButton.dataset.inboxFilter;
      render();
      return;
    }
    if (event.target.closest("[data-promote]")) {
      if (gateToken === report.promotion_gate.confirm_token && gateAcknowledged) {
        promoted = true;
        render();
      }
    }
  });

  workspace.addEventListener("input", (event) => {
    if (event.target.matches("[data-inbox-search]")) {
      inboxSearch = event.target.value;
      render();
      const replacement = workspace.querySelector("[data-inbox-search]");
      if (replacement) {
        replacement.focus();
        replacement.setSelectionRange(inboxSearch.length, inboxSearch.length);
      }
    }
    if (event.target.matches("[data-gate-token]")) {
      gateToken = event.target.value;
      const button = workspace.querySelector("[data-promote]");
      if (button) button.disabled = !(gateToken === report.promotion_gate.confirm_token && gateAcknowledged);
    }
  });

  workspace.addEventListener("change", (event) => {
    if (event.target.matches("[data-gate-ack]")) {
      gateAcknowledged = event.target.checked;
      const button = workspace.querySelector("[data-promote]");
      if (button) button.disabled = !(gateToken === report.promotion_gate.confirm_token && gateAcknowledged);
    }
  });

  document.getElementById("reset-demo").addEventListener("click", () => {
    activeView = "overview";
    selectedDeliveryId = "delivery_demo_005";
    inboxFilter = "all";
    inboxSearch = "";
    gateToken = "";
    gateAcknowledged = false;
    promoted = false;
    updateRoute();
    render();
  });

  document.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.target.matches("input")) return;
    const index = Number(event.key) - 1;
    if (index >= 0 && index < viewOrder.length) setView(viewOrder[index], true);
  });

  render();
})();
