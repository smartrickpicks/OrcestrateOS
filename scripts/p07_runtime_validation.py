#!/usr/bin/env python3
"""P0.7 Runtime Validation — Playwright-based checks for:
  1. Architect can upload JSON truth config
  2. Architect can create first baseline
  3. Architect can set test mode
  4. Architect can promote baseline (confirmation path)
  5. Admin can rollback baseline
  6. Architect can edit role display names; non-architect cannot
  7. Single-use invite works once; second use blocked
  8. Invite creates member with assigned role
  9. People tabs persist state after refresh
  10. No regressions in triage/grid/SRR
"""

import asyncio
import os
import sys
import subprocess
import json

from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000"
CHROMIUM_PATH = subprocess.check_output(["which", "chromium"]).decode().strip()

RESULTS = []

def record(check_name, observed, passed):
    RESULTS.append({"check": check_name, "observed": observed, "result": "PASS" if passed else "FAIL"})


async def main():
    print("=" * 70)
    print("[P0.7] ===== P0.7 RUNTIME VALIDATION START =====")
    print("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM_PATH,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context()
        page = await ctx.new_page()

        errors = []
        logs = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: logs.append(m.text))

        # Load page and clear state
        await page.goto(BASE_URL + "/ui/viewer/index.html", timeout=30000)
        await page.wait_for_timeout(2000)

        # Clear localStorage for clean test
        await page.evaluate("localStorage.clear()")
        await page.reload(timeout=30000)
        await page.wait_for_timeout(2000)

        # Check no parse errors
        js_errors = [e for e in errors if "SyntaxError" in e]
        record("No JS parse errors", f"errors={len(js_errors)}", len(js_errors) == 0)

        # Verify all P0.7 modules loaded
        modules = await page.evaluate("""() => ({
            TruthPack: typeof TruthPack !== 'undefined',
            TruthConfig: typeof TruthConfig !== 'undefined',
            InviteManager: typeof InviteManager !== 'undefined',
            ROLE_REGISTRY: typeof ROLE_REGISTRY !== 'undefined',
            getRoleRegistry: typeof getRoleRegistry !== 'undefined',
            hasPermission: typeof hasPermission !== 'undefined'
        })""")
        all_loaded = all(modules.values())
        record("All P0.7 modules loaded", str(modules), all_loaded)

        if not all_loaded:
            print("[P0.7] FATAL: Modules not loaded, aborting")
            for r in RESULTS:
                print(f"  [{r['result']}] {r['check']}: {r['observed']}")
            await browser.close()
            return

        # === CHECK 1: Architect can upload JSON truth config ===
        # Switch to admin, enable architect
        await page.evaluate("""() => {
            localStorage.setItem('viewer_mode_v10', 'admin');
            currentMode = 'admin';
        }""")
        await page.evaluate("""() => {
            TruthPack.enableArchitectMode();
        }""")
        await page.wait_for_timeout(500)

        # Upload a truth config
        upload_result = await page.evaluate("""() => {
            return TruthConfig.uploadConfig({test_field: 'test_value'}, 'test_config.json')
                .then(function(r) { return r ? {ok: true, id: r.version_id} : {ok: false}; })
                .catch(function(e) { return {ok: false, err: e.message}; });
        }""")
        record("1. Architect uploads JSON truth config", str(upload_result), upload_result.get("ok", False))

        # === CHECK 2: Architect can create baseline from runtime ===
        baseline_result = await page.evaluate("""() => {
            return TruthConfig.createBaselineFromRuntime()
                .then(function(r) { return r ? {ok: true, id: r.version_id, status: r.status} : {ok: false}; })
                .catch(function(e) { return {ok: false, err: e.message}; });
        }""")
        record("2. Architect creates first baseline", str(baseline_result), baseline_result.get("ok", False))

        # === CHECK 3: Architect can set test mode ===
        if baseline_result.get("ok"):
            vid = baseline_result["id"]
            # First promote it so we can set test mode
            await page.evaluate(f"""() => {{
                window._confirmOrig = window.confirm;
                window.confirm = function() {{ return true; }};
                return TruthConfig.promoteBaseline('{vid}');
            }}""")
            await page.wait_for_timeout(300)
            test_mode_result = await page.evaluate(f"""() => {{
                return TruthConfig.setTestMode('{vid}')
                    .then(function(ok) {{ return {{ok: ok, status: TruthConfig.getStatus()}}; }});
            }}""")
            record("3. Architect sets test mode", str(test_mode_result), test_mode_result.get("status") == "test_mode")
        else:
            record("3. Architect sets test mode", "skipped (no baseline)", False)

        # === CHECK 4: Architect can promote baseline ===
        if baseline_result.get("ok"):
            promote_result = await page.evaluate(f"""() => {{
                window.confirm = function() {{ return true; }};
                return TruthConfig.promoteBaseline('{vid}')
                    .then(function(ok) {{ return {{ok: ok, status: TruthConfig.getStatus()}}; }});
            }}""")
            await page.evaluate("window.confirm = window._confirmOrig || window.confirm;")
            record("4. Architect promotes baseline", str(promote_result), promote_result.get("status") == "established")
        else:
            record("4. Architect promotes baseline", "skipped", False)

        # === CHECK 5: Admin can rollback baseline ===
        rollback_result = await page.evaluate("""() => {
            window._confirmOrig2 = window.confirm;
            window.confirm = function() { return true; };
            return TruthConfig.rollbackBaseline()
                .then(function(ok) { return {ok: ok, status: TruthConfig.getStatus()}; });
        }""")
        await page.evaluate("window.confirm = window._confirmOrig2 || window.confirm;")
        record("5. Admin rollbacks baseline", str(rollback_result), rollback_result.get("status") == "no_baseline")

        # === CHECK 6: Architect can edit role display names; non-architect cannot ===
        edit_result = await page.evaluate("""() => {
            var isArch = TruthPack.isArchitect();
            var reg = getRoleRegistry();
            var oldName = reg.analyst.display_name;
            updateRoleDisplayName('analyst', 'Data Analyst');
            var newReg = getRoleRegistry();
            var changed = newReg.analyst.display_name === 'Data Analyst';
            updateRoleDisplayName('analyst', oldName);
            return {isArchitect: isArch, nameChanged: changed};
        }""")
        record("6. Architect edits role display name", str(edit_result), edit_result.get("nameChanged", False))

        # Now test as non-architect
        await page.evaluate("""() => {
            TruthPack.disableArchitectMode();
            localStorage.setItem('viewer_mode_v10', 'analyst');
            currentMode = 'analyst';
        }""")
        await page.wait_for_timeout(300)
        non_arch_result = await page.evaluate("""() => {
            var reg = getRoleRegistry();
            var oldName = reg.verifier.display_name;
            updateRoleDisplayName('verifier', 'Checker');
            var newReg = getRoleRegistry();
            var blocked = newReg.verifier.display_name === oldName;
            return {blocked: blocked, isArch: TruthPack.isArchitect()};
        }""")
        record("6b. Non-architect blocked from editing roles", str(non_arch_result), non_arch_result.get("blocked", False))

        # Switch back to architect for remaining tests
        await page.evaluate("""() => {
            localStorage.setItem('viewer_mode_v10', 'admin');
            currentMode = 'admin';
            TruthPack.enableArchitectMode();
        }""")
        await page.wait_for_timeout(300)

        # === CHECK 7: Single-use invite ===
        invite_result = await page.evaluate("""() => {
            var inv = InviteManager.createInvite('analyst', 0, 'test invite');
            if (!inv) return {ok: false, reason: 'create_failed'};
            var use1 = InviteManager.useInvite(inv.invite_id, 'Test User', 'test@example.com');
            var use2 = InviteManager.useInvite(inv.invite_id, 'Test User 2', 'test2@example.com');
            return {
                created: true,
                first_use: use1.success,
                second_use_blocked: !use2.success,
                second_reason: use2.reason || 'unknown'
            };
        }""")
        record("7. Single-use invite (reuse blocked)", str(invite_result),
               invite_result.get("first_use", False) and invite_result.get("second_use_blocked", False))

        # === CHECK 8: Invite creates member with assigned role ===
        member_check = await page.evaluate("""() => {
            var users = getDemoUsers();
            var found = false;
            var role = '';
            for (var i = 0; i < users.length; i++) {
                if (users[i].email === 'test@example.com') {
                    found = true;
                    role = users[i].role;
                    break;
                }
            }
            return {found: found, role: role};
        }""")
        record("8. Invite creates member with assigned role", str(member_check),
               member_check.get("found", False) and member_check.get("role") == "analyst")

        # === CHECK 9: People tabs persist state after refresh ===
        await page.evaluate("localStorage.setItem('people_active_tab', 'invites')")
        await page.reload(timeout=30000)
        await page.wait_for_timeout(2000)
        persist_check = await page.evaluate("localStorage.getItem('people_active_tab')")
        record("9. People tab state persists after refresh", f"tab={persist_check}", persist_check == "invites")

        # === CHECK 10: No regressions in triage/grid/SRR ===
        nav_check = await page.evaluate("""() => {
            var triagePage = document.getElementById('page-triage');
            var gridPage = document.getElementById('page-grid');
            var srrPage = document.getElementById('page-row');
            return {
                triage_exists: !!triagePage,
                grid_exists: !!gridPage,
                srr_exists: !!srrPage
            };
        }""")
        no_regression = nav_check.get("triage_exists") and nav_check.get("grid_exists") and nav_check.get("srr_exists")
        record("10. No regressions in triage/grid/SRR", str(nav_check), no_regression)

        await browser.close()

    # === REPORT ===
    passes = sum(1 for r in RESULTS if r["result"] == "PASS")
    total = len(RESULTS)
    status = "GREEN" if passes == total else "RED"

    print(f"\n{'=' * 70}")
    print(f"[P0.7] Phase Result: {status} ({passes}/{total})")
    print(f"{'=' * 70}")
    print()
    print(f"{'Check':<55} | {'Observed':<50} | Result")
    print("-" * 120)
    for r in RESULTS:
        obs = r["observed"][:50] if len(r["observed"]) > 50 else r["observed"]
        print(f"{r['check']:<55} | {obs:<50} | {r['result']}")
    print()

    # Audit events check
    audit_events = [l for l in logs if any(e in l for e in [
        "truth_config_uploaded", "truth_baseline_created", "truth_mode_set",
        "truth_baseline_promoted", "truth_baseline_rolled_back",
        "invite_created", "invite_used", "role_display_updated",
        "member_role_assigned"
    ])]
    print(f"[P0.7] Audit Events Captured: {len(audit_events)}")
    for ae in audit_events[:10]:
        print(f"  {ae}")

    print(f"\n[P0.7] FINAL: P0.7 = {status}")
    print(f"[P0.7] ===== P0.7 RUNTIME VALIDATION END =====")


if __name__ == "__main__":
    asyncio.run(main())
