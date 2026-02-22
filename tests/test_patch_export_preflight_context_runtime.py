import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_export_patch_requests_includes_preflight_context():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available in test environment")

    repo_root = Path(__file__).resolve().parents[1]
    index_html = repo_root / "ui" / "viewer" / "index.html"

    js = r"""
const fs = require('fs');

const src = fs.readFileSync(process.argv[1], 'utf8');

function extractFunction(name) {
  const needle = `function ${name}(`;
  const start = src.indexOf(needle);
  if (start < 0) throw new Error(`missing function: ${name}`);
  return extractBlock(start);
}

function extractBlock(start) {
  const open = src.indexOf('{', start);
  let depth = 0;
  let inString = false;
  let quote = '';
  let escaped = false;
  for (let i = open; i < src.length; i += 1) {
    const ch = src[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === quote) { inString = false; quote = ''; }
      continue;
    }
    if (ch === '"' || ch === "'" || ch === '`') { inString = true; quote = ch; continue; }
    if (ch === '{') depth += 1;
    else if (ch === '}') {
      depth -= 1;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error('unclosed function block');
}

const snippets = [
  extractFunction('renderIntentPreview'),
  extractFunction('generatePatchRequestId'),
  extractFunction('createPatchRequest'),
  extractFunction('getPatchRequest'),
  extractFunction('exportPatchRequestsForKiwi')
];

const vm = require('vm');
const ctx = {
  console,
  Date,
  Math,
  JSON,
  currentMode: 'admin',
  IDENTITY_CONTEXT: { tenant_id: 'tenant_1', division_id: 'division_1', dataset_id: 'dataset_demo' },
  CONDITION_TYPES: [{ value: 'OTHER', label: 'Other (specify)' }],
  ACTION_TYPES: [{ value: 'ADD_COMMENT', label: 'Add comment' }, { value: 'OTHER', label: 'Other (specify)' }],
  patchRequestsStore: { requests: [], loaded: true, selectedIds: [] },
  PATCH_REQUEST_STORE: { save() {} },
  savePatchRequests() { return true; }
};

vm.createContext(ctx);
vm.runInContext(snippets.join('\n\n'), ctx);

const req = ctx.createPatchRequest({
  author: 'Admin',
  author_role: 'admin',
  patch_kind: 'comment',
  target: 'preflight_resolution',
  sheet: 'Preflight',
  field: 'resolution_story',
  action_type: 'ADD_COMMENT',
  preflight_context: {
    source: 'preflight_test_lab',
    gate_color: 'YELLOW',
    findings: [{ section: 'opportunity_spine', code: 'OPP_CONTRACT_TYPE', status: 'review' }]
  }
});

const payload = JSON.parse(ctx.exportPatchRequestsForKiwi([req.request_id]));
const item = payload.requests && payload.requests[0] ? payload.requests[0] : null;
const ok = !!(item && item.preflight_context && item.preflight_context.gate_color === 'YELLOW');
console.log(JSON.stringify({ ok, has_preflight_context: !!(item && item.preflight_context), keys: item ? Object.keys(item) : [] }));
if (!ok) process.exit(1);
"""

    proc = subprocess.run(
        [node, "-e", js, str(index_html)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"node runtime assertion failed:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    parsed = json.loads(proc.stdout.strip().splitlines()[-1])
    assert parsed["ok"] is True
