# QE‑FineTuner (Concept Only)

Scope
- Proposal‑only placeholder; not implemented. Offline‑first and deterministic; copy‑only outputs; no network, no execution.

Purpose
- Suggest configuration deltas (patch suggestions, blacklist entries) to reduce warnings/flags while preserving semantics.

Inputs (proposal)
- Truth Config snapshot (config/config_pack.base.json)
- Proposed Changes (patch draft)
- Preview Packet (Preview Packet JSON)
- Optional: Reference Expected, Evidence Pack notes

Outputs (proposal)
- Patch Suggestions: changes[] (add_rule/deprecate_rule/SET_VALUE patterns)
- Blacklist Suggestions: Do‑Not‑Match or Require Manual Review entries
- Questions: crisp clarification prompts (e.g., ambiguous headers)

Boundaries (hard)
- Must not edit Truth Config directly; no runtime execution; no Salesforce API logic
- Copy‑only JSON suggestions; Admin/Verifier approval and smoke pass required before adoption

Suggested JSON schema (proposal)
```
{
  "$schema": "orchestrate_os.qe_finetuner_suggestions.v1",
  "inputs": {
    "base_version": "v0.1.0",
    "ruleset_version": "r-2026-01-30",
    "artifacts": {
      "truth_config_path": "config/config_pack.base.json",
      "proposed_patch_path": "config/config_pack.v0.1.3.patch.json",
      "preview_packet_path": "out/sf_packet.preview.json"
    }
  },
  "suggestions": {
    "patch_changes": [ { "action": "add_rule", "target": "salesforce_rules", "rule": { /* ... */ } } ],
    "blacklist_entries": [ { "pattern": "...", "scope": {"sheet":"accounts","field":"account_name"}, "action": "DO_NOT_MATCH" } ],
    "questions": [ "Is header X an alias of Y?" ]
  },
  "notes": "Copy-only; Admin decides whether to adopt and prepares version bump; strict smoke remains the arbiter"
}
```

Review & adoption
- Admin reviews suggestions, merges into a new patch draft if accepted, and coordinates verifier approval + smoke pass. Version bump documented in CHANGELOG.
