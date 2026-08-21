(function () {
  'use strict';

  const base = window.EVALUATION_RELEASE_GATE_BASE;
  if (!base || base.schema_version !== 1) {
    throw new Error('Synthetic demo snapshot is unavailable.');
  }

  const titles = {
    overview: 'Release decision brief',
    review: 'Blind A/B case review',
    failures: 'Failure taxonomy',
    matrix: 'Slice regression matrix',
    gate: 'Release gate + receipt'
  };
  const sliceNames = {
    grounding: 'Grounding',
    instruction_adherence: 'Instruction adherence',
    safe_escalation: 'Safe escalation',
    structured_output_fidelity: 'Structured-output fidelity'
  };
  const sliceRationales = {
    grounding: 'better_grounding',
    instruction_adherence: 'instruction_boundary_preserved',
    safe_escalation: 'safe_escalation_preserved',
    structured_output_fidelity: 'handoff_contract_complete'
  };
  const failureDescriptions = {
    grounding: 'Claims outrun the invented evidence, erase unknowns, or manufacture a decision.',
    instruction_adherence: 'The response violates the declared shape, length, or non-commitment boundary.',
    safe_escalation: 'The response acts without authority instead of holding and naming the decision owner.',
    structured_output_fidelity: 'The response changes an exact schema or omits fields needed by the receiving owner.'
  };

  const state = {
    view: 'overview',
    filter: 'development',
    selectedCaseId: base.development_cases[0].case_id,
    holdoutLoaded: false,
    holdoutLoading: false,
    holdoutPromise: null,
    revealError: null,
    reviews: new Map(),
    exactInspected: new Set(),
    exportReceipt: null,
    receiptRevision: 0
  };

  const byId = (id) => document.getElementById(id);
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const add = (parent, ...children) => {
    children.forEach((child) => parent.appendChild(child));
    return parent;
  };

  function allCases() {
    const holdoutCases = state.holdoutLoaded ? window.EVALUATION_RELEASE_GATE_HOLDOUT.holdout_cases : [];
    return base.development_cases.concat(holdoutCases);
  }

  function caseById(caseId) {
    return allCases().find((item) => item.case_id === caseId);
  }

  function setView(view) {
    if (!Object.hasOwn(titles, view)) return;
    state.view = view;
    document.querySelectorAll('.view').forEach((node) => node.classList.toggle('active', node.id === `view-${view}`));
    document.querySelectorAll('.nav-item').forEach((node) => node.classList.toggle('active', node.dataset.view === view));
    byId('view-title').textContent = titles[view];
    if (view === 'review') renderReview();
    if (view === 'failures') renderFailures();
    if (view === 'matrix') renderMatrix();
    if (view === 'gate') renderGate();
  }

  function filteredCases() {
    if (state.filter === 'holdout' && !state.holdoutLoaded) return [];
    if (state.filter === 'all') return allCases();
    return allCases().filter((item) => item.partition === state.filter);
  }

  function renderCaseList() {
    const list = byId('case-list');
    list.replaceChildren();
    const cases = filteredCases();
    byId('case-count').textContent = state.filter === 'all' ? `${cases.length} available` : `${cases.length || 4} ${state.filter}`;
    if (!cases.length) {
      const note = make('div', 'notice', 'Details remain out of the base snapshot until explicit local reveal.');
      list.appendChild(note);
      return;
    }
    if (!cases.some((item) => item.case_id === state.selectedCaseId)) state.selectedCaseId = cases[0].case_id;
    cases.forEach((item) => {
      const button = make('button', `case-item${item.case_id === state.selectedCaseId ? ' active' : ''}`);
      button.type = 'button';
      button.dataset.caseId = item.case_id;
      const title = make('b', '', item.case_id);
      const subtitle = make('small', '', sliceNames[item.slice]);
      const status = make('i');
      const review = state.reviews.get(item.case_id);
      if (item.grader.type !== 'human_rubric' && state.exactInspected.has(item.case_id)) {
        status.className = Object.values(item.automatic_pass).every(Boolean) ? 'pass' : 'fail';
      } else if (review) {
        status.className = 'pass';
      }
      add(button, title, subtitle, status);
      button.addEventListener('click', () => {
        state.selectedCaseId = item.case_id;
        renderReview();
      });
      list.appendChild(button);
    });
  }

  function graderDescription(item) {
    if (item.grader.type === 'human_rubric') return item.grader.rubric_focus;
    if (item.grader.type === 'exact_json') return 'Strict JSON: recursive type identity, exact keys and cardinality, no duplicate keys, non-finite values, or trailing text.';
    return `Required: ${item.grader.required_phrases.join(', ')}. Forbidden: ${item.grader.forbidden_phrases.join(', ')}.`;
  }

  function scoreSelect(label, current) {
    const wrapper = make('div', 'score-control');
    const controlLabel = make('label', '', `Rubric score ${label}`);
    controlLabel.htmlFor = `score-${label.toLowerCase()}`;
    const select = make('select');
    select.id = `score-${label.toLowerCase()}`;
    select.dataset.scoreLabel = label;
    for (let score = 0; score <= 4; score += 1) {
      const option = make('option', '', `${score}: ${base.rubric.anchors[String(score)]}`);
      option.value = String(score);
      option.selected = current === score;
      select.appendChild(option);
    }
    add(wrapper, controlLabel, select);
    return wrapper;
  }

  function renderCaseDetail() {
    const target = byId('case-detail');
    target.replaceChildren();
    const item = caseById(state.selectedCaseId);
    if (!item) {
      const sealed = make('div', 'sealed-card');
      const icon = make('div', 'seal-icon', '◇');
      const title = make('h3', '', 'Four holdouts remain workflow-sealed');
      const copy = make('p', '', 'Their identifiers and hashes are visible, but task briefs, candidate outputs, grader contracts, and identity bindings are excluded from the base snapshot. Reveal loads a separate local static bundle. This is not a confidentiality guarantee.');
      const button = make('button', 'button primary', 'Reveal + evaluate locally');
      button.type = 'button';
      button.addEventListener('click', revealHoldout);
      add(sealed, icon, title, copy, button);
      target.appendChild(sealed);
      return;
    }

    const meta = make('div', 'case-meta');
    add(meta, make('code', '', item.case_id), make('span', 'chip neutral', sliceNames[item.slice].toUpperCase()), make('span', 'chip neutral', item.grader.type.replaceAll('_', ' ').toUpperCase()));
    if (item.hard_veto) meta.appendChild(make('span', 'chip hold', 'HARD VETO'));
    const heading = make('span', 'kicker', item.partition === 'holdout' ? 'Revealed synthetic holdout' : 'Synthetic development case');
    const brief = make('h2', 'case-brief', item.task_brief);
    const rubric = make('div', 'rubric-box', graderDescription(item));
    const responses = make('div', 'responses');
    const existing = state.reviews.get(item.case_id);
    ['A', 'B'].forEach((label) => {
      const card = make('article', 'response-card');
      const header = make('header');
      const labelNode = make('span', 'blind-label', label);
      const pill = make('span', 'grade-pill', item.grader.type === 'human_rubric' ? 'HUMAN SCORE' : 'NOT RUN');
      if (item.grader.type !== 'human_rubric' && state.exactInspected.has(item.case_id)) {
        pill.textContent = item.automatic_pass[label] ? 'EXACT PASS' : 'EXACT FAIL';
        pill.classList.add(item.automatic_pass[label] ? 'pass' : 'fail');
      }
      add(header, labelNode, pill);
      add(card, header, make('p', '', item.responses[label].output));
      if (item.grader.type === 'human_rubric') {
        const controls = make('div', 'score-controls');
        controls.appendChild(scoreSelect(label, existing ? existing.scores[label] : 2));
        card.appendChild(controls);
      }
      responses.appendChild(card);
    });
    const actions = make('div', 'review-actions');
    const hint = make('small', '', item.grader.type === 'human_rubric' ? 'Scores remain keyed to blind labels until gate calculation.' : 'Exact evaluation runs entirely in this static snapshot.');
    let action;
    if (item.grader.type === 'human_rubric') {
      action = make('button', 'button primary', existing ? 'Update blind judgment' : 'Record blind judgment');
      action.type = 'button';
      action.id = 'record-judgment';
      action.addEventListener('click', () => {
        const scoreA = Number(byId('score-a').value);
        const scoreB = Number(byId('score-b').value);
        const preference = scoreA === scoreB ? 'tie' : (scoreA > scoreB ? 'A' : 'B');
        state.reviews.set(item.case_id, {
          case_id: item.case_id,
          blind_preference: preference,
          rationale_code: preference === 'tie' ? 'tie_no_material_difference' : sliceRationales[item.slice],
          scores: { A: scoreA, B: scoreB }
        });
        invalidateReceipt();
        renderReview();
      });
    } else {
      action = make('button', 'button primary', state.exactInspected.has(item.case_id) ? 'Exact contract evaluated' : 'Run exact contract');
      action.type = 'button';
      action.id = 'run-exact';
      action.disabled = state.exactInspected.has(item.case_id);
      action.addEventListener('click', () => {
        state.exactInspected.add(item.case_id);
        invalidateReceipt();
        renderReview();
      });
    }
    add(actions, hint, action);
    add(target, meta, heading, brief, rubric, responses, actions);
  }

  function renderReview() {
    renderCaseList();
    renderCaseDetail();
  }

  function renderFailures() {
    const grid = byId('failure-grid');
    grid.replaceChildren();
    base.dimensions.forEach((slice, index) => {
      const available = allCases().filter((item) => item.slice === slice);
      const visibleCodes = available.map((item) => item.failure_code);
      const card = make('article', 'failure-card');
      const head = make('div', 'failure-head');
      add(head, make('span', 'failure-num', `0${index + 1} / 04`), make('span', 'chip neutral', `${available.length} AVAILABLE`));
      const title = make('h3', '', sliceNames[slice]);
      const copy = make('p', '', failureDescriptions[slice]);
      const codes = make('div', 'failure-codes');
      visibleCodes.forEach((code) => codes.appendChild(make('span', '', code)));
      if (!state.holdoutLoaded) codes.appendChild(make('span', '', 'HOLDOUT CODE SEALED'));
      add(card, head, title, copy, codes);
      grid.appendChild(card);
    });
  }

  function statusPills(cases) {
    const wrapper = make('div', 'matrix-stack');
    if (!cases.length) {
      wrapper.appendChild(make('span', 'cell-pill waiting', 'SEALED'));
      return wrapper;
    }
    cases.forEach((item) => {
      let status = 'waiting';
      let text = item.case_id;
      if (item.grader.type !== 'human_rubric') {
        const passes = Object.values(item.automatic_pass);
        status = passes.every(Boolean) ? 'pass' : 'fail';
      } else if (state.reviews.has(item.case_id)) {
        status = 'pass';
        text += ' REVIEWED';
      }
      wrapper.appendChild(make('span', `cell-pill ${status}`, text));
    });
    return wrapper;
  }

  function computeGate() {
    if (state.revealError) {
      return { outcome: 'PENDING', reason: `Holdout reveal failed closed: ${state.revealError}`, totals: null, regressions: [], hardVeto: [] };
    }
    if (!state.holdoutLoaded) {
      return { outcome: 'PENDING', reason: 'Holdout reveal and evaluation are incomplete.', totals: null, regressions: [], hardVeto: [] };
    }
    const payload = window.EVALUATION_RELEASE_GATE_HOLDOUT;
    const baseline = payload.candidate_roles.baseline;
    const challenger = payload.candidate_roles.challenger;
    const totals = { [baseline]: 0, [challenger]: 0 };
    const regressions = [];
    const hardVeto = [];
    const missing = [];
    allCases().forEach((item) => {
      const binding = payload.candidate_bindings[item.case_id];
      const scores = {};
      if (item.grader.type === 'human_rubric') {
        const review = state.reviews.get(item.case_id);
        if (!review) {
          missing.push(item.case_id);
          return;
        }
        ['A', 'B'].forEach((label) => { scores[binding[label]] = review.scores[label]; });
      } else {
        ['A', 'B'].forEach((label) => { scores[binding[label]] = item.automatic_pass[label] ? 4 : 0; });
      }
      totals[baseline] += scores[baseline];
      totals[challenger] += scores[challenger];
      if (scores[challenger] < scores[baseline]) regressions.push(item.case_id);
      const challengerLabel = binding.A === challenger ? 'A' : 'B';
      if (item.hard_veto && item.partition === 'holdout' && item.automatic_pass[challengerLabel] === false) hardVeto.push(item.case_id);
    });
    if (missing.length) return { outcome: 'PENDING', reason: `Human adjudication incomplete: ${missing.join(', ')}.`, totals, regressions, hardVeto, missing };
    if (totals[challenger] < totals[baseline] || regressions.length > base.gate_policy.maximum_case_regressions) {
      return { outcome: 'ROLLBACK', reason: 'The challenger exceeds the allowed regression limit.', totals, regressions, hardVeto, missing: [] };
    }
    if (hardVeto.length) return { outcome: 'HOLD', reason: `A synthetic holdout hard veto failed: ${hardVeto.join(', ')}. No action is authorized.`, totals, regressions, hardVeto, missing: [] };
    return { outcome: 'PENDING', reason: 'Review complete; this portfolio lab has no promotion authority.', totals, regressions, hardVeto, missing: [] };
  }

  function renderMatrix() {
    const body = byId('matrix-body');
    body.replaceChildren();
    const gate = computeGate();
    base.dimensions.forEach((slice) => {
      const cases = allCases().filter((item) => item.slice === slice);
      const dev = cases.filter((item) => item.partition === 'development');
      const holdout = cases.filter((item) => item.partition === 'holdout');
      const row = make('tr');
      const name = make('td', '', sliceNames[slice]);
      const devCell = make('td'); devCell.appendChild(statusPills(dev));
      const holdCell = make('td'); holdCell.appendChild(statusPills(holdout));
      const signal = make('td', '', gate.regressions.some((id) => cases.some((item) => item.case_id === id)) ? 'Candidate regression observed' : (state.holdoutLoaded ? 'No slice-level total regression' : 'Awaiting reveal'));
      const effect = make('td', '', gate.hardVeto.some((id) => cases.some((item) => item.case_id === id)) ? 'HARD VETO → HOLD' : (gate.outcome === 'ROLLBACK' ? 'REGRESSION → ROLLBACK' : 'No autonomous action'));
      add(row, name, devCell, holdCell, signal, effect);
      body.appendChild(row);
    });
  }

  function checkRow(done, title, detail) {
    const row = make('div', `check-item${done ? ' done' : ''}`);
    const left = make('div');
    add(left, make('span', 'check-icon', done ? '✓' : '·'), make('b', '', title));
    add(row, left, make('small', '', detail));
    return row;
  }

  function invalidateReceipt() {
    state.receiptRevision += 1;
    state.exportReceipt = null;
  }

  async function stableDigest(value) {
    const canonical = JSON.stringify(value, (_, item) => {
      if (!item || Array.isArray(item) || typeof item !== 'object') return item;
      return Object.keys(item).sort().reduce((result, key) => {
        result[key] = item[key];
        return result;
      }, {});
    });
    const bytes = new TextEncoder().encode(canonical);
    const digest = await window.crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  async function buildBrowserReceipt() {
    const gate = computeGate();
    const events = [];
    let previous = '0'.repeat(64);
    for (const [eventType, details] of [
      ['BASE_SNAPSHOT_VALIDATED', { development_cases: 8, synthetic: true }],
      ['HOLDOUT_REVEAL_STATE_RECORDED', { revealed: state.holdoutLoaded, bundle_sha256: base.holdout_bundle_sha256 }],
      ['BLIND_HUMAN_REVIEWS_RECORDED', { completed: state.reviews.size, identity_keys_in_reviewer_input: false }],
      ['NON_AUTHORITATIVE_GATE_RECORDED', { outcome: gate.outcome, action_authorized: false }]
    ]) {
      const event = { sequence: events.length + 1, event_type: eventType, details, previous_hash: previous };
      event.event_hash = await stableDigest(event);
      events.push(event);
      previous = event.event_hash;
    }
    const body = {
      schema_version: 1,
      receipt_type: 'browser_local_synthetic_review_state',
      boundary: base.boundary,
      digest_semantics: 'sha256_content_integrity_not_identity_approval_or_signature',
      holdout: {
        revealed: state.holdoutLoaded,
        bundle_sha256: base.holdout_bundle_sha256,
        seal_semantics: base.holdout_semantics,
        cryptographic_confidentiality_claimed: false
      },
      reviewer_inputs: Array.from(state.reviews.values()).sort((a, b) => a.case_id.localeCompare(b.case_id)),
      outcome: gate.outcome,
      reason: gate.reason,
      candidate_totals: gate.totals,
      regression_case_ids: gate.regressions,
      hard_veto_failure_case_ids: gate.hardVeto,
      allowed_outcomes: ['HOLD', 'ROLLBACK', 'PENDING'],
      action_authorized: false,
      runtime_network_used: false,
      inference_used: false,
      model_route_changed: false,
      audit_chain: events
    };
    return Object.assign({}, body, { receipt_sha256: await stableDigest(body) });
  }

  async function refreshReceipt() {
    const revision = state.receiptRevision;
    const button = byId('export-receipt');
    const digestNode = byId('receipt-digest');
    button.disabled = true;
    digestNode.textContent = 'digest / calculating';
    try {
      const receipt = await buildBrowserReceipt();
      if (revision !== state.receiptRevision) return;
      state.exportReceipt = receipt;
      digestNode.textContent = `sha256 / ${receipt.receipt_sha256}`;
      digestNode.title = receipt.receipt_sha256;
      button.disabled = false;
    } catch (_error) {
      digestNode.textContent = 'digest unavailable in this browser';
      button.disabled = true;
    }
  }

  function renderGate() {
    const gate = computeGate();
    const outcome = byId('gate-outcome');
    outcome.textContent = gate.outcome;
    outcome.className = `outcome-display ${gate.outcome.toLowerCase()}`;
    byId('gate-reason').textContent = gate.reason;
    const chip = byId('outcome-chip');
    chip.textContent = gate.outcome;
    chip.className = `chip ${gate.outcome.toLowerCase()}`;
    byId('seal-chip').textContent = state.holdoutLoaded ? 'HOLDOUT REVEALED LOCALLY' : 'HOLDOUT SEALED';
    const completeHuman = state.reviews.size === 4;
    const checks = [
      [true, 'Strict fixtures validated', '12 synthetic cases'],
      [true, 'Development graders available', '8 / 8 cases'],
      [state.holdoutLoaded, 'Holdout explicitly revealed', state.holdoutLoaded ? '4 / 4 evaluated' : 'workflow-sealed'],
      [completeHuman, 'Human rubric complete', `${state.reviews.size} / 4 reviewed`]
    ];
    const complete = checks.filter((item) => item[0]).length;
    byId('gate-progress').textContent = `${complete} / 4`;
    const checklist = byId('gate-checklist');
    checklist.replaceChildren(...checks.map((item) => checkRow(...item)));
    byId('reveal-holdout').disabled = state.holdoutLoaded || state.holdoutLoading;
    byId('reveal-holdout').textContent = state.holdoutLoaded ? 'Holdout revealed locally' : (state.holdoutLoading ? 'Loading local bundle…' : 'Reveal + evaluate holdout');
    byId('load-reference').disabled = state.holdoutLoading;
    byId('load-regression').disabled = state.holdoutLoading;
    byId('matrix-reference').disabled = state.holdoutLoading;
    invalidateReceipt();
    refreshReceipt();
  }

  function loadReferenceReviews() {
    if (!state.holdoutLoaded) {
      revealThen(loadReferenceReviews);
      return;
    }
    state.reviews.clear();
    window.EVALUATION_RELEASE_GATE_HOLDOUT.reference_adjudications.forEach((review) => state.reviews.set(review.case_id, JSON.parse(JSON.stringify(review))));
    invalidateReceipt();
    renderReview();
    renderMatrix();
    renderGate();
  }

  function loadRegressionReviews() {
    if (!state.holdoutLoaded) {
      revealThen(loadRegressionReviews);
      return;
    }
    state.reviews.clear();
    const payload = window.EVALUATION_RELEASE_GATE_HOLDOUT;
    base.development_cases.filter((item) => item.grader.type === 'human_rubric').forEach((item) => {
      const binding = payload.candidate_bindings[item.case_id];
      const baselineLabel = binding.A === payload.candidate_roles.baseline ? 'A' : 'B';
      const challengerLabel = baselineLabel === 'A' ? 'B' : 'A';
      state.reviews.set(item.case_id, {
        case_id: item.case_id,
        blind_preference: baselineLabel,
        rationale_code: sliceRationales[item.slice],
        scores: { A: baselineLabel === 'A' ? 4 : 0, B: challengerLabel === 'B' ? 0 : 4 }
      });
    });
    invalidateReceipt();
    renderReview();
    renderMatrix();
    renderGate();
  }

  function revealHoldout() {
    if (state.holdoutLoaded) return Promise.resolve();
    if (state.holdoutPromise) return state.holdoutPromise;
    state.revealError = null;
    state.holdoutLoading = true;
    renderGate();
    state.holdoutPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'data/holdout_snapshot.js';
      script.onload = async () => {
        try {
          const payload = window.EVALUATION_RELEASE_GATE_HOLDOUT;
          const payloadDigest = payload ? await stableDigest(payload) : '';
          if (!payload || payloadDigest !== base.holdout_payload_sha256 || payload.holdout_bundle_sha256 !== base.holdout_bundle_sha256 || payload.holdout_cases.length !== 4) {
            throw new Error('Local holdout payload integrity check failed.');
          }
          state.holdoutLoading = false;
          state.holdoutLoaded = true;
          state.revealError = null;
          state.exactInspected = new Set(allCases().filter((item) => item.grader.type !== 'human_rubric').map((item) => item.case_id));
          invalidateReceipt();
          renderReview();
          renderFailures();
          renderMatrix();
          renderGate();
          resolve();
        } catch (error) {
          state.holdoutLoading = false;
          state.holdoutLoaded = false;
          state.revealError = error instanceof Error ? error.message : 'Unknown local reveal error.';
          delete window.EVALUATION_RELEASE_GATE_HOLDOUT;
          script.remove();
          renderGate();
          reject(error);
        }
      };
      script.onerror = () => {
        const error = new Error('Unable to load the local holdout bundle.');
        state.holdoutLoading = false;
        state.holdoutLoaded = false;
        state.revealError = error.message;
        script.remove();
        renderGate();
        reject(error);
      };
      document.head.appendChild(script);
    });
    state.holdoutPromise = state.holdoutPromise.finally(() => {
      state.holdoutPromise = null;
    });
    return state.holdoutPromise;
  }

  function surfaceRevealFailure(error) {
    state.revealError = error instanceof Error ? error.message : 'Unknown local reveal error.';
    renderGate();
  }

  function revealThen(action) {
    revealHoldout().then(action).catch(surfaceRevealFailure);
  }

  function exportReceipt() {
    if (!state.exportReceipt) return;
    const blob = new Blob([`${JSON.stringify(state.exportReceipt, null, 2)}\n`], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `evaluation-release-gate-${state.exportReceipt.outcome.toLowerCase()}-synthetic-receipt.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
  document.querySelectorAll('[data-go]').forEach((button) => button.addEventListener('click', () => setView(button.dataset.go)));
  document.querySelectorAll('[data-filter]').forEach((button) => button.addEventListener('click', () => {
    state.filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach((item) => item.classList.toggle('active', item.dataset.filter === state.filter));
    if (state.filter === 'holdout' && !state.holdoutLoaded) state.selectedCaseId = null;
    renderReview();
  }));
  byId('reveal-holdout').addEventListener('click', () => revealHoldout().catch(surfaceRevealFailure));
  byId('load-reference').addEventListener('click', loadReferenceReviews);
  byId('load-regression').addEventListener('click', loadRegressionReviews);
  byId('matrix-reference').addEventListener('click', loadReferenceReviews);
  byId('export-receipt').addEventListener('click', exportReceipt);

  renderFailures();
  renderMatrix();
  renderGate();
})();
