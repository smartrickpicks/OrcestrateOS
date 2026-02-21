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
    const ch = source[i];
    if (ch === "{") depth += 1;
    if (ch === "}") {
      depth -= 1;
      if (depth === 0) {
        return source.slice(start, i + 1);
      }
    }
  }
  throw new Error(`Unclosed function body: ${name}`);
}

function extractVarStatement(source, name) {
  const needle = `var ${name}`;
  const start = source.indexOf(needle);
  if (start < 0) throw new Error(`Variable not found: ${name}`);
  let depthCurly = 0;
  let depthSquare = 0;
  let depthParen = 0;
  let inString = false;
  let quote = "";
  let escaped = false;
  for (let i = start; i < source.length; i += 1) {
    const ch = source[i];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (ch === "\\") {
        escaped = true;
      } else if (ch === quote) {
        inString = false;
        quote = "";
      }
      continue;
    }
    if (ch === "'" || ch === '"' || ch === "`") {
      inString = true;
      quote = ch;
      continue;
    }
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
  const outPath = path.join(repoRoot, "out", "v256_export_drive_e2e_artifact.json");
  const source = fs.readFileSync(uiPath, "utf8");

  const snippets = [
    extractVarStatement(source, "EXPORT_STATUS_ENUM"),
    extractVarStatement(source, "EXPORT_FINAL_STATES"),
    extractVarStatement(source, "EXPORT_CELL_FILLS"),
    extractVarStatement(source, "EXPORT_STATE_PRIORITY"),
    extractFunction(source, "_normalizeExportStatus"),
    extractFunction(source, "_resolveExportStatus"),
    extractFunction(source, "_buildExportFilename"),
    extractFunction(source, "_applyCellStylesToSheet"),
    extractFunction(source, "buildMetadataSheet"),
    extractFunction(source, "buildAuditLogSheet"),
    extractFunction(source, "_buildExportWorkbook"),
  ];

  const fnHandleExportClean = extractFunction(source, "handleExportClean");
  const fnHandleExportFull = extractFunction(source, "handleExportFull");
  const fnHandleSaveToDrive = extractFunction(source, "handleSaveToDrive");

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
    IDENTITY_CONTEXT: {
      batch_id: "Batch 001",
      dataset_id: "dataset_demo",
      workspace_id: "ws_demo",
      tenant_id: "tenant_1",
      division_id: "division_1",
    },
    workbook: {
      order: ["Accounts"],
      activeSheet: "Accounts",
      sheets: {
        Accounts: {
          headers: ["contract_key", "status"],
          rows: [{ contract_key: "CK-001", status: "Corrected Value" }],
        },
      },
    },
    getDataSheets: () => ["Accounts"],
    getMetaSheets: () => [],
    getTotalRecordCount: () => 1,
    getCurrentUserName: () => "Jane Analyst",
    getCurrentRole: () => "verifier",
    _getWorkspaceId: () => "ws_demo",
    _getFieldState: () => "",
    normalizeFieldKey: (v) => String(v || ""),
    localStorage: { getItem: () => "" },
    window: { _gridVerifiedCells: {} },
    PATCH_REQUEST_STORE: { list: () => [] },
    RFI_STORE: { list: () => [] },
    changeMap: { changes: {} },
    signalStore: { stats: { total: 0, by_type: {} }, signals_by_cell: {} },
    AuditTimeline: {
      _memCache: [
        {
          event_id: "evt_1",
          event_type: "FIELD_UPDATED",
          actor_id: "usr_1",
          actor_role: "analyst",
          timestamp_iso: "2026-02-18T16:00:00Z",
          dataset_id: "dataset_demo",
          file_id: "Accounts",
          record_id: "CK-001",
          field_key: "status",
          patch_request_id: "pr_1",
          before_value: "Old",
          after_value: "Corrected Value",
          metadata: { source: "test" },
        },
      ],
    },
    buildChangeLogSheet: () => null,
    buildRFISheet: () => null,
    buildSignalsSummarySheet: () => null,
    XLSX: {
      utils: {
        book_new: () => ({ SheetNames: [], Sheets: {} }),
        aoa_to_sheet: (rows) => ({ __rows: rows }),
        book_append_sheet: (wb, ws, name) => {
          wb.SheetNames.push(name);
          wb.Sheets[name] = ws;
        },
        encode_cell: ({ r, c }) => `R${r}C${c}`,
      },
    },
  };

  vm.createContext(context);
  vm.runInContext(snippets.join("\n\n"), context);

  const wbExport = context._buildExportWorkbook({ full: false });
  const wbExportFull = context._buildExportWorkbook({ full: true });
  const builtFileName = context._buildExportFilename("Batch 001", "in progress");

  const exportRows = wbExport.Sheets.Accounts.__rows;
  const exportHeader = exportRows[0];
  const statusColumn = exportHeader.indexOf("status");
  const correctedValue = exportRows[1][statusColumn];

  const govRows = wbExportFull.Sheets.GOV_META.__rows;
  const auditRows = wbExportFull.Sheets.Audit_Log.__rows;
  const govStatusRow = govRows.find((row) => row[0] === "export_status");
  const auditHeader = auditRows[0] || [];

  const checks = {
    export_corrected_values_persist: correctedValue === "Corrected Value",
    export_has_no_full_audit_sheets: !wbExport.SheetNames.includes("GOV_META") && !wbExport.SheetNames.includes("Audit_Log"),
    export_full_includes_gov_meta: wbExportFull.SheetNames.includes("GOV_META"),
    export_full_includes_orchestrate_meta: wbExportFull.SheetNames.includes("_orchestrate_meta"),
    export_full_includes_audit_log: wbExportFull.SheetNames.includes("Audit_Log"),
    export_full_gov_meta_status_normalized: !!govStatusRow && govStatusRow[1] === "VERIFIER_DONE",
    export_full_audit_header_stable:
      JSON.stringify(auditHeader) ===
      JSON.stringify([
        "event_id",
        "event_type",
        "actor_id",
        "actor_role",
        "timestamp_iso",
        "dataset_id",
        "file_id",
        "record_id",
        "field_key",
        "patch_request_id",
        "before_value",
        "after_value",
        "metadata",
      ]),
    export_filename_convention:
      /^Batch_001__IN_PROGRESS_ANALYST__\d{4}-\d{2}-\d{2}_\d{2}-\d{2}__ws_demo\.xlsx$/.test(builtFileName),
    save_to_drive_uses_full_workbook: fnHandleSaveToDrive.includes("_buildExportWorkbook({ full: true })"),
    save_to_drive_posts_drive_save_endpoint: fnHandleSaveToDrive.includes("/api/v2.5/workspaces/") && fnHandleSaveToDrive.includes("/drive/save"),
    export_action_wires_clean_mode: fnHandleExportClean.includes("_exportToFile({ full: false })"),
    export_full_action_wires_full_mode: fnHandleExportFull.includes("_exportToFile({ full: true })"),
  };

  const summary = {
    run_id: "V2.56-EXPORT-DRIVE-E2E",
    generated_at_utc: new Date().toISOString(),
    source_file: uiPath,
    checks,
    all_passed: Object.values(checks).every(Boolean),
  };

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(summary, null, 2));
  process.stdout.write(`${outPath}\n`);
  if (!summary.all_passed) process.exitCode = 1;
}

run();
