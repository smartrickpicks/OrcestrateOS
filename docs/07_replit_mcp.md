# 07 — Replit MCP (Operator Guide)

## Purpose and Scope
This document explains how to use Replit MCP (Model Context Protocol) with this repository to:
- edit/add files safely, and
- run the offline governance preview commands.

Scope-locked: MCP here is an operator surface only. It does not add runtime execution, external APIs, credentials, or prompts. All workflows remain offline and deterministic.

---

## What MCP Is Used For in This Repo
- File operations: open, edit, create documentation and config files in a Replit workspace.
- Commands: run local offline scripts (validate_config.py, run_local.py) the same way you would locally.
- Determinism: identical inputs produce identical outputs; no network calls are required.

---

## Install Link Format
Use Replit’s integration link format with a base64-encoded JSON payload:

https://replit.com/integrations?mcp={BASE64_ENCODED_JSON}

Payload schema (keys must be stable for deterministic diffs):
```
{
  "displayName": "<string>",
  "baseUrl": "<string>",
  "headers": [
    { "key": "<string>", "value": "<string>" }
  ]
}
```
Notes:
- `headers` is optional. If you need it, use placeholder values only. Do not include secrets in this repo.

Example placeholder (do not hardcode; replace locally as needed):
```
{
  "displayName": "Kiwi Semantic Control Board",
  "baseUrl": "https://YOUR_REPLIT_DEPLOYMENT_URL/mcp",
  "headers": [
    { "key": "Authorization", "value": "Bearer YOUR_TOKEN_PLACEHOLDER" }
  ]
}
```

---

## How to Generate the Payload Locally
Always serialize JSON with sorted keys and compact separators to ensure deterministic base64 output.

Python (one-liner):
```
python3 -c 'import json,base64; p={"displayName":"X","baseUrl":"https://example.com/mcp"}; s=json.dumps(p,sort_keys=True,separators=(",",":")); print(base64.b64encode(s.encode()).decode())'
```

Node (one-liner):
```
node -e 'const p={displayName:"X",baseUrl:"https://example.com/mcp"}; const s=JSON.stringify(p,Object.keys(p).sort()); console.log(Buffer.from(s,"utf8").toString("base64"))'
```

Repo tool (recommended): scripts/mcp_link_gen.py
- Deterministically prints ENCODED payload, full LINK, and BADGE_MARKDOWN using the Replit badge image.
- Example:
```
python3 scripts/mcp_link_gen.py \
  --display-name "Kiwi Semantic Control Board" \
  --base-url "https://YOUR_REPLIT_DEPLOYMENT_URL/mcp" \
  --caption "Add to Replit" \
  --header "Authorization: Bearer YOUR_TOKEN_PLACEHOLDER"
```

Badge output format (example):
```
BADGE_MARKDOWN=[![Add to Replit](https://replit.com/badge?caption=Add%20to%20Replit)](https://replit.com/integrations?mcp=...)
```
Note: Keep captions concise (recommended ≤ 30 characters) for readability.

---

## No Secrets Policy
- Do not commit real tokens, credentials, or private endpoints.
- If a header is required, use placeholders in documentation and local generation.
- Validate that headers are scrubbed before sharing links.

---

## MCP + Smoke Flow (Deterministic)
Checklist:
1) Make helper scripts executable (optional, improves UX):
```
chmod +x scripts/mcp_link_gen.py scripts/replit_smoke.sh
```
2) Install MCP in Replit using the generated link.
3) Open this repo in Replit.
4) Run the smoke script:
```
bash scripts/replit_smoke.sh
```
5) Verify output:
- Confirm out/sf_packet.preview.json exists
- Compare with examples/expected_outputs/sf_packet.example.json

Reference:
- .replit contains an equivalent one-button run command.
- All operations remain offline and deterministic.
