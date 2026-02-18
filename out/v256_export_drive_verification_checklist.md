# V2.56 Export + Drive Verification Checklist

Branch: `codex/v256-export-drive`  
Run ID: `V2.56-EXPORT-DRIVE-E2E`

## Checklist

- [x] Export output preserves corrected values
  - Evidence: `export_corrected_values_persist: true`
- [x] Export (clean) excludes full audit/meta sheets
  - Evidence: `export_has_no_full_audit_sheets: true`
- [x] Export Full includes governance metadata
  - Evidence: `export_full_includes_gov_meta: true`
- [x] Export Full includes orchestrate metadata
  - Evidence: `export_full_includes_orchestrate_meta: true`
- [x] Export Full includes audit log sheet
  - Evidence: `export_full_includes_audit_log: true`
- [x] Export Full uses normalized export status in metadata
  - Evidence: `export_full_gov_meta_status_normalized: true`
- [x] Audit log schema/header is stable
  - Evidence: `export_full_audit_header_stable: true`
- [x] Export filename follows status/naming convention
  - Evidence: `export_filename_convention: true`
- [x] Save-to-Drive uses full workbook payload
  - Evidence: `save_to_drive_uses_full_workbook: true`
- [x] Save-to-Drive targets Drive save endpoint
  - Evidence: `save_to_drive_posts_drive_save_endpoint: true`
- [x] UI actions mapped correctly (`Export` vs `Export Full`)
  - Evidence: `export_action_wires_clean_mode: true`, `export_full_action_wires_full_mode: true`

## Sample Artifact Evidence

- E2E artifact JSON:
  - `/Users/zacharyholwerda/Desktop/CreateMusicFiles/Orchestrate_OS/V1 | ORCHESTRATEOS/V1 Log /V2.5 Build/V2.5 /OrcestrateOS/out/v256_export_drive_e2e_artifact.json`
  - `all_passed: true`
- Test artifact:
  - `/Users/zacharyholwerda/Desktop/CreateMusicFiles/Orchestrate_OS/V1 | ORCHESTRATEOS/V1 Log /V2.5 Build/V2.5 /OrcestrateOS/out/v256_export_drive_pytest.txt`
  - `7 passed`
- Regression tests added for convention behavior:
  - `/Users/zacharyholwerda/Desktop/CreateMusicFiles/Orchestrate_OS/V1 | ORCHESTRATEOS/V1 Log /V2.5 Build/V2.5 /OrcestrateOS/tests/test_drive_export_conventions.py`
    - `test_normalize_export_status_aliases_and_default`
    - `test_build_export_filename_is_canonical`
    - `test_drive_save_normalizes_status_and_audit_metadata`
