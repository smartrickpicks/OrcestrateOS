# INTERFACES (Scope-Locked)

This document defines the offline, deterministic interfaces used by the Kiwi Semantic Control Board. No runtime, no APIs, no credentials.

---

## config_pack.base.json
Producer: Kiwi Control Board
Consumer: Offline preview tools (local_runner)

Required
- version: string (e.g., "v0.1.0")
- metadata: object
  - purpose: string
  - scope_lock: string
  - join_strategy: ["contract_key", "file_url", "file_name"]
  - determinism: string
  - created: YYYY-MM-DD
  - notes: string
- salesforce_rules: { rules: [] }
- qa_rules: { rules: [] }
- resolver_rules: { rules: [] }

Optional
- deprecated_rules: []

Example
```
{
  "version": "v0.1.0",
  "metadata": {
    "purpose": "Semantic control plane base configuration.",
    "scope_lock": "No runtime, no APIs, no credentials.",
    "join_strategy": ["contract_key", "file_url", "file_name"],
    "determinism": "Offline preview only.",
    "created": "2026-01-29",
    "notes": "Operator-first; synthetic examples."
  },
  "salesforce_rules": { "rules": [] },
  "qa_rules": { "rules": [] },
  "resolver_rules": { "rules": [] },
  "deprecated_rules": []
}
```

---

## config_pack.patch.json
Producer: Kiwi Control Board
Consumer: Reviewers, Offline preview

Required
- base_version: string
- changes: array of change objects

Optional
- rationale: string
- author: string

Change Objects (current)
- add_rule (target: "salesforce_rules")
  - rule: { rule_id, description, when, then[] }
- deprecate_rule (target: "salesforce_rules")
  - rule_id: string
  - reason: string

Rule Schema
- rule_id: string
- description: string
- when: { sheet: string, field: string, operator: IN|EQ|NEQ|CONTAINS|EXISTS|NOT_EXISTS, value?: string|[string] }
- then: [ { action: REQUIRE_BLANK|REQUIRE_PRESENT|SET_VALUE, sheet: string, field: string, severity: info|warning|blocking, proposed_value?: any } ]

---

## standardized_dataset (sheeted format)
Producer: Upstream normalization (example-only here)
Consumer: Offline Preview Engine

Shape
```
{
  "standardized_dataset": {
    "sheets": {
      "accounts": {
        "headers": ["file_name", "file_url", "account_name", "subtype", ...],
        "rows": [ { "file_name": "...", "file_url": "...", "subtype": "...", ... } ]
      },
      "catalog": {
        "headers": ["file_name", "file_url", "artist_name", ...],
        "rows": [ { "file_name": "...", "artist_name": "...", ... } ]
      }
    }
  }
}
```
Notes
- Join strategy must be respected across sheets: primary contract_key; fallback file_url; last resort file_name.
- Additional fields are allowed if they do not contradict the canonical headers.

---

## sf_packet (preview)
Producer: Offline Preview Engine (local_runner)
Consumer: Operators/Reviewers

Required Keys
- sf_summary: { contracts, blocked, needs_review, ready }
- sf_contract_results: [ { contract_key|null, file_name|null, file_url|null, detected_subtype: { value|null, confidence|null }, sf_contract_status: READY|NEEDS_REVIEW|BLOCKED, notes|null } ]
- sf_field_actions: [ { contract_key|null, file_name|null, file_url|null, sheet, field, action: blank|format_fix, proposed_value|null, reason_category, reason_text, severity } ]
- sf_issues: [ { contract_key|null, sheet, field, issue_type, severity, details, suggested_routing|null } ]
- sf_manual_review_queue: [ { contract_key|null, severity, reason } ]
- sf_change_log: [ { timestamp|null, agent: "salesforce_agent_preview", sheet, field, old_value, new_value, reason_category, severity, notes } ]
- sf_meta: { ruleset_version: string }

Determinism
- Outputs must be stably ordered by join keys and field names to ensure reproducible diffs.

---

## Join Strategy (global)
Primary: contract_key → Fallback: file_url → Last resort: file_name
- Never fabricate identifiers.
- If joins fail, preview must surface the gap rather than guessing.

---

## Artifact Store (v1.5.2)

LocalStorage-backed mock filesystem for artifacts, events, and threads.

### Storage Layout

| Prefix | Content | Example Key |
|--------|---------|-------------|
| `art:` | Artifact objects | `art:art_ds1_rec123_field_2026...` |
| `pr:` | PatchRequest objects | `pr:pr_1234567890` |
| `evt:` | Event log entries | `evt:evt_2026-02-04T...` |
| `thr:` | Thread messages | `thr:thr_art_ds1_rec123...` |

### Artifact ID Generation

Deterministic artifact ID formula:
```
artifact_id = "art_" + dataset_id + "_" + record_id + "_" + field_key + "_" + timestamp
```

- `dataset_id`: Source dataset identifier
- `record_id`: Stable record hash
- `field_key`: Affected field name
- `timestamp`: ISO 8601 creation time

### Thread ID Generation
```
thread_id = "thr_" + artifact_id
```

### Event Log

Events are appended to localStorage with `evt:` prefix:

| Event Type | Trigger |
|------------|---------|
| `artifact_created` | New artifact stored |
| `artifact_updated` | Artifact status changed |
| `thread_message` | Comment added to thread |
| `status_transition` | Review state changed |

### Environment Scoping

Artifacts are scoped by:
- `workspace_id`: Current workspace context
- `environment`: `development` or `production`

Playground mode uses `environment: "playground"` for isolated testing.
