# AppModules Developer Guide

> How to use, extend, and safely extract modules in the `window.AppModules` namespace.

## 1. How to Call Modules Safely

All module methods use `typeof` guards to protect against undefined references. When calling a module from outside the AppModules namespace, follow the same pattern:

```javascript
// Safe call pattern (ES5)
if (window.AppModules && window.AppModules.Components.GridHeader) {
    window.AppModules.Components.GridHeader.render(visibleColumns, gridViewMode);
}

// State access pattern
var record = null;
if (window.AppModules && window.AppModules.Engines.RecordInspectorState) {
    record = window.AppModules.Engines.RecordInspectorState.getCurrentRecord();
}
```

**Key rules:**

- Always check `window.AppModules` exists before accessing any module.
- Never assume a module method will return a value; check for `null`/`undefined` returns.
- Modules are registered during page load; they are available after DOMContentLoaded.
- All module code must be ES5 compliant: no `const`, `let`, arrow functions, template literals, or `async/await`.

## 2. How to Add a New Module

### Step 1: Choose the namespace

- **Engines** (`AppModules.Engines.*`) — State access, data computation, business logic. No DOM manipulation.
- **Components** (`AppModules.Components.*`) — UI rendering, DOM manipulation, event wiring.

### Step 2: Create the IIFE block

Place a new IIFE between the last phase end comment and Phase B start. Follow the naming convention `PHASE DXX: DESCRIPTION`:

```javascript
// ========== PHASE D13: YOUR_FEATURE MODULE EXTRACTION ==========
(function() {
    var _ns = window.AppModules;
    if (!_ns) return;

    _ns.Engines.YourFeatureState = {
        _id: 'Engines.YourFeatureState',
        getData: function() {
            if (typeof yourDataSource !== 'undefined') return yourDataSource;
            return null;
        }
    };
    _ns._registry.push('Engines.YourFeatureState');
    console.log('[APP-MODULES][P1D13] registered: Engines.YourFeatureState');

    _ns.Components.YourFeaturePanel = {
        _id: 'Components.YourFeaturePanel',
        open: function() {
            if (typeof openYourFeature === 'function') openYourFeature();
        }
    };
    _ns._registry.push('Components.YourFeaturePanel');
    console.log('[APP-MODULES][P1D13] registered: Components.YourFeaturePanel');

    console.log('[APP-MODULES][P1D13] yourfeature_modules_registered: YourFeatureState, YourFeaturePanel');
})();
// ========== END PHASE D13 ==========
```

### Step 3: Add typeof guards to every delegate

Every method that calls an original function must wrap it in a `typeof` guard:

```javascript
myMethod: function() {
    if (typeof originalFunction === 'function') originalFunction();
}
```

For state access:

```javascript
getState: function() {
    if (typeof stateVar !== 'undefined') return stateVar;
    return null;
}
```

### Step 4: Add deterministic logs to original functions

Inject `console.log` calls into the original function bodies (not just the module wrappers) for real-path observability:

```javascript
// Inside the ORIGINAL function body (not the module wrapper)
console.log('[YOURFEATURE-D13] action_name');
```

Log tag format: `[FEATURE_TAG-PHASE] event_name`

### Step 5: Register in `_registry`

Each module must push its full path to `_ns._registry`:

```javascript
_ns._registry.push('Engines.YourFeatureState');
_ns._registry.push('Components.YourFeaturePanel');
```

### Step 6: Add phase completion log

At the end of the IIFE, log the phase registration summary:

```javascript
console.log('[APP-MODULES][P1D13] yourfeature_modules_registered: YourFeatureState, YourFeaturePanel');
```

### Step 7: Update documentation

1. Update `replit.md` AppModules Registry section with the new module table, log entries, and updated count.
2. Update `docs/architecture/appmodules-catalog.md` with the new phase section.
3. Update `docs/architecture/appmodules-map.md` Mermaid graph with the new subgraph.

## 3. Checklist for Behavior-Preserving Extraction

Use this checklist for every phase extraction to ensure zero behavioral regressions:

### Pre-Extraction
- [ ] Identify all functions to extract (list function names, line numbers)
- [ ] Verify no DOM IDs or CSS classes will change
- [ ] Confirm all target functions exist and are reachable at runtime

### Module Design
- [ ] Each module has a unique `_id` property
- [ ] All methods use `typeof` guards (functions: `typeof fn === 'function'`, state: `typeof var !== 'undefined'`)
- [ ] Modules are pure delegates: no new logic, no modified behavior
- [ ] ES5 compliance verified: no `const`, `let`, `=>`, template literals, `async/await`

### Registration
- [ ] Each module calls `_ns._registry.push('Type.ModuleName')`
- [ ] Registration log emitted: `console.log('[APP-MODULES][P1DXX] registered: Type.ModuleName')`
- [ ] Phase completion log emitted at end of IIFE
- [ ] Total registry count updated (check with `window.AppModules._registry.length`)

### Deterministic Logging
- [ ] Logs injected into ORIGINAL function bodies (not just wrappers)
- [ ] Log tag follows format: `[FEATURE-PHASE] event_name`
- [ ] All key lifecycle events covered: opened, started, finished, failed, action_taken
- [ ] Block/error paths have distinct log entries (e.g., `submit_blocked` with reason)

### Validation
- [ ] Smoke tests pass (`scripts/replit_smoke.sh`)
- [ ] No DOM ID changes (grep for element IDs before and after)
- [ ] No CSS class changes
- [ ] No event handler changes (onclick, onchange, etc.)
- [ ] Module count matches expected total (43 explicit + 4 dynamic = 47 as of D12)
- [ ] All module methods callable without errors when dependencies are undefined (typeof guards prevent crashes)

### Documentation
- [ ] `replit.md` updated with module table, log entries, count
- [ ] `docs/architecture/appmodules-catalog.md` updated with new phase section
- [ ] `docs/architecture/appmodules-map.md` Mermaid graph updated

## 4. Module Naming Conventions

| Convention | Example | Rule |
|---|---|---|
| Engine name | `Engines.GridState` | `Engines.` + PascalCase feature + `State` |
| Component name | `Components.GridHeader` | `Components.` + PascalCase feature + UI element |
| Module `_id` | `'Engines.GridState'` | Must match the registration path exactly |
| Phase comment | `PHASE D1: GRID MODULE EXTRACTION` | `PHASE D` + number + `: ` + UPPER_CASE description |
| Registration log | `[APP-MODULES][P1D1]` | `[APP-MODULES][P1D` + phase number + `]` |
| Feature log | `[GRIDCTX-D11]` | `[FEATURE_ABBREV-D` + phase number + `]` |

## 5. ES5 Compliance Quick Reference

| Prohibited (ES6+) | Use Instead (ES5) |
|---|---|
| `const x = 1` | `var x = 1` |
| `let y = 2` | `var y = 2` |
| `() => {}` | `function() {}` |
| `` `template ${var}` `` | `'string ' + var` |
| `async/await` | Callbacks or `Promise.then()` |
| `class Foo {}` | `function Foo() {}` or object literal |
| `{ method() {} }` | `{ method: function() {} }` |
| `for (const x of arr)` | `for (var i = 0; i < arr.length; i++)` |
| `{ ...obj }` | Manual property copy |
