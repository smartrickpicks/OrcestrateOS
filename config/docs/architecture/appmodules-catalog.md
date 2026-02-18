# AppModules Catalog

> Visual module catalog for `window.AppModules` — 55 modules through Phase D15.
> Source: `ui/viewer/index.html`

## Summary

| Phase | Module Count | Registration |
|-------|-------------|--------------|
| C (Dynamic) | 4 | `register()` |
| D1 (Grid) | 3 | `_registry.push` |
| D2 (Record Inspector) | 4 | `_registry.push` |
| D3 (PDF Viewer) | 3 | `_registry.push` |
| D4 (Admin Panel) | 8 | `_registry.push` |
| D5 (Audit Timeline) | 3 | `_registry.push` |
| D6 (DataSource/Import) | 3 | `_registry.push` |
| D7 (System Pass) | 3 | `_registry.push` |
| D8 (Contract Health) | 3 | `_registry.push` |
| D9 (Data Quality) | 3 | `_registry.push` |
| D10 (Batch Merge) | 3 | `_registry.push` |
| D11 (Grid Context Menu) | 3 | `_registry.push` |
| D12 (Patch Studio) | 3 | `_registry.push` |
| D13 (Contract Index) | 3 | `_registry.push` |
| D14 (Export Engine) | 3 | `_registry.push` |
| D15 (Rollback/Undo) | 3 | `_registry.push` |
| **Total** | **55** | 51 explicit + 4 dynamic |

---

## Phase C — Dynamic Modules (4)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Components.MetricStrip` | Metric strip rendering | `MetricStrip.render()` | `[APP-MODULES][P1C] MetricStrip.render: contracts=N, records=N` |
| `Components.LifecycleRail` | Lifecycle rail rendering | `LifecycleRail.render()` | `[APP-MODULES][P1C] LifecycleRail.render: stages=N` |
| `Components.ContractSummaryTable` | Contract summary table rendering | `ContractSummaryTable.render()` | `[APP-MODULES][P1C] ContractSummaryTable.render: rows=N` |
| `Components.PreflightIssueTable` | Preflight issue table rendering | `PreflightIssueTable.renderChecklist()` | `[APP-MODULES][P1C] PreflightIssueTable.renderChecklist: steps=N` |

**Phase log:** `[APP-MODULES][P1C] bootstrap_complete: modules=N, version=N`

---

## Phase D1 — Grid Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.GridState` | Filter get/set, sort, column visibility, filtered data | `getRef`, `getFilter`, `setFilter`, `getSort`, `setSort`, `getVisibleColumns`, `getColumnLetter`, `updateFilterChips` → `updateGridFilterChips()`, `updateURL` → `updateGridURL()`, `getFilteredData` | `[APP-MODULES][P1D1] registered: Engines.GridState` |
| `Components.GridHeader` | Header render with sort indicators, column drag | `render(visibleColumns, gridViewMode)` | `[APP-MODULES][P1D1] GridHeader.render: cols=N` |
| `Components.GridTable` | Row render, empty state, footer, batch render | `renderEmpty(colSpan, message)`, `updateFooter(filteredCount, totalCount, gs)`, `renderBatch` → `renderGridBatch()` | `[APP-MODULES][P1D1] registered: Components.GridTable` |

**Phase log:** `[APP-MODULES][P1D1] grid_modules_registered`

---

## Phase D2 — Record Inspector Modules (4)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.RecordInspectorState` | State access, open/close, record get/set | `getRef` → `srrState`, `getCurrentRecord`, `getCurrentSheetName`, `getCurrentRowIndex`, `getCurrentRecordKey`, `getFieldStates`, `getActiveFilter`, `getSearchQuery`, `isReadOnly`, `getPatchDraft` | `[APP-MODULES][P1D2] registered: Engines.RecordInspectorState` |
| `Components.RecordInspectorHeader` | Header with navigation, close button | `renderIdentity` → `_srrResolveRecordName()`, `updateNav` → `srrUpdateNavButtons()`, `updateBackButton` → `_srrUpdateBackButton()`, `updateFileActionBar` → `srrUpdateFileActionBar()` | `[APP-MODULES][P1D2] RecordInspectorHeader.renderIdentity: NAME` |
| `Components.RecordInspectorFieldList` | Field rows with signal badges | `render` → `renderSrrFields()`, `setFilter` → `srrSetFilter()`, `updateFilterCounts` → `srrUpdateFilterCounts()`, `filterByGroup` → `srrFilterByGroup()`, `getFieldCount` | `[APP-MODULES][P1D2] registered: Components.RecordInspectorFieldList` |
| `Components.RecordInspectorPatchRail` | Patch context, draft actions | `expand` → `_srrExpandPatchPanel()`, `collapse` → `_srrCollapsePatchPanel()`, `toggle` → `_srrTogglePatchPanel()`, `renderEditor` → `srrRenderPatchEditor()`, `renderPatchList` → `renderSrrPatchList()`, `isOpen` → `srrIsPatchOverlayOpen()` | `[APP-MODULES][P1D2] registered: Components.RecordInspectorPatchRail` |

**Phase log:** `[APP-MODULES][P1D2] inspector_modules_registered`

---

## Phase D3 — PDF Viewer Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.PdfViewerState` | State access, document load, anchor search | `getCurrentPdfUrl`, `getDocPage`, `getZoom`, `getDocTotalPages`, `getUseFragmentZoom`, `getPdfSourceType`, `getCacheStatus`, `getNetworkPdfUrl`, `getLocalAttachmentFallback`, `getMatchState`, `isValidPdfUrl` → `srrIsValidPdfUrl()`, `buildLogEntry` → `srrBuildLogEntry()`, `loadPersistedState` → `loadSrrPdfState()`, `savePersistedState` → `saveSrrPdfState()` | `[APP-MODULES][P1D3] registered: Engines.PdfViewerState` |
| `Components.PdfViewerToolbar` | Toolbar buttons, page nav, zoom | `prevPage` → `srrPrevPage()`, `nextPage` → `srrNextPage()`, `navigateToPage` → `srrNavigateToPage()`, `forcePageNav` → `srrForcePageNav()`, `zoomIn` → `srrZoomIn()`, `zoomOut` → `srrZoomOut()`, `updateZoomDisplay` → `srrUpdateZoomDisplay()`, `updatePageDisplay` → `srrUpdatePageDisplay()`, `disableFragmentZoom` → `srrDisableFragmentZoom()`, `matchDismiss` → `pdfMatchDismiss()`, `matchNav` → `pdfMatchNav()`, `matchUpdateBar` → `pdfMatchUpdateBar()` | `[APP-MODULES][P1D3] registered: Components.PdfViewerToolbar` |
| `Components.PdfViewerFrame` | Frame render, page display | `loadForRecord` → `srrLoadPdfForRecord()`, `render` → `srrRenderPdf()`, `showEmptyState` → `srrShowEmptyState()`, `showOfflineStub` → `srrShowOfflineStub()`, `showError` → `srrShowPdfError()`, `hideError` → `srrHidePdfError()`, `switchToLocalAttachment` → `srrSwitchToLocalAttachment()`, `updateIframeSrc` → `srrUpdateIframeSrc()`, `setupIframeHandlers` → `srrSetupIframeHandlers()`, `jumpToAnchor` → `srrJumpToAnchor()`, `updateViewerHighlight` → `srrUpdateViewerHighlight()`, `clearHighlight` → `srrClearHighlight()` | `[APP-MODULES][P1D3] registered: Components.PdfViewerFrame` |

**Phase log:** `[APP-MODULES][P1D3] pdf_viewer_modules_registered`

---

## Phase D4 — Admin Panel Modules (8)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.AdminTabState` | Tab get/set, alias resolution, validation | `getCurrentTab`, `resolveAlias`, `isValidTab`, `getAliasMap` | `[APP-MODULES][P1D4] registered: Engines.AdminTabState` |
| `Components.AdminTabsNav` | Tab bar with active indicator | `switchTab` → `switchAdminTab()`, `hideAllPanels`, `showPanel`, `updateButtonStyles`, `updateArchitectRail`, `onUsersActivate` → `renderUsersTable()`, `updateEnvModeUI()` | `[APP-MODULES][P1D4] registered: Components.AdminTabsNav` |
| `Components.AdminTabGovernance` | Governance settings render | `onActivate` → `renderBatchAddAdminToggles()`, `BatchMerge.refreshSourceList()`, `BatchMerge.renderMergedBatchPanel()` | `[APP-MODULES][P1D4] registered: Components.AdminTabGovernance` |
| `Components.AdminTabSchemaStandards` | Schema tree editor render | `onActivate` → `refreshUnknownColumnsTable()` | `[APP-MODULES][P1D4] registered: Components.AdminTabSchemaStandards` |
| `Components.AdminTabPatchOps` | Patch operations render | `onActivate` → `renderAdminQueue()`, `renderPatchConsoleTable()` | `[APP-MODULES][P1D4] registered: Components.AdminTabPatchOps` |
| `Components.AdminTabPeopleAccess` | People workspace render | `onActivate` → `switchPeopleTab()` | `[APP-MODULES][P1D4] registered: Components.AdminTabPeopleAccess` |
| `Components.AdminTabQARunner` | Test suite render | `onActivate` → `QARunner._onTabOpen()` | `[APP-MODULES][P1D4] registered: Components.AdminTabQARunner` |
| `Components.AdminTabRuntimeConfig` | Runtime settings render | `onActivate` → `renderGlossarySummary()` | `[APP-MODULES][P1D4] registered: Components.AdminTabRuntimeConfig` |

**Phase log:** `[APP-MODULES][P1D4] admin_modules_registered`

---

## Phase D5 — Audit Timeline Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.AuditTimelineState` | memCache access, query, actor resolution, canonical event names | `getStore` → `AuditTimeline`, `getMemCache`, `getCount`, `query`, `getForRecord`, `getForDataset`, `resolveActor`, `canonicalEventName` → `_canonicalAuditEventName()`, `inferScope` → `_inferAuditScope()` | `[APP-MODULES][P1D5] registered: Engines.AuditTimelineState` |
| `Components.AuditTimelinePanel` | Panel open/close, badge, dropdown, export | `open` → `openFullAuditPanel()`, `close` → `closeFullAuditPanel()`, `refresh` → `refreshFullAuditPanel()`, `refreshDropdown` → `refreshAuditHeaderDropdown()`, `exportLog` → `exportAuditLogOnly()`, `showForRecord` → `showAuditLogForRecord()`, `isOpen`, `updateBadge` | `[APP-MODULES][P1D5] registered: Components.AuditTimelinePanel` |
| `Components.AuditTimelineFilters` | Filter get/set, quick chips, presets | `getFilters`, `setFilters`, `applyQuickChip` → `applyAuditQuickChip()`, `savePreset` → `saveCurrentAuditFilter()`, `renderPresets` → `renderAuditFilterPresets()`, `resetAll` | `[APP-MODULES][P1D5] registered: Components.AuditTimelineFilters` |

**Phase log:** `[APP-MODULES][P1D5] audit_timeline_modules_registered`

---

## Phase D6 — DataSource/Import Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.ImportState` | Import state tracking, file type detection, parse status | `getSessionState` → `sessionState`, `getStatus`, `getSourceType`, `getFileName`, `getDatasetId`, `isLoaded`, `getLoadedAt`, `getErrors`, `parseCSV` → `parseCSV()`, `parseWorkbook` → `parseWorkbook()`, `handleFileImport` → `handleFileImport()`, `resetSession` → `resetSession()` | `[APP-MODULES][P1D6] registered: Engines.ImportState` |
| `Engines.WorkbookSessionStore` | Workbook cache save/load/clear, named session save/load/list | `getSessionDB` → `SessionDB`, `saveWorkbookToCache` → `saveWorkbookToCache()`, `loadWorkbookFromCache` → `loadWorkbookFromCache()`, `clearWorkbookCache` → `clearWorkbookCache()`, `getSavedSessions` → `getSavedSessions()`, `saveCurrentSession` → `saveCurrentSession()`, `loadSavedSession` → `loadSavedSession()`, `deleteSavedSession` → `deleteSavedSession()`, `saveNavState` → `saveNavStateToCache()`, `loadNavState` → `loadNavStateFromCache()`, `handleClearAndReload` → `handleClearCacheAndReload()` | `[IMPORT-D6] session_saved`, `[IMPORT-D6] session_loaded` |
| `Components.DataSourcePanel` | Panel open/close, file input | `open` → `openDataSourcePanel()`, `close` → `closeDataSourceDrawer()`, `isOpen`, `updateBar` → `updateActiveDataSourceBar()`, `updateDrawerState` → `updateDataSourceDrawerState()`, `renderSessions` → `renderSavedSessionsList()`, `handleExcelUpload` → `handleExcelUpload()`, `getActiveSourceName` | `[IMPORT-D6] source_opened` |

**Phase log:** `[APP-MODULES][P1D6] datasource_modules_registered`

---

## Phase D7 — System Pass Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.SystemPassState` | Proposals, run/rerun, accept/reject, bulk actions, hinge detection, sort/filter | `getProposals` → `SystemPass.getProposals()`, `getSortedProposals` → `SystemPass.getSortedProposals()`, `run` → `SystemPass.run()`, `acceptProposal` → `SystemPass.acceptProposal()`, `rejectProposal` → `SystemPass.rejectProposal()`, `bulkAccept` → `SystemPass.bulkAccept()`, `bulkReject` → `SystemPass.bulkReject()`, `reset` → `SystemPass.reset()`, `isHingeField` → `SystemPass._isHingeField()`, `getLastRunTimestamp` | `[SYSTEMPASS-D7] rerun_started`, `[SYSTEMPASS-D7] rerun_finished`, `[SYSTEMPASS-D7] proposal_action`, `[SYSTEMPASS-D7] bulk_action` |
| `Components.SystemPassPanel` | Panel open/close, rerun, render | `open` → `rerunSystemPass()`, `close` → `cancelSystemPassRerun()`, `executeRerun` → `executeSystemPassRerun()`, `renderResults` → `renderSystemPassResults()`, `changeSort` → `changeSystemPassSort()`, `changeFilter` → `changeSystemPassFilter()` | `[SYSTEMPASS-D7] panel_opened` |
| `Components.SystemPassActions` | Single and bulk proposal actions with delegate wiring | `acceptProposal` → `acceptSystemPassProposal()`, `rejectProposal` → `rejectSystemPassProposal()`, `bulkAccept` → `bulkAcceptSystemPass()`, `promptBulkReject` → `promptBulkRejectSystemPass()`, `cancelBulkReject` → `cancelBulkRejectSystemPass()`, `executeBulkReject` → `executeBulkRejectSystemPass()` | (actions logged via Engines.SystemPassState) |

**Phase log:** `[APP-MODULES][P1D7] systempass_modules_registered`

---

## Phase D8 — Contract Health Score Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.ContractHealthState` | Scores, penalties, bands, computeAll, sortByHealth, getFilteredContracts | `getScores`, `getPrevScores`, `getActiveBandFilter`, `getPenaltyConfig`, `getBands`, `getBand`, `computeScore` → `ContractHealthScore.computeScore()`, `computeAll` → `ContractHealthScore.computeAll()`, `sortByHealth` → `ContractHealthScore.sortByHealth()`, `getFilteredContracts` → `ContractHealthScore.getFilteredContracts()`, `getScoreForContract` | `[HEALTH-D8] score_calculated` |
| `Components.ContractHealthPanel` | Health cell render, filter chip UI, band filter action | `renderHealthCell` → `ContractHealthScore.renderHealthCell()`, `filterByBand` → `ContractHealthScore.filterByBand()`, `updateFilterChips` → `ContractHealthScore._updateFilterChips()` | `[HEALTH-D8] panel_rendered`, `[HEALTH-D8] health_refreshed` |
| `Components.ContractHealthBadges` | Badge rendering in triage/patch/queue tables | `renderInlineBadge`, `renderInlineBadgeWithTooltip`, `getWorstScore` | `[HEALTH-D8] badge_rendered` |

**Phase log:** `[APP-MODULES][P1D8] health_modules_registered`

---

## Phase D9 — Data Quality Check Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.DataQualityState` | DQ state access, run/detect/rerun, card update | `getState` → `_dqCheckState`, `getActiveTab`, `getAcctQueue`, `getAcctIndex`, `getAddrQueue`, `getAddrIndex`, `getDuplicateAccountItems`, `getAddressCandidateItems`, `getAddressCandidateDecisions`, `run` → `_dqCheckRun()`, `detectOnly` → `_dqCheckDetectOnly()`, `rerun` → `_dqCheckRerun()`, `reopen` → `_dqCheckReopen()`, `updateCard` → `_dqCheckUpdateCard()` | `[DQ-D9] dq_started`, `[DQ-D9] dq_finished` |
| `Components.DataQualityModal` | Modal show/close, tab switch, tab badge update | `show` → `_dqCheckShowModal()`, `close` → `_dqCheckClose()`, `switchTab` → `_dqCheckSwitchTab()`, `updateTabs` → `_dqCheckUpdateTabs()`, `showAcctCurrent` → `_dqCheckShowAcctCurrent()`, `showAddrCurrent` → `_dqCheckShowAddrCurrent()` | `[DQ-D9] modal_opened` |
| `Components.DataQualityActions` | Account dismiss/merge/link, address accept/reject | `acctDismiss` → `_dqAcctDismiss()`, `acctMerge` → `_dqAcctMerge()`, `acctLinkOnly` → `_dqAcctLinkOnly()`, `addrAccept` → `_dqAddrAccept()`, `addrReject` → `_dqAddrReject()` | `[DQ-D9] action_taken` |

**Phase log:** `[APP-MODULES][P1D9] dq_modules_registered`

---

## Phase D10 — Batch Merge Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.BatchMergeState` | Merged batch state access, session restore, reset, active filter | `getMergedBatches` → `BatchMerge._mergedBatches`, `getMergedBatch` → `BatchMerge.getMergedBatch()`, `listMergedBatches` → `BatchMerge.listMergedBatches()`, `getActiveMergedBatchFilter`, `restoreFromSession` → `BatchMerge.restoreFromSession()`, `reset` → `BatchMerge.reset()` | (state-only, no direct logs) |
| `Components.BatchMergePanel` | Source list refresh, merged panel render, lineage view, filter change | `refreshSourceList` → `BatchMerge.refreshSourceList()`, `renderMergedBatchPanel` → `BatchMerge.renderMergedBatchPanel()`, `viewContractLineage` → `BatchMerge._viewContractLineage()`, `showStatus` → `BatchMerge._showStatus()`, `populateMergedBatchSelector` → `populateMergedBatchSelector()`, `handleMergedBatchFilterChange` → `handleMergedBatchFilterChange()` | `[MERGE-D10] panel_opened` |
| `Components.BatchMergeActions` | Merge execution (try/catch guarded), delete, tenant rule promotion | `executeMerge` → `BatchMerge.executeMerge()`, `deleteMergedBatch` → `BatchMerge.deleteMergedBatch()`, `promoteTenantRule` → `BatchMerge.promoteTenantRule()`, `promptPromoteRule` → `BatchMerge._promptPromoteRule()` | `[MERGE-D10] merge_started`, `[MERGE-D10] merge_finished`, `[MERGE-D10] merge_failed`, `[MERGE-D10] action_taken` |

**Phase log:** `[APP-MODULES][P1D10] merge_modules_registered`

---

## Phase D11 — Grid Context Menu Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.GridContextState` | Context state, role matrix, current role, system field check, action state, record resolve | `getState` → `_gridCtxState`, `getRoleMatrix` → `_GRID_CTX_ROLE_MATRIX`, `getCurrentRole` → `_gridCtxGetCurrentRole()`, `isSystemField` → `_gridCtxIsSystemField()`, `getActionState` → `getGridContextActionState()`, `resolveRecord` → `_gridCtxResolveRecord()`, `findClosest` → `_gridCtxFindClosest()` | (state-only; logs emitted from original functions) |
| `Components.GridContextMenu` | Menu open/close, item render, isOpen check | `open` → `_gridCtxOpen()`, `close` → `_gridCtxClose()`, `renderItem` → `_gridCtxItem()`, `isOpen` | `[GRIDCTX-D11] menu_opened`, `[GRIDCTX-D11] menu_closed` |
| `Components.GridContextActions` | Action dispatch, action state query | `dispatch` → `_gridCtxAction()`, `getActionState` (delegates to `Engines.GridContextState`) | `[GRIDCTX-D11] action_invoked`, `[GRIDCTX-D11] action_blocked` |

**Phase log:** `[APP-MODULES][P1D11] gridctx_modules_registered`

---

## Phase D12 — Patch Studio Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.PatchStudioState` | Panel open state, patch type, draft, proposed changes, override, drawer context, gate validation | `isPanelOpen` → `srrIsPatchOverlayOpen()`, `getPatchType` → `srrState.patchType`, `getDraft` → `srrState.patchDraft`, `getProposedChanges` → `srrState.proposedChanges`, `isOverrideEnabled` → `srrState.overrideEnabled`, `getDrawerContext` → `window._gridDrawerContext`, `validateGates` → `validateSubmissionGates()` | `[APP-MODULES][P1D12] registered: Engines.PatchStudioState` |
| `Components.PatchStudioPanel` | Panel open/close/toggle, editor render, draft save, submit, drawer open/close/submit | `open` → `_srrExpandPatchPanel()`, `close` → `_srrCollapsePatchPanel()`, `toggle` → `_srrTogglePatchPanel()`, `renderEditor` → `srrRenderPatchEditor()`, `saveDraft` → `srrSaveDraft()`, `submit` → `srrSubmitPatchRequest()`, `openDrawer` → `_gridOpenPatchDrawer()`, `closeDrawer` → `_gridCloseDrawer()`, `submitDrawer` → `_gridDrawerSubmit()` | `[PATCHSTUDIO-D12] panel_opened`, `[PATCHSTUDIO-D12] draft_updated`, `[PATCHSTUDIO-D12] submit_attempted`, `[PATCHSTUDIO-D12] submit_blocked`, `[PATCHSTUDIO-D12] submit_succeeded` |
| `Components.PatchStudioEvidence` | Evidence save, evidence gate check, preflight gate check, drawer evidence save/get | `saveEvidence` → `srrSaveEvidenceDraft()`, `checkEvidenceGate` → `srrCheckEvidenceGate()`, `checkPreflightGate` → `srrCheckPreflightGate()`, `saveDrawerEvidence` → `_gridDrawerSaveEvidence()`, `getDrawerEvidenceDraft` → `window._gridDrawerContext._evidenceDraft` | (evidence logs via original functions) |

**Phase log:** `[APP-MODULES][P1D12] patchstudio_modules_registered`

---

## Phase D13 — Contract Index Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.ContractIndexState` | Build/reset contract index, availability check, fail-open state, index access, session persist/restore | `build` → `ContractIndex.build()`, `reset` → `ContractIndex.reset()`, `isAvailable` → `ContractIndex.isAvailable()`, `isFailOpen` → `ContractIndex._failOpen`, `getIndex` → `ContractIndex._index`, `getStats` → `ContractIndex._index.stats`, `persistToSession` → `ContractIndex._persistToSession()`, `restoreFromSession` → `ContractIndex._restoreFromSession()` | `[CIDX-D13] build_started`, `[CIDX-D13] build_finished` |
| `Components.ContractIndexQueries` | Contract ID derivation, document ID derivation, batch ID, contract/row lookups | `deriveContractId` → `ContractIndex.deriveContractId()`, `deriveDocumentId` → `ContractIndex.deriveDocumentId()`, `deriveBatchId` → `ContractIndex.deriveBatchId()`, `getContract` → `ContractIndex.getContract()`, `getContractForRow` → `ContractIndex.getContractForRow()`, `listContracts` → `ContractIndex.listContracts()`, `getContractRows` → `ContractIndex.getContractRows()` | `[CIDX-D13] query_executed` |
| `Components.ContractIndexRollups` | Rollup computation, selector population, detail drawer, filter change, unknown column access | `getRollup` → `ContractIndex.getRollup()`, `populateSelector` → `populateContractSelector()`, `openDetailDrawer` → `openContractDetailDrawer()`, `handleFilterChange` → `handleContractFilterChange()`, `getUnknownColumns` → `ContractIndex._index.unknown_columns` | `[CIDX-D13] rollup_rendered` |

**Phase log:** `[APP-MODULES][P1D13] contractindex_modules_registered`

---

## Phase D14 — Export Engine Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.ExportState` | XLSX availability, workbook load check, data/meta sheet lists, record count, export context snapshot | `isXlsxAvailable` → `typeof XLSX`, `isWorkbookLoaded` → `workbook.order`, `getDataSheets` → `getDataSheets()`, `getMetaSheets` → `getMetaSheets()`, `getTotalRecordCount` → `getTotalRecordCount()`, `getExportContext` → composite snapshot | (state-only, no direct logs) |
| `Components.ExportWorkbook` | Full workbook export, individual sheet builders (change log, RFI, signals, metadata, audit log) | `exportFull` → `handleExportSave()`, `buildChangeLogSheet` → `buildChangeLogSheet()`, `buildRFISheet` → `buildRFISheet()`, `buildSignalsSummarySheet` → `buildSignalsSummarySheet()`, `buildMetadataSheet` → `buildMetadataSheet()`, `buildAuditLogSheet` → `buildAuditLogSheet()` | `[EXPORT-D14] export_started`, `[EXPORT-D14] workbook_built`, `[EXPORT-D14] audit_built`, `[EXPORT-D14] export_finished`, `[EXPORT-D14] export_failed` |
| `Components.ExportAuditOnly` | Standalone audit log export, unknown columns export | `exportAuditLog` → `exportAuditLogOnly()`, `exportUnknownColumns` → `exportUnknownColumnsRequest()` | `[EXPORT-D14] export_started`, `[EXPORT-D14] export_finished`, `[EXPORT-D14] export_failed` |

**Phase log:** `[APP-MODULES][P1D14] export_modules_registered`

---

## Phase D15 — Rollback / Undo Modules (3)

| Module Path | Responsibility | Delegate Sites | Deterministic Logs |
|---|---|---|---|
| `Engines.RollbackState` | Rollback artifact access/filter/reset, undo buffer state/peek/canUndo | `getArtifacts` → `RollbackEngine.getArtifacts()`, `getArtifact` → `RollbackEngine.getArtifacts()` lookup, `reset` → `RollbackEngine.reset()`, `getUndoBuffer` → `UndoManager.getBuffer()`, `canUndo` → `UndoManager.canUndo()`, `peekUndo` → `UndoManager.peek()` | (state-only, no direct logs) |
| `Components.RollbackActions` | Create rollback at field/patch/contract/batch scope, apply rollback | `createFieldRollback` → `createFieldRollback()`, `createPatchRollback` → `createPatchRollback()`, `createContractRollback` → `createContractRollback()`, `createBatchRollback` → `createBatchRollback()`, `applyRollback` → `applyRollback()` | `[ROLLBACK-D15] rollback_created`, `[ROLLBACK-D15] rollback_applied`, `[ROLLBACK-D15] rollback_blocked` |
| `Components.UndoActions` | Push undo entry, execute undo, undo last edit, undo specific field change, clear buffer | `push` → `UndoManager.push()`, `undo` → `UndoManager.undo()`, `undoLastEdit` → `srrUndoLastEdit()`, `undoChange` → `srrUndoChange()`, `clear` → `UndoManager.clear()` | `[ROLLBACK-D15] undo_applied`, `[ROLLBACK-D15] undo_blocked` |

**Phase log:** `[APP-MODULES][P1D15] rollback_undo_modules_registered`
