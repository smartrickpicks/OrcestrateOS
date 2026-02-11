# Orchestrate OS

## What is Orchestrate OS?
Orchestrate OS is an offline‑first, deterministic, config‑driven governance surface for DataDash workflows. It defines, validates, previews, and exports semantic rules using local artifacts only. No runtime execution, no network calls, no credentials, and no LLM prompts. Preview evidence and strict smoke tests are the arbiter of correctness.

## Key Artifacts (human labels)
- Truth Config: config/config_pack.base.json (authoritative base semantics)
- Proposed Changes: config/config_pack.<version>.patch.json (patch file with changes[])
- Preview Packet: out/sf_packet.preview.json (deterministic preview evidence produced by the harness)
- Reference Expected: examples/expected_outputs/*.json (comparison target for smoke)
- Validation Evidence: validator output (JSON/stdout)
- Smoke Evidence: strict pass/fail logs for baseline (and edge when applicable)

## Roles
- Analyst: Loads artifacts, triages queues, drafts rule/patch overlays, submits Patch Requests for verification
- Verifier: Verifies Validation/Smoke evidence, enforces gates, approves or requests clarification
- Admin: Oversees configuration conventions, determinism policy, baselines and version bump policy (no day‑to‑day record fixing unless permitted)

## No Runtime / No Network (Scope Lock)
- No runtime execution, no external APIs, no credentials
- Patch Requests are submitted in-app; deterministic previews and smoke tests run locally via shell
- Deterministic: severity ordering and join triplet (contract_key → file_url → file_name; nulls last)

## Legacy Naming (Aliases)
The product is now “Orchestrate OS.” Historical aliases you may still see in docs or commits: “Kiwi,” “Control Board,” “Kiwi Semantic Control Board.” Treat these as searchable legacy names that refer to Orchestrate OS.

## Offline Quickstart (local shell)
1) Validate configuration
```
python3 local_runner/validate_config.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json
```
2) Run a deterministic preview (baseline)
```
python3 local_runner/run_local.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json \
  --standardized examples/standardized_dataset.example.json \
  --out out/sf_packet.preview.json
```
3) Strict smoke tests
```
bash scripts/replit_smoke.sh
bash scripts/replit_smoke.sh --edge
```

## Repository Structure (high level)
- docs/: specs, PRDs, interfaces, UI contracts, governance guidance
- rules/: operator‑facing rule authoring templates (Salesforce/QA/Resolver)
- config/: Truth Config and example patch format
- examples/: synthetic datasets and expected outputs (baseline + edge)
- local_runner/: offline harness (validate/preview)
- scripts/: smoke, MCP link generator, repo materializer (offline‑only)
- ui/: governance viewer (in-app Submit Patch Request; deterministic preview via local harness)
## Stakeholder Materials

Executive-facing overviews, deck outlines, and FAQs derived from the core governance doctrine live under `docs/stakeholder/`. These documents are non-normative and reference this README, Flow Doctrine, and Human–Agent workflow as sources of truth.

Primary navigation: docs/INDEX.md
