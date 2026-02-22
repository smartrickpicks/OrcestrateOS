#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function extractFunction(source, name) {
  const needle = `function ${name}(`;
  const start = source.indexOf(needle);
  if (start < 0) throw new Error(`Function not found: ${name}`);
  const open = source.indexOf("{", start);
  if (open < 0) throw new Error(`Function body not found: ${name}`);
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(start, i + 1);
    }
  }
  throw new Error(`Unclosed function body: ${name}`);
}

function extractVarStatement(source, name) {
  const needle = `var ${name}`;
  const start = source.indexOf(needle);
  if (start < 0) throw new Error(`Variable not found: ${name}`);
  let depthCurly = 0, depthSquare = 0, depthParen = 0;
  let inString = false, quote = "", escaped = false;
  for (let i = start; i < source.length; i += 1) {
    const ch = source[i];
    if (inString) {
      if (escaped) { escaped = false; }
      else if (ch === "\\") { escaped = true; }
      else if (ch === quote) { inString = false; quote = ""; }
      continue;
    }
    if (ch === "'" || ch === '"' || ch === "`") { inString = true; quote = ch; continue; }
    if (ch === "{") depthCurly += 1;
    else if (ch === "}") depthCurly -= 1;
    else if (ch === "[") depthSquare += 1;
    else if (ch === "]") depthSquare -= 1;
    else if (ch === "(") depthParen += 1;
    else if (ch === ")") depthParen -= 1;
    else if (ch === ";" && depthCurly === 0 && depthSquare === 0 && depthParen === 0) {
      return source.slice(start, i + 1);
    }
  }
  throw new Error(`Unterminated variable statement: ${name}`);
}

function run() {
  const repoRoot = path.resolve(__dirname, "..");
  const uiPath = path.join(repoRoot, "ui", "viewer", "index.html");
  const outPath = path.join(repoRoot, "out", "v256_preflight_export_e2e_artifact.json");
  const source = fs.readFileSync(uiPath, "utf8");

  const snippets = [
    extractVarStatement(source, "PATCH_REQUESTS_STORAGE_KEY"),
    extractVarStatement(source, "PATCH_REQUEST_STATUSES"),
    extractVarStatement(source, "patchRequestsStore"),
    extractVarStatement(source, "STATUS_TRANSITIONS"),
    extractVarStatement(source, "CONDITION_TYPES"),
    extractVarStatement(source, "ACTION_TYPES"),
    extractFunction(source, "generatePatchRequestId"),
    extractFunction(source, "renderIntentPreview"),
    extractFunction(source, "canTransition"),
    extractFunction(source, "getAuditEventForTransition"),
    extractFunction(source, "createPatchRequest"),
    extractFunction(source, "savePatchRequests"),
    extractFunction(source, "getPatchRequest"),
    extractFunction(source, "updatePatchRequestStatus"),
    extractFunction(source, "submitPatchRequest"),
    extractFunction(source, "exportPatchRequestsForKiwi"),
  ];

  const context = {
    console,
    Date,
    JSON,
    Math,
    RegExp,
    String,
    Number,
    Object,
    Array,
    Boolean,
    parseInt,
    parseFloat,
    isNaN,
    undefined,
    null: null,
    IDENTITY_CONTEXT: {
      tenant_id: "tenant_test",
      division_id: "division_test",
      dataset_id: "dataset_test",
    },
    currentMode: "admin",
    _governedDecisions: {
      canPerformAction: () => true,
    },
    showToast: () => {},
    isDemoMode: () => false,
    localStorage: { getItem: () => null, setItem: () => {} },
    PATCH_REQUEST_STORE: { save: () => {}, get: () => null, list: () => [] },
    AuditTimeline: { emit: () => {} },
  };

  vm.createContext(context);
  vm.runInContext(snippets.join("\n\n"), context);

  const testPreflightContext = {
    source: "preflight_test_lab",
    record_key: "assign_CK-TEST_doc.pdf",
    submit_kind: "comment",
    captured_at_utc: "2026-02-21T00:00:00.000Z",
    gate_color: "YELLOW",
    health_score: 72,
    pending_findings: [
      { scope: "entity_resolution", code: "ER01", label: "Entity match", status: "warn", reason: "Low confidence", value: "55%" },
    ],
  };

  const created = context.createPatchRequest({
    author: "Admin",
    author_role: "admin",
    status: "Draft",
    patch_kind: "comment",
    target: "preflight_resolution",
    sheet: "Preflight",
    field: "resolution_story",
    condition_type: "OTHER",
    action_type: "ADD_COMMENT",
    severity: "warning",
    risk: "medium",
    because: "Analyst comment from Preflight Test Lab.",
    rationale: "Preflight gate: YELLOW. Findings: 1.",
    evidence_observation: "Open checks: Entity match [WARN]",
    evidence_expected: "Capture analyst note.",
    evidence_justification: "Preflight deterministic checks.",
    evidence_repro: "Open Test Lab, run analysis, submit.",
    preflight_context: testPreflightContext,
  });

  const requestId = created.request_id;
  const stored = context.getPatchRequest(requestId);
  const initialStatus = stored && stored.status;

  const submitted = context.submitPatchRequest(requestId, "Analyst", "analyst");

  const exportJson = context.exportPatchRequestsForKiwi([requestId]);
  const exported = JSON.parse(exportJson);
  const exportedReq = exported.requests && exported.requests[0];

  const correctionCtx = {
    source: "preflight_test_lab",
    record_key: "assign_CK-CORR_doc2.pdf",
    submit_kind: "correction",
    captured_at_utc: "2026-02-21T01:00:00.000Z",
    gate_color: "RED",
    health_score: 38,
    pending_findings: [
      { scope: "financials_readiness", code: "FR01", label: "Missing financials", status: "fail", reason: "No rate card", value: "" },
    ],
  };

  const corrReq = context.createPatchRequest({
    author: "Admin",
    author_role: "admin",
    status: "Draft",
    patch_kind: "correction",
    target: "preflight_resolution",
    sheet: "Preflight",
    field: "resolution_story",
    condition_type: "OTHER",
    action_type: "UPDATE_VALUE",
    severity: "blocking",
    risk: "high",
    because: "Analyst correction from Preflight Test Lab.",
    rationale: "Preflight gate: RED. Findings: 1.",
    evidence_observation: "Open checks: Missing financials [FAIL]",
    evidence_expected: "Apply corrections.",
    evidence_justification: "Preflight deterministic checks.",
    evidence_repro: "Open Test Lab, run analysis, submit correction.",
    preflight_context: correctionCtx,
  });

  const corrExportJson = context.exportPatchRequestsForKiwi([corrReq.request_id]);
  const corrExported = JSON.parse(corrExportJson);
  const corrExportedReq = corrExported.requests && corrExported.requests[0];

  const checks = {
    create_stores_preflight_context: !!(stored && stored.preflight_context),
    stored_context_has_pending_findings: !!(stored && stored.preflight_context && Array.isArray(stored.preflight_context.pending_findings) && stored.preflight_context.pending_findings.length === 1),
    stored_context_gate_color: !!(stored && stored.preflight_context && stored.preflight_context.gate_color === "YELLOW"),
    stored_context_health_score: !!(stored && stored.preflight_context && stored.preflight_context.health_score === 72),
    stored_patch_kind_comment: !!(stored && stored.patch_kind === "comment"),
    draft_status_correct: initialStatus === "Draft",
    submit_transitions_to_submitted: !!(submitted && submitted.status === "Submitted"),
    export_includes_preflight_context: !!(exportedReq && exportedReq.preflight_context),
    export_preflight_context_has_findings: !!(exportedReq && exportedReq.preflight_context && Array.isArray(exportedReq.preflight_context.pending_findings)),
    export_includes_patch_kind: !!(exportedReq && exportedReq.patch_kind === "comment"),
    export_includes_status: !!(exportedReq && exportedReq.status === "Submitted"),
    export_includes_evidence_pack: !!(exportedReq && exportedReq.evidence_pack),
    correction_export_patch_kind: !!(corrExportedReq && corrExportedReq.patch_kind === "correction"),
    correction_export_preflight_context: !!(corrExportedReq && corrExportedReq.preflight_context),
    correction_export_gate_color_red: !!(corrExportedReq && corrExportedReq.preflight_context && corrExportedReq.preflight_context.gate_color === "RED"),
    correction_export_health_score: !!(corrExportedReq && corrExportedReq.preflight_context && corrExportedReq.preflight_context.health_score === 38),
  };

  const summary = {
    run_id: "V2.56-PREFLIGHT-EXPORT-REGRESSION",
    generated_at_utc: new Date().toISOString(),
    source_file: uiPath,
    checks,
    all_passed: Object.values(checks).every(Boolean),
  };

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(summary, null, 2));

  if (summary.all_passed) {
    console.log("PASS: All " + Object.keys(checks).length + " preflight export checks passed.");
  } else {
    const failed = Object.entries(checks).filter(([, v]) => !v).map(([k]) => k);
    console.error("FAIL: " + failed.length + " check(s) failed: " + failed.join(", "));
  }

  process.stdout.write(outPath + "\n");
  if (!summary.all_passed) process.exitCode = 1;
}

run();
