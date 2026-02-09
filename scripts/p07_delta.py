#!/usr/bin/env python3
"""
P0.7 DELTA: Role Governance + Truth Config Versioning + People Workspace
Applies targeted edits to ui/viewer/index.html on top of P0.6.
"""
import sys, os, re

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read_html():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def write_html(content):
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def apply_edit(content, label, old, new, required=True):
    if old in content:
        content = content.replace(old, new, 1)
        print(f'  [PASS] {label}')
        return content
    else:
        tag = 'SKIP' if not required else 'FAIL'
        print(f'  [{tag}] {label}: old text not found')
        if required:
            # Print first 80 chars of old for debugging
            print(f'         Looking for: {old[:120]}...')
        return content

def main():
    print('[P0.7] Loading index.html...')
    c = read_html()
    original_len = len(c)
    edits = 0

    # =========================================================================
    # EDIT 1: Role Registry + Stable Role IDs
    # Insert after TRUTH_PACK_ARCHITECT_ALLOWLIST definition
    # =========================================================================
    ROLE_REGISTRY_CODE = """
    // P0.7: Role Registry — stable role IDs with permissions
    var ROLE_REGISTRY = {
      architect: {
        role_id: 'architect',
        display_name: 'Architect',
        permissions: ['admin_access', 'truth_pack', 'calibration', 'role_edit', 'invite_manage', 'config_manage', 'baseline_promote', 'baseline_rollback'],
        active: true,
        editable_by_architect: true
      },
      admin: {
        role_id: 'admin',
        display_name: 'Admin',
        permissions: ['admin_access', 'config_manage', 'baseline_rollback', 'user_manage'],
        active: true,
        editable_by_architect: true
      },
      verifier: {
        role_id: 'verifier',
        display_name: 'Verifier',
        permissions: ['review_access', 'patch_verify'],
        active: true,
        editable_by_architect: true
      },
      analyst: {
        role_id: 'analyst',
        display_name: 'Analyst',
        permissions: ['triage_access', 'patch_create', 'srr_access'],
        active: true,
        editable_by_architect: true
      }
    };

    var ROLE_REGISTRY_KEY = 'orchestrate_role_registry_v1';

    function getRoleRegistry() {
      try {
        var stored = localStorage.getItem(ROLE_REGISTRY_KEY);
        if (stored) {
          var parsed = JSON.parse(stored);
          var ids = Object.keys(ROLE_REGISTRY);
          for (var ri = 0; ri < ids.length; ri++) {
            if (!parsed[ids[ri]]) parsed[ids[ri]] = JSON.parse(JSON.stringify(ROLE_REGISTRY[ids[ri]]));
          }
          return parsed;
        }
      } catch(e) {}
      return JSON.parse(JSON.stringify(ROLE_REGISTRY));
    }

    function saveRoleRegistry(registry) {
      try {
        localStorage.setItem(ROLE_REGISTRY_KEY, JSON.stringify(registry));
        return true;
      } catch(e) { return false; }
    }

    function getRoleDisplayName(roleId) {
      var reg = getRoleRegistry();
      if (reg[roleId]) return reg[roleId].display_name;
      return roleId.charAt(0).toUpperCase() + roleId.slice(1);
    }

    function hasPermission(roleId, permission) {
      var reg = getRoleRegistry();
      var role = reg[roleId];
      if (!role || !role.active) return false;
      for (var pi = 0; pi < role.permissions.length; pi++) {
        if (role.permissions[pi] === permission) return true;
      }
      return false;
    }

    function migrateRoleLegacy() {
      var users = null;
      try {
        var stored = localStorage.getItem('orchestrate_demo_users');
        if (stored) users = JSON.parse(stored);
      } catch(e) {}
      if (!users || !users.length) return;
      var LEGACY_MAP = { 'Analyst': 'analyst', 'Verifier': 'verifier', 'Admin': 'admin', 'Architect': 'architect' };
      var changed = false;
      for (var ui = 0; ui < users.length; ui++) {
        var u = users[ui];
        if (u.role && LEGACY_MAP[u.role] && u.role !== LEGACY_MAP[u.role]) {
          u.role = LEGACY_MAP[u.role];
          changed = true;
        }
      }
      if (changed) {
        localStorage.setItem('orchestrate_demo_users', JSON.stringify(users));
        console.log('[P0.7][MIGRATE] Legacy role labels migrated to stable IDs');
      }
    }
"""

    c = apply_edit(c, 'EDIT-1: Role Registry + stable IDs',
        "    var TRUTH_PACK_ARCHITECT_ALLOWLIST = ['architect@orchestrate.local'];",
        "    var TRUTH_PACK_ARCHITECT_ALLOWLIST = ['architect@orchestrate.local'];\n" + ROLE_REGISTRY_CODE)

    # =========================================================================
    # EDIT 2: Truth Config Versioning module
    # Insert after TruthPack.restoreFromStorage closing
    # =========================================================================
    TRUTH_CONFIG_CODE = """
    // P0.7: Truth Config Versioning
    var TRUTH_CONFIG_STORE = 'truth_config_versions';
    var TRUTH_CONFIG_POINTER_KEY = 'active_truth_version_id';

    var TruthConfig = {
      _versions: [],
      _activeId: null,

      init: function() {
        var self = this;
        self._activeId = localStorage.getItem(TRUTH_CONFIG_POINTER_KEY) || null;
        return SessionDB._getAll(SessionDB.WORKBOOK_STORE).then(function(all) {
          self._versions = [];
          for (var i = 0; i < all.length; i++) {
            if (all[i].id && all[i].id.indexOf('truth_config_v_') === 0) {
              self._versions.push(all[i]);
            }
          }
          self._versions.sort(function(a, b) {
            return (b.created_at || '').localeCompare(a.created_at || '');
          });
          console.log('[P0.7][TruthConfig] init: ' + self._versions.length + ' versions, active=' + (self._activeId || 'none'));
          return self._versions;
        }).catch(function() { return []; });
      },

      _generateId: function() {
        return 'truth_config_v_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 4);
      },

      getActive: function() {
        if (!this._activeId) return null;
        for (var i = 0; i < this._versions.length; i++) {
          if (this._versions[i].version_id === this._activeId) return this._versions[i];
        }
        return null;
      },

      getStatus: function() {
        var active = this.getActive();
        if (!active) return 'no_baseline';
        return active.status || 'no_baseline';
      },

      uploadConfig: function(jsonPayload, fileName) {
        if (!TruthPack.isArchitect()) {
          if (typeof showToast === 'function') showToast('Architect role required', 'error');
          return Promise.resolve(null);
        }
        var versionId = this._generateId();
        var record = {
          id: versionId,
          version_id: versionId,
          payload: jsonPayload,
          created_at: new Date().toISOString(),
          created_by: AuditTimeline._resolveActor().id,
          status: 'test_mode',
          promoted_at: null,
          promoted_by: null,
          source: 'upload',
          file_name: fileName || 'unknown.json'
        };
        var self = this;
        return SessionDB._put(SessionDB.WORKBOOK_STORE, record).then(function(ok) {
          if (ok) {
            self._versions.unshift(record);
            self._activeId = versionId;
            localStorage.setItem(TRUTH_CONFIG_POINTER_KEY, versionId);
            AuditTimeline.emit('truth_config_uploaded', {
              actor_role: 'architect',
              metadata: { version_id: versionId, source: 'upload', file_name: fileName }
            });
            console.log('[P0.7][TruthConfig] uploaded: ' + versionId);
            if (typeof showToast === 'function') showToast('Truth Config uploaded (test mode)', 'success');
            self._renderUI();
          }
          return record;
        });
      },

      createBaselineFromRuntime: function() {
        if (!TruthPack.isArchitect()) {
          if (typeof showToast === 'function') showToast('Architect role required', 'error');
          return Promise.resolve(null);
        }
        var snapshot = {};
        try {
          if (typeof fieldMeta !== 'undefined') snapshot.field_meta = fieldMeta;
          if (typeof qaFlags !== 'undefined') snapshot.qa_flags = qaFlags;
          if (typeof hingeGroups !== 'undefined') snapshot.hinge_groups = hingeGroups;
          if (typeof sheetOrder !== 'undefined') snapshot.sheet_order = sheetOrder;
          if (typeof documentTypes !== 'undefined') snapshot.document_types = documentTypes;
          if (typeof columnAliases !== 'undefined') snapshot.column_aliases = columnAliases;
        } catch(e) {}
        var versionId = this._generateId();
        var record = {
          id: versionId,
          version_id: versionId,
          payload: snapshot,
          created_at: new Date().toISOString(),
          created_by: AuditTimeline._resolveActor().id,
          status: 'test_mode',
          promoted_at: null,
          promoted_by: null,
          source: 'runtime_snapshot'
        };
        var self = this;
        return SessionDB._put(SessionDB.WORKBOOK_STORE, record).then(function(ok) {
          if (ok) {
            self._versions.unshift(record);
            self._activeId = versionId;
            localStorage.setItem(TRUTH_CONFIG_POINTER_KEY, versionId);
            AuditTimeline.emit('truth_baseline_created', {
              actor_role: 'architect',
              metadata: { version_id: versionId, source: 'runtime_snapshot' }
            });
            console.log('[P0.7][TruthConfig] baseline_created: ' + versionId);
            if (typeof showToast === 'function') showToast('Baseline created from runtime (test mode)', 'success');
            self._renderUI();
          }
          return record;
        });
      },

      setTestMode: function(versionId) {
        var target = null;
        for (var i = 0; i < this._versions.length; i++) {
          if (this._versions[i].version_id === versionId) { target = this._versions[i]; break; }
        }
        if (!target) return Promise.resolve(false);
        if (!TruthPack.isArchitect()) {
          if (typeof showToast === 'function') showToast('Architect role required', 'error');
          return Promise.resolve(false);
        }
        target.status = 'test_mode';
        this._activeId = versionId;
        localStorage.setItem(TRUTH_CONFIG_POINTER_KEY, versionId);
        var self = this;
        return SessionDB._put(SessionDB.WORKBOOK_STORE, target).then(function(ok) {
          if (ok) {
            AuditTimeline.emit('truth_mode_set', {
              actor_role: 'architect',
              metadata: { version_id: versionId, status: 'test_mode' }
            });
            console.log('[P0.7][TruthConfig] test_mode_set: ' + versionId);
            if (typeof showToast === 'function') showToast('Test mode activated', 'info');
            self._renderUI();
          }
          return ok;
        });
      },

      promoteBaseline: function(versionId) {
        var target = null;
        for (var i = 0; i < this._versions.length; i++) {
          if (this._versions[i].version_id === versionId) { target = this._versions[i]; break; }
        }
        if (!target) return Promise.resolve(false);
        if (!TruthPack.isArchitect()) {
          if (typeof showToast === 'function') showToast('Architect role required', 'error');
          return Promise.resolve(false);
        }
        if (!confirm('Promote this baseline to Established? This will be the active truth config for all users.')) {
          return Promise.resolve(false);
        }
        var actor = AuditTimeline._resolveActor();
        target.status = 'established';
        target.promoted_at = new Date().toISOString();
        target.promoted_by = actor.id;
        this._activeId = versionId;
        localStorage.setItem(TRUTH_CONFIG_POINTER_KEY, versionId);
        var self = this;
        return SessionDB._put(SessionDB.WORKBOOK_STORE, target).then(function(ok) {
          if (ok) {
            AuditTimeline.emit('truth_baseline_promoted', {
              actor_role: 'architect',
              metadata: { version_id: versionId, promoted_by: actor.id }
            });
            console.log('[P0.7][TruthConfig] baseline_promoted: ' + versionId);
            if (typeof showToast === 'function') showToast('Baseline promoted to Established', 'success');
            self._renderUI();
          }
          return ok;
        });
      },

      rollbackBaseline: function() {
        var currentMode = (localStorage.getItem('viewer_mode_v10') || '').toLowerCase();
        if (currentMode !== 'admin' && !TruthPack.isArchitect()) {
          if (typeof showToast === 'function') showToast('Admin or Architect role required', 'error');
          return Promise.resolve(false);
        }
        if (!this._activeId) {
          if (typeof showToast === 'function') showToast('No active baseline to rollback', 'error');
          return Promise.resolve(false);
        }
        if (!confirm('Rollback active baseline? This clears the active truth config version.')) {
          return Promise.resolve(false);
        }
        var prevId = this._activeId;
        this._activeId = null;
        localStorage.removeItem(TRUTH_CONFIG_POINTER_KEY);
        AuditTimeline.emit('truth_baseline_rolled_back', {
          actor_role: TruthPack.isArchitect() ? 'architect' : 'admin',
          metadata: { rolled_back_version: prevId }
        });
        console.log('[P0.7][TruthConfig] baseline_rolled_back: ' + prevId);
        if (typeof showToast === 'function') showToast('Baseline rolled back', 'info');
        this._renderUI();
        return Promise.resolve(true);
      },

      _renderUI: function() {
        var container = document.getElementById('truth-config-controls');
        if (!container) return;
        var isArch = TruthPack.isArchitect();
        var currentMode = (localStorage.getItem('viewer_mode_v10') || '').toLowerCase();
        var canAccess = isArch || currentMode === 'admin';
        if (!canAccess) { container.style.display = 'none'; return; }
        container.style.display = '';

        var status = this.getStatus();
        var active = this.getActive();
        var chipColor = status === 'established' ? '#4caf50' : (status === 'test_mode' ? '#ff9800' : '#9e9e9e');
        var chipLabel = status === 'established' ? 'Established' : (status === 'test_mode' ? 'Test Mode' : 'No Baseline');

        var html = '<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">' +
          '<span style="font-weight: 600; font-size: 0.9em; color: #6a1b9a;">Truth Config</span>' +
          '<span id="truth-config-status-chip" style="font-size: 0.7em; padding: 2px 8px; background: ' + chipColor + '; color: white; border-radius: 10px; font-weight: 600;">' + chipLabel + '</span>' +
          (active ? '<span style="font-size: 0.7em; color: #888;">v: ' + (active.version_id || '').substr(0, 16) + '</span>' : '') +
          '</div>';

        if (isArch) {
          html += '<div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px;">' +
            '<button onclick="TruthConfig._handleUploadClick()" style="padding: 4px 10px; font-size: 0.78em; background: #7b1fa2; color: white; border: none; border-radius: 4px; cursor: pointer;">Upload Truth Config</button>' +
            '<input type="file" id="truth-config-file-input" accept=".json" style="display:none;" onchange="TruthConfig._handleFileSelected(this)">' +
            '<button onclick="TruthConfig.createBaselineFromRuntime()" style="padding: 4px 10px; font-size: 0.78em; background: #1565c0; color: white; border: none; border-radius: 4px; cursor: pointer;">Create Baseline</button>';
          if (active && active.status === 'test_mode') {
            html += '<button onclick="TruthConfig.promoteBaseline(\'' + active.version_id + '\')" style="padding: 4px 10px; font-size: 0.78em; background: #2e7d32; color: white; border: none; border-radius: 4px; cursor: pointer;">Promote to Established</button>';
          }
          if (active && active.status === 'established') {
            html += '<button onclick="TruthConfig.setTestMode(\'' + active.version_id + '\')" style="padding: 4px 10px; font-size: 0.78em; background: #ff9800; color: white; border: none; border-radius: 4px; cursor: pointer;">Set Test Mode</button>';
          }
          html += '</div>';
        }

        if (this._activeId && canAccess) {
          html += '<div style="margin-bottom: 6px;">' +
            '<button onclick="TruthConfig.rollbackBaseline()" style="padding: 4px 10px; font-size: 0.78em; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">Rollback Baseline</button>' +
            '</div>';
        }

        if (this._versions.length > 0) {
          html += '<div style="font-size: 0.75em; color: #888; margin-top: 4px;">History: ' + this._versions.length + ' version(s)</div>';
          html += '<div style="max-height: 120px; overflow-y: auto; margin-top: 4px; font-size: 0.75em; border: 1px solid #e0e0e0; border-radius: 4px;">';
          for (var vi = 0; vi < Math.min(this._versions.length, 10); vi++) {
            var v = this._versions[vi];
            var isActiveV = (v.version_id === this._activeId);
            html += '<div style="padding: 4px 8px; border-bottom: 1px solid #f0f0f0; background: ' + (isActiveV ? '#f3e5f5' : '#fff') + ';">' +
              '<span style="font-weight: ' + (isActiveV ? '600' : '400') + ';">' + (v.version_id || '').substr(0, 20) + '</span>' +
              ' <span style="color: #999;">' + (v.source || '') + '</span>' +
              ' <span style="padding: 1px 4px; border-radius: 3px; background: ' + (v.status === 'established' ? '#e8f5e9' : '#fff3e0') + '; font-size: 0.9em;">' + (v.status || '') + '</span>' +
              '</div>';
          }
          html += '</div>';
        }

        container.innerHTML = html;
      },

      _handleUploadClick: function() {
        var inp = document.getElementById('truth-config-file-input');
        if (inp) inp.click();
      },

      _handleFileSelected: function(input) {
        if (!input.files || !input.files[0]) return;
        var file = input.files[0];
        var reader = new FileReader();
        var self = this;
        reader.onload = function(e) {
          try {
            var parsed = JSON.parse(e.target.result);
            self.uploadConfig(parsed, file.name);
          } catch(err) {
            if (typeof showToast === 'function') showToast('Invalid JSON file', 'error');
          }
          input.value = '';
        };
        reader.readAsText(file);
      }
    };
"""

    c = apply_edit(c, 'EDIT-2: Truth Config Versioning module',
        "    var ContractIndex = {",
        TRUTH_CONFIG_CODE + "\n    var ContractIndex = {")

    # =========================================================================
    # EDIT 3: People Workspace module (Invites)
    # Insert after TruthConfig module (before ContractIndex)
    # =========================================================================
    PEOPLE_CODE = """
    // P0.7: Invite System
    var INVITES_KEY = 'orchestrate_invites_v1';

    var InviteManager = {
      _invites: [],

      init: function() {
        try {
          var stored = localStorage.getItem(INVITES_KEY);
          if (stored) this._invites = JSON.parse(stored);
        } catch(e) { this._invites = []; }
        this._expireCheck();
      },

      _save: function() {
        try {
          localStorage.setItem(INVITES_KEY, JSON.stringify(this._invites));
        } catch(e) {}
      },

      _expireCheck: function() {
        var now = new Date().toISOString();
        for (var i = 0; i < this._invites.length; i++) {
          var inv = this._invites[i];
          if (inv.status === 'active' && inv.expires_at && inv.expires_at < now) {
            inv.status = 'expired';
          }
        }
        this._save();
      },

      createInvite: function(roleId, expiryHours, note) {
        if (!TruthPack.isArchitect() && (localStorage.getItem('viewer_mode_v10') || '').toLowerCase() !== 'admin') {
          if (typeof showToast === 'function') showToast('Admin or Architect role required', 'error');
          return null;
        }
        var reg = getRoleRegistry();
        if (!reg[roleId]) {
          if (typeof showToast === 'function') showToast('Invalid role: ' + roleId, 'error');
          return null;
        }
        var invite = {
          invite_id: 'inv_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 4),
          role_id: roleId,
          status: 'active',
          created_at: new Date().toISOString(),
          created_by: AuditTimeline._resolveActor().id,
          expires_at: expiryHours ? new Date(Date.now() + expiryHours * 3600000).toISOString() : null,
          note: note || '',
          used_by: null,
          used_at: null
        };
        this._invites.push(invite);
        this._save();
        AuditTimeline.emit('invite_created', {
          actor_role: TruthPack.isArchitect() ? 'architect' : 'admin',
          metadata: { invite_id: invite.invite_id, role_id: roleId, expires_at: invite.expires_at }
        });
        console.log('[P0.7][Invite] created: ' + invite.invite_id + ' role=' + roleId);
        if (typeof showToast === 'function') showToast('Invite created for ' + getRoleDisplayName(roleId), 'success');
        return invite;
      },

      useInvite: function(inviteId, userName, userEmail) {
        var invite = null;
        for (var i = 0; i < this._invites.length; i++) {
          if (this._invites[i].invite_id === inviteId) { invite = this._invites[i]; break; }
        }
        if (!invite) return { success: false, reason: 'not_found' };
        if (invite.status !== 'active') return { success: false, reason: 'already_' + invite.status };
        if (invite.expires_at && invite.expires_at < new Date().toISOString()) {
          invite.status = 'expired';
          this._save();
          return { success: false, reason: 'expired' };
        }
        invite.status = 'used';
        invite.used_by = userEmail;
        invite.used_at = new Date().toISOString();
        this._save();

        var users = getDemoUsers();
        var newUser = {
          id: 'user_' + Date.now().toString(36),
          name: userName,
          email: userEmail,
          role: invite.role_id,
          status: 'active',
          invited_by: invite.created_by,
          invite_id: invite.invite_id
        };
        users.push(newUser);
        saveDemoUsers(users);

        AuditTimeline.emit('invite_used', {
          actor_role: invite.role_id,
          metadata: { invite_id: inviteId, user_email: userEmail, role_id: invite.role_id }
        });
        console.log('[P0.7][Invite] used: ' + inviteId + ' by ' + userEmail);
        return { success: true, user: newUser };
      },

      revokeInvite: function(inviteId) {
        var invite = null;
        for (var i = 0; i < this._invites.length; i++) {
          if (this._invites[i].invite_id === inviteId) { invite = this._invites[i]; break; }
        }
        if (!invite || invite.status !== 'active') return false;
        invite.status = 'revoked';
        this._save();
        AuditTimeline.emit('invite_revoked', {
          actor_role: TruthPack.isArchitect() ? 'architect' : 'admin',
          metadata: { invite_id: inviteId, role_id: invite.role_id }
        });
        console.log('[P0.7][Invite] revoked: ' + inviteId);
        if (typeof showToast === 'function') showToast('Invite revoked', 'info');
        return true;
      },

      getAll: function() {
        this._expireCheck();
        return this._invites;
      }
    };
"""

    c = apply_edit(c, 'EDIT-3: People Workspace (InviteManager)',
        "\n    var ContractIndex = {",
        PEOPLE_CODE + "\n    var ContractIndex = {")

    # =========================================================================
    # EDIT 4: Add People tab to admin panel tabs bar
    # =========================================================================
    c = apply_edit(c, 'EDIT-4: Add People tab button',
        """          <button class="admin-tab" data-admin-tab="unknown-cols" onclick="switchAdminTab('unknown-cols')" style="padding: 10px 20px; background: #f5f5f5; color: #666; border: none; border-radius: 6px 6px 0 0; cursor: pointer;">Unknown Cols</button>""",
        """          <button class="admin-tab" data-admin-tab="unknown-cols" onclick="switchAdminTab('unknown-cols')" style="padding: 10px 20px; background: #f5f5f5; color: #666; border: none; border-radius: 6px 6px 0 0; cursor: pointer;">Unknown Cols</button>
          <button class="admin-tab" data-admin-tab="people" onclick="switchAdminTab('people')" style="padding: 10px 20px; background: #f5f5f5; color: #666; border: none; border-radius: 6px 6px 0 0; cursor: pointer;">People</button>""")

    # =========================================================================
    # EDIT 5: Add People tab panel HTML before end of page-admin
    # =========================================================================
    PEOPLE_PANEL_HTML = """
        <!-- PEOPLE TAB (P0.7) -->
        <div id="admin-tab-people" class="admin-tab-panel" data-admin-section="true" style="display: none;">
          <!-- People Sub-Tabs -->
          <div style="display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid #e0e0e0;">
            <button class="people-sub-tab active" data-people-tab="members" onclick="switchPeopleTab('members')" style="padding: 8px 16px; background: #1976d2; color: white; border: none; border-radius: 4px 4px 0 0; cursor: pointer; font-size: 0.85em; font-weight: 600;">Members</button>
            <button class="people-sub-tab" data-people-tab="roles" onclick="switchPeopleTab('roles')" style="padding: 8px 16px; background: #f5f5f5; color: #666; border: none; border-radius: 4px 4px 0 0; cursor: pointer; font-size: 0.85em;">Roles</button>
            <button class="people-sub-tab" data-people-tab="invites" onclick="switchPeopleTab('invites')" style="padding: 8px 16px; background: #f5f5f5; color: #666; border: none; border-radius: 4px 4px 0 0; cursor: pointer; font-size: 0.85em;">Invites</button>
          </div>

          <!-- Members Sub-Panel -->
          <div id="people-tab-members" class="people-sub-panel" style="background: white; padding: 16px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4 style="margin: 0 0 12px; font-size: 0.95em; color: #333;">Members</h4>
            <div id="people-members-table"></div>
          </div>

          <!-- Roles Sub-Panel -->
          <div id="people-tab-roles" class="people-sub-panel" style="display: none; background: white; padding: 16px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4 style="margin: 0 0 12px; font-size: 0.95em; color: #333;">Role Configuration <span style="font-size: 0.75em; color: #999;">(Architect-only edit)</span></h4>
            <div id="people-roles-table"></div>
          </div>

          <!-- Invites Sub-Panel -->
          <div id="people-tab-invites" class="people-sub-panel" style="display: none; background: white; padding: 16px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4 style="margin: 0 0 12px; font-size: 0.95em; color: #333;">Invites</h4>
            <div id="people-invite-form" style="margin-bottom: 16px; padding: 12px; background: #f9f9f9; border-radius: 6px; border: 1px solid #eee;">
              <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-end;">
                <div>
                  <label style="font-size: 0.75em; color: #666; display: block;">Role</label>
                  <select id="invite-role-select" style="padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85em;">
                    <option value="analyst">Analyst</option>
                    <option value="verifier">Verifier</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label style="font-size: 0.75em; color: #666; display: block;">Expiry (hours)</label>
                  <input type="number" id="invite-expiry-input" placeholder="optional" style="padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85em; width: 80px;">
                </div>
                <div>
                  <label style="font-size: 0.75em; color: #666; display: block;">Note</label>
                  <input type="text" id="invite-note-input" placeholder="optional" style="padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85em; width: 140px;">
                </div>
                <button onclick="createInviteFromForm()" style="padding: 6px 14px; font-size: 0.85em; background: #4caf50; color: white; border: none; border-radius: 4px; cursor: pointer;">Create Invite</button>
              </div>
            </div>
            <div id="people-invites-table"></div>
          </div>
        </div><!-- end admin-tab-people -->
"""

    c = apply_edit(c, 'EDIT-5: People tab panel HTML',
        "        </div><!-- end admin-tab-inspector -->",
        "        </div><!-- end admin-tab-inspector -->\n" + PEOPLE_PANEL_HTML)

    # =========================================================================
    # EDIT 6: Add Truth Config controls section in admin panel (after architect controls)
    # =========================================================================
    c = apply_edit(c, 'EDIT-6: Truth Config controls HTML in admin',
        '          <div id="truth-pack-admin-controls" style="display: none;"></div>\n        </div>',
        '          <div id="truth-pack-admin-controls" style="display: none;"></div>\n' +
        '          <div id="truth-config-controls" style="margin-top: 12px;"></div>\n' +
        '        </div>')

    # =========================================================================
    # EDIT 7: Update switchAdminTab to include 'people' tab
    # =========================================================================
    c = apply_edit(c, 'EDIT-7: switchAdminTab includes people',
        "      const tabs = ['governance', 'users', 'patch-queue', 'config', 'inspector', 'standardizer', 'patch-console', 'evidence', 'unknown-cols'];",
        "      var tabs = ['governance', 'users', 'patch-queue', 'config', 'inspector', 'standardizer', 'patch-console', 'evidence', 'unknown-cols', 'people'];")

    # =========================================================================
    # EDIT 8: Add People workspace JS functions (switchPeopleTab, render functions)
    # Insert after migrateRoleLegacy function in the ROLE_REGISTRY block
    # =========================================================================
    PEOPLE_JS = """
    // P0.7: People workspace functions
    function switchPeopleTab(tabName) {
      var subTabs = ['members', 'roles', 'invites'];
      for (var ti = 0; ti < subTabs.length; ti++) {
        var panel = document.getElementById('people-tab-' + subTabs[ti]);
        if (panel) panel.style.display = (subTabs[ti] === tabName) ? '' : 'none';
      }
      var btns = document.querySelectorAll('.people-sub-tab');
      for (var bi = 0; bi < btns.length; bi++) {
        var btn = btns[bi];
        var isActive = btn.getAttribute('data-people-tab') === tabName;
        btn.style.background = isActive ? '#1976d2' : '#f5f5f5';
        btn.style.color = isActive ? 'white' : '#666';
        btn.style.fontWeight = isActive ? '600' : '400';
      }
      if (tabName === 'members') renderPeopleMembers();
      if (tabName === 'roles') renderPeopleRoles();
      if (tabName === 'invites') renderPeopleInvites();
      localStorage.setItem('people_active_tab', tabName);
    }

    function renderPeopleMembers() {
      var container = document.getElementById('people-members-table');
      if (!container) return;
      var users = getDemoUsers();
      var html = '<table style="width: 100%; border-collapse: collapse; font-size: 0.85em;">' +
        '<thead style="background: #f5f5f5;"><tr>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Name</th>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Email</th>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Role</th>' +
        '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #e0e0e0;">Status</th>' +
        '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #e0e0e0;">Assign</th>' +
        '</tr></thead><tbody>';
      for (var ui = 0; ui < users.length; ui++) {
        var u = users[ui];
        html += '<tr style="border-bottom: 1px solid #f0f0f0;">' +
          '<td style="padding: 6px 8px;">' + (u.name || '—') + '</td>' +
          '<td style="padding: 6px 8px;">' + (u.email || '—') + '</td>' +
          '<td style="padding: 6px 8px;">' + getRoleDisplayName(u.role || 'analyst') + '</td>' +
          '<td style="padding: 6px 8px; text-align: center;"><span style="padding: 2px 6px; border-radius: 8px; font-size: 0.8em; background: ' + (u.status === 'active' ? '#e8f5e9' : '#fff3e0') + ';">' + (u.status || 'active') + '</span></td>' +
          '<td style="padding: 6px 8px; text-align: center;">' +
          '<select onchange="assignMemberRole(\'' + u.id + '\', this.value)" style="padding: 3px 6px; font-size: 0.85em; border: 1px solid #ddd; border-radius: 4px;">' +
          '<option value="analyst"' + (u.role === 'analyst' ? ' selected' : '') + '>Analyst</option>' +
          '<option value="verifier"' + (u.role === 'verifier' ? ' selected' : '') + '>Verifier</option>' +
          '<option value="admin"' + (u.role === 'admin' ? ' selected' : '') + '>Admin</option>' +
          '</select></td></tr>';
      }
      html += '</tbody></table>';
      container.innerHTML = html;
    }

    function assignMemberRole(userId, newRole) {
      var users = getDemoUsers();
      for (var i = 0; i < users.length; i++) {
        if (users[i].id === userId) {
          users[i].role = newRole;
          break;
        }
      }
      saveDemoUsers(users);
      AuditTimeline.emit('member_role_assigned', {
        actor_role: TruthPack.isArchitect() ? 'architect' : 'admin',
        metadata: { user_id: userId, new_role: newRole }
      });
      console.log('[P0.7][People] role_assigned: user=' + userId + ' role=' + newRole);
      if (typeof showToast === 'function') showToast('Role updated to ' + getRoleDisplayName(newRole), 'success');
      renderPeopleMembers();
    }

    function renderPeopleRoles() {
      var container = document.getElementById('people-roles-table');
      if (!container) return;
      var reg = getRoleRegistry();
      var isArch = TruthPack.isArchitect();
      var roleIds = ['architect', 'admin', 'verifier', 'analyst'];
      var html = '<table style="width: 100%; border-collapse: collapse; font-size: 0.85em;">' +
        '<thead style="background: #f5f5f5;"><tr>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Role ID</th>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Display Name</th>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Permissions</th>' +
        '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #e0e0e0;">Active</th>' +
        '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #e0e0e0;">Actions</th>' +
        '</tr></thead><tbody>';
      for (var ri = 0; ri < roleIds.length; ri++) {
        var role = reg[roleIds[ri]];
        if (!role) continue;
        html += '<tr style="border-bottom: 1px solid #f0f0f0;">' +
          '<td style="padding: 6px 8px; font-family: monospace; font-size: 0.85em;">' + role.role_id + '</td>' +
          '<td style="padding: 6px 8px;">' + (isArch ? '<input type="text" value="' + (role.display_name || '') + '" onchange="updateRoleDisplayName(\'' + role.role_id + '\', this.value)" style="padding: 3px 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; width: 120px;">' : role.display_name) + '</td>' +
          '<td style="padding: 6px 8px; font-size: 0.8em; color: #555;">' + (role.permissions || []).join(', ') + '</td>' +
          '<td style="padding: 6px 8px; text-align: center;">' +
          (isArch ? '<input type="checkbox"' + (role.active ? ' checked' : '') + ' onchange="toggleRoleActive(\'' + role.role_id + '\', this.checked)">' : (role.active ? 'Yes' : 'No')) + '</td>' +
          '<td style="padding: 6px 8px; text-align: center;">' + (isArch ? '<span style="font-size: 0.75em; color: #999;">editable</span>' : '<span style="font-size: 0.75em; color: #ccc;">locked</span>') + '</td>' +
          '</tr>';
      }
      html += '</tbody></table>';
      container.innerHTML = html;
    }

    function updateRoleDisplayName(roleId, newName) {
      if (!TruthPack.isArchitect()) {
        if (typeof showToast === 'function') showToast('Architect role required to edit roles', 'error');
        return;
      }
      var reg = getRoleRegistry();
      if (reg[roleId]) {
        reg[roleId].display_name = newName;
        saveRoleRegistry(reg);
        AuditTimeline.emit('role_display_updated', {
          actor_role: 'architect',
          metadata: { role_id: roleId, new_display_name: newName }
        });
        console.log('[P0.7][Roles] display_name_updated: ' + roleId + ' -> ' + newName);
        if (typeof showToast === 'function') showToast('Role display name updated', 'success');
      }
    }

    function toggleRoleActive(roleId, active) {
      if (!TruthPack.isArchitect()) {
        if (typeof showToast === 'function') showToast('Architect role required', 'error');
        return;
      }
      var reg = getRoleRegistry();
      if (reg[roleId]) {
        reg[roleId].active = active;
        saveRoleRegistry(reg);
        console.log('[P0.7][Roles] toggle_active: ' + roleId + ' = ' + active);
      }
    }

    function renderPeopleInvites() {
      var container = document.getElementById('people-invites-table');
      if (!container) return;
      var invites = InviteManager.getAll();
      if (invites.length === 0) {
        container.innerHTML = '<div style="padding: 12px; color: #999; font-size: 0.85em; text-align: center;">No invites created yet.</div>';
        return;
      }
      var html = '<table style="width: 100%; border-collapse: collapse; font-size: 0.85em;">' +
        '<thead style="background: #f5f5f5;"><tr>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Invite ID</th>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Role</th>' +
        '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #e0e0e0;">Status</th>' +
        '<th style="padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0;">Note</th>' +
        '<th style="padding: 8px; text-align: center; border-bottom: 1px solid #e0e0e0;">Actions</th>' +
        '</tr></thead><tbody>';
      for (var ii = invites.length - 1; ii >= 0; ii--) {
        var inv = invites[ii];
        var statusColor = inv.status === 'active' ? '#4caf50' : (inv.status === 'used' ? '#1976d2' : (inv.status === 'expired' ? '#ff9800' : '#9e9e9e'));
        html += '<tr style="border-bottom: 1px solid #f0f0f0;">' +
          '<td style="padding: 6px 8px; font-family: monospace; font-size: 0.8em;">' + (inv.invite_id || '').substr(0, 18) + '</td>' +
          '<td style="padding: 6px 8px;">' + getRoleDisplayName(inv.role_id) + '</td>' +
          '<td style="padding: 6px 8px; text-align: center;"><span style="padding: 2px 6px; border-radius: 8px; font-size: 0.8em; color: white; background: ' + statusColor + ';">' + inv.status + '</span></td>' +
          '<td style="padding: 6px 8px; font-size: 0.8em; color: #666;">' + (inv.note || '—') + (inv.used_by ? ' (used by ' + inv.used_by + ')' : '') + '</td>' +
          '<td style="padding: 6px 8px; text-align: center;">' +
          (inv.status === 'active' ? '<button onclick="InviteManager.revokeInvite(\'' + inv.invite_id + '\'); renderPeopleInvites();" style="padding: 2px 8px; font-size: 0.78em; background: #f44336; color: white; border: none; border-radius: 3px; cursor: pointer;">Revoke</button>' : '—') +
          '</td></tr>';
      }
      html += '</tbody></table>';
      container.innerHTML = html;
    }

    function createInviteFromForm() {
      var roleSelect = document.getElementById('invite-role-select');
      var expiryInput = document.getElementById('invite-expiry-input');
      var noteInput = document.getElementById('invite-note-input');
      var roleId = roleSelect ? roleSelect.value : 'analyst';
      var expiry = expiryInput ? parseInt(expiryInput.value, 10) : 0;
      var note = noteInput ? noteInput.value : '';
      InviteManager.createInvite(roleId, expiry || 0, note);
      if (expiryInput) expiryInput.value = '';
      if (noteInput) noteInput.value = '';
      renderPeopleInvites();
    }
"""

    # Insert after migrateRoleLegacy closing brace
    c = apply_edit(c, 'EDIT-8: People workspace JS functions',
        "        console.log('[P0.7][MIGRATE] Legacy role labels migrated to stable IDs');\n      }\n    }",
        "        console.log('[P0.7][MIGRATE] Legacy role labels migrated to stable IDs');\n      }\n    }\n" + PEOPLE_JS)

    # =========================================================================
    # EDIT 9: Initialize modules on page load
    # Hook into TruthPack.restoreFromStorage or DOMContentLoaded init
    # =========================================================================
    c = apply_edit(c, 'EDIT-9: Init P0.7 modules on restore',
        "        this._renderControls();\n        this._renderCalibrationPanel();\n      }\n    };\n\n    var ContractIndex = {",
        "        this._renderControls();\n        this._renderCalibrationPanel();\n      }\n    };\n\n    // P0.7 init\n    migrateRoleLegacy();\n    InviteManager.init();\n    SessionDB.init().then(function() {\n      TruthConfig.init().then(function() { TruthConfig._renderUI(); });\n    });\n\n    var ContractIndex = {")

    # =========================================================================
    # EDIT 10: switchAdminTab - render People tab and TruthConfig
    # =========================================================================
    c = apply_edit(c, 'EDIT-10: switchAdminTab renders people + truth config',
        "      if (tabName === 'users') {\n        renderUsersTable();\n        updateEnvModeUI();\n      }",
        "      if (tabName === 'users') {\n        renderUsersTable();\n        updateEnvModeUI();\n      }\n      if (tabName === 'people') {\n        var savedPTab = localStorage.getItem('people_active_tab') || 'members';\n        switchPeopleTab(savedPTab);\n      }\n      if (typeof TruthConfig !== 'undefined') TruthConfig._renderUI();")

    # =========================================================================
    # EDIT 11: Fix ES5 issues in switchAdminTab (arrow functions -> function())
    # =========================================================================
    c = apply_edit(c, 'EDIT-11a: ES5 fix arrow in querySelectorAll panels',
        "      document.querySelectorAll('.admin-tab-panel').forEach(panel => {\n        panel.style.display = 'none';\n      });",
        "      var _panels = document.querySelectorAll('.admin-tab-panel');\n      for (var _pi = 0; _pi < _panels.length; _pi++) {\n        _panels[_pi].style.display = 'none';\n      }")

    # Fix the includes() call  
    c = apply_edit(c, 'EDIT-11b: ES5 fix includes() in switchAdminTab',
        "      if (!tabs.includes(tabName)) tabName = 'governance';",
        "      if (tabs.indexOf(tabName) === -1) tabName = 'governance';",
        required=False)

    # =========================================================================
    # EDIT 12: Fix remaining arrow functions in switchAdminTab
    # =========================================================================
    old_arrow = "      document.querySelectorAll('.admin-tab').forEach(btn => {"
    if old_arrow in c:
        # Find the full block
        idx = c.index(old_arrow)
        # Read the next ~200 chars to find the closing
        block_end_search = c[idx:idx+500]
        # Replace the forEach with a for loop
        c = apply_edit(c, 'EDIT-12: ES5 fix arrow in tab buttons',
            old_arrow,
            "      var _tabBtns = document.querySelectorAll('.admin-tab');\n      for (var _tbi = 0; _tbi < _tabBtns.length; _tbi++) { var btn = _tabBtns[_tbi];")
    else:
        print('  [SKIP] EDIT-12: ES5 fix arrow in tab buttons')

    # =========================================================================
    # EDIT 13: Add truth-config-status-chip to triage calibration panel header
    # =========================================================================
    c = apply_edit(c, 'EDIT-13: Truth Config status chip in calibration panel',
        "'<strong>Truth Pack Mode</strong> — Upload a dataset to begin calibration run. No sample data loaded.' +",
        "'<strong>Truth Pack Mode</strong> <span id=\"truth-config-chip-triage\" style=\"font-size: 0.85em; padding: 2px 6px; border-radius: 8px; background: ' + ((typeof TruthConfig !== 'undefined' && TruthConfig.getStatus() === 'established') ? '#4caf50' : (typeof TruthConfig !== 'undefined' && TruthConfig.getStatus() === 'test_mode') ? '#ff9800' : '#9e9e9e') + '; color: white;\">' + ((typeof TruthConfig !== 'undefined') ? (TruthConfig.getStatus() === 'established' ? 'Established' : (TruthConfig.getStatus() === 'test_mode' ? 'Test Mode' : 'No Baseline')) : 'No Baseline') + '</span>' +\n            ' — Upload a dataset to begin calibration run. No sample data loaded.' +")

    # =========================================================================
    # Final: Write and report
    # =========================================================================
    write_html(c)
    new_len = len(c)
    print(f'\n[P0.7] Done. Original: {original_len} chars, New: {new_len} chars, Delta: +{new_len - original_len}')

if __name__ == '__main__':
    main()
