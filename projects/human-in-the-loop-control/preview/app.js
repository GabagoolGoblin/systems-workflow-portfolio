"use strict";

const identifierCache = Object.freeze({
  "100000000011": "7001001",
  "100000000028": "7001002",
  "100000000035": "7001003",
});

const originalRows = Object.freeze([
  Object.freeze({ requestId: "LAB-REQ-001", barcode: "100000000011", item: "Citrus Sparkler", current: "2.49", requested: "2.69" }),
  Object.freeze({ requestId: "LAB-REQ-002", barcode: "100000000028", item: "Berry Iced Tea", current: "2.79", requested: "2.99" }),
  Object.freeze({ requestId: "LAB-REQ-003", barcode: "100000000035", item: "Vanilla Cold Brew", current: "3.89", requested: "4.19" }),
  Object.freeze({ requestId: "LAB-REQ-004", barcode: "100000000042", item: "Ginger Lime Soda", current: "2.59", requested: "2.79" }),
  Object.freeze({ requestId: "LAB-REQ-005", barcode: "100000000011", item: "Citrus Sparkler", current: "2.49", requested: "2.69" }),
]);

let rows;
let phase;
let audit;

function resetState() {
  rows = originalRows.map(row => ({ ...row, identifier: "", status: "Pending", staged: "", reread: "", duplicate: false }));
  phase = "pending";
  audit = [{ label: "Synthetic batch loaded; no network or external write occurred." }];
}

function escapeHTML(value) {
  return String(value).replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
}

function addAudit(label) {
  audit.push({ label });
}

function holdDuplicateSubmissions() {
  const seen = new Set();
  rows.forEach(row => {
    row.duplicate = seen.has(row.barcode);
    seen.add(row.barcode);
    if (row.duplicate) {
      row.identifier = "";
      row.staged = "";
      row.reread = "";
      row.status = "Held: duplicate barcode submission";
    }
  });
}

function resolveCache() {
  if (phase !== "pending") return;
  holdDuplicateSubmissions();
  rows.forEach(row => {
    if (row.duplicate) return;
    row.identifier = identifierCache[row.barcode] || "";
    row.status = row.identifier ? "Cache hit" : "Held for manual lookup";
  });
  phase = "resolved";
  addAudit("Cache resolved 3 known identifiers; 1 unknown and 1 duplicate submission remained held.");
  render();
}

function validateHeld() {
  if (phase !== "resolved") return;
  holdDuplicateSubmissions();
  const held = rows.find(row => !row.identifier && !row.duplicate);
  if (!held) return;
  held.identifier = "7001999";
  held.status = "Manually validated";
  phase = "validated";
  addAudit("Human supplied one invented identifier mapping; the hold was resolved locally.");
  render();
}

function stageValues() {
  if (phase !== "validated") return;
  holdDuplicateSubmissions();
  const eligible = rows.filter(row => !row.duplicate);
  if (eligible.some(row => !row.identifier)) return;
  eligible.forEach(row => { row.staged = row.requested; row.status = "Staged, not saved"; });
  phase = "staged";
  addAudit("Four eligible values were staged in memory; the duplicate submission remained held.");
  render();
}

function verifyValues() {
  if (phase !== "staged") return;
  holdDuplicateSubmissions();
  const mismatch = document.querySelector("#mismatch").checked;
  const eligible = rows.filter(row => !row.duplicate);
  if (eligible.some(row => !row.staged)) return;
  eligible.forEach((row, index) => {
    row.reread = mismatch && index === 1 ? "999.99" : row.staged;
    row.status = row.reread === row.requested ? "Verified, awaiting approval" : "Held: reread mismatch";
  });
  phase = mismatch ? "blocked" : "verified";
  addAudit(mismatch ? "Reread mismatch detected; the whole batch and human save stayed blocked." : "Every reread matched; the batch awaits explicit human approval.");
  render();
}

function approveSave() {
  if (phase !== "verified") return;
  holdDuplicateSubmissions();
  const eligible = rows.filter(row => !row.duplicate);
  if (eligible.some(row => row.status !== "Verified, awaiting approval")) return;
  eligible.forEach(row => { row.current = row.staged; row.status = "Saved after human approval (lab)"; });
  phase = "approved";
  addAudit("A person approved the verified synthetic values; only in-memory demo state changed.");
  render();
}

function resetDemo() {
  resetState();
  document.querySelector("#mismatch").checked = false;
  render();
}

function statusClass(status) {
  if (status.includes("Held")) return "hold";
  if (status.includes("Verified") || status.includes("Saved") || status.includes("validated") || status.includes("Cache hit")) return "pass";
  return "";
}

function renderRows() {
  document.querySelector("#rows").innerHTML = rows.map(row => `<tr data-request-id="${escapeHTML(row.requestId)}">
    <td>${escapeHTML(row.requestId)}</td>
    <td>${escapeHTML(row.barcode)}</td>
    <td>${escapeHTML(row.item)}</td>
    <td>$${escapeHTML(row.current)}</td>
    <td>$${escapeHTML(row.requested)}</td>
    <td>${escapeHTML(row.identifier || "HELD")}</td>
    <td><span class="status ${statusClass(row.status)}">${escapeHTML(row.status)}</span></td>
  </tr>`).join("");
}

function renderFlow() {
  const completed = {
    resolve: phase !== "pending",
    validate: ["validated", "staged", "verified", "blocked", "approved"].includes(phase),
    stage: ["staged", "verified", "blocked", "approved"].includes(phase),
    verify: ["verified", "blocked", "approved"].includes(phase),
    approve: phase === "approved",
  };
  document.querySelectorAll("[data-step]").forEach(item => {
    item.classList.toggle("complete", completed[item.dataset.step]);
    item.classList.toggle("blocked", item.dataset.step === "verify" && phase === "blocked");
  });
  document.querySelector('[data-action="resolve"]').disabled = phase !== "pending";
  document.querySelector('[data-action="validate"]').disabled = phase !== "resolved";
  document.querySelector('[data-action="stage"]').disabled = phase !== "validated";
  document.querySelector('[data-action="verify"]').disabled = phase !== "staged";
  document.querySelector('[data-action="approve"]').disabled = phase !== "verified";
}

function renderMetrics() {
  const resolved = rows.filter(row => row.identifier).length;
  const held = rows.filter(row => row.status.includes("Held")).length;
  const gate = phase === "approved" ? "APPROVED" : phase === "verified" ? "HUMAN" : "STOPPED";
  const detail = phase === "approved" ? "synthetic save recorded" : phase === "verified" ? "approval required" : phase === "blocked" ? "reread mismatch" : "awaiting controls";
  document.querySelector("#metric-resolved").textContent = String(resolved);
  document.querySelector("#metric-held").textContent = String(held);
  document.querySelector("#metric-gate").textContent = gate;
  document.querySelector("#metric-gate-detail").textContent = detail;
  document.querySelector("#phase-pill").textContent = phase.toUpperCase();
}

function renderAudit() {
  document.querySelector("#audit").innerHTML = audit.map((entry, index) => `<li><time>DEMO-${String(index + 1).padStart(2, "0")}</time><span>${escapeHTML(entry.label)}</span></li>`).join("");
}

function render() {
  renderRows();
  renderFlow();
  renderMetrics();
  renderAudit();
}

document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => ({
  resolve: resolveCache,
  validate: validateHeld,
  stage: stageValues,
  verify: verifyValues,
  approve: approveSave,
  reset: resetDemo,
})[button.dataset.action]()));

resetState();
render();
