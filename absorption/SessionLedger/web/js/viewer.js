// SessionLedger viewer — real API integration with session replay.
//
// Endpoints consumed:
//   GET /api/bundles          — full OKF documents as JSON array
//   GET /api/search?...       — BundleMeta objects with filters
//   GET /api/replay/:id       — SSE stream of entities for a bundle

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  var allBundles = [];
  var filteredBundles = [];
  var selectedBundleId = null;
  var jsonViewActive = false;

  // ---------------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------------
  var searchInput, modelFilter, tagFilter, sortSelect;
  var statusText, resultCount;
  var sessionsContainer, errorContainer;
  var detailPanel, detailTitle, detailMeta, entityList;
  var relationsSection, relationList;
  var jsonView, jsonContent, toggleJsonBtn, closeDetailBtn;

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    searchInput = document.getElementById('search-input');
    modelFilter = document.getElementById('model-filter');
    tagFilter = document.getElementById('tag-filter');
    sortSelect = document.getElementById('sort-select');
    statusText = document.getElementById('status-text');
    resultCount = document.getElementById('result-count');
    sessionsContainer = document.getElementById('sessions-container');
    errorContainer = document.getElementById('error-container');
    detailPanel = document.getElementById('detail-panel');
    detailTitle = document.getElementById('detail-title');
    detailMeta = document.getElementById('detail-meta');
    entityList = document.getElementById('entity-list');
    relationsSection = document.getElementById('relations-section');
    relationList = document.getElementById('relation-list');
    jsonView = document.getElementById('json-view');
    jsonContent = document.getElementById('json-content');
    toggleJsonBtn = document.getElementById('toggle-json');
    closeDetailBtn = document.getElementById('close-detail');

    if (!sessionsContainer) return;

    fetchBundles();

    // Filter / sort event listeners
    searchInput.addEventListener('input', applyFilters);
    modelFilter.addEventListener('change', applyFilters);
    tagFilter.addEventListener('change', applyFilters);
    sortSelect.addEventListener('change', applyFilters);

    // Detail panel controls
    closeDetailBtn.addEventListener('click', closeDetail);
    toggleJsonBtn.addEventListener('click', toggleJsonView);
  }

  // ---------------------------------------------------------------------------
  // Fetch bundles from the daemon
  // ---------------------------------------------------------------------------
  function fetchBundles() {
    showLoading('Fetching bundles from daemon...');
    hideError();

    fetch('/api/bundles')
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status + ' ' + res.statusText);
        return res.json();
      })
      .then(function (data) {
        if (!Array.isArray(data)) {
          allBundles = [];
        } else {
          allBundles = data.map(normalizeBundle);
        }
        populateFilterOptions();
        applyFilters();
        updateStatus('Bundles loaded');
      })
      .catch(function (err) {
        showError(
          'Could not connect to the SessionLedger daemon.',
          'Make sure sl-daemon is running: sl-daemon serve --out ./okf-out --http-bind 127.0.0.1:8080\n\nError: ' + err.message
        );
        updateStatus('Connection failed');
      });
  }

  // ---------------------------------------------------------------------------
  // Normalize a raw OKF document into a display-friendly shape.
  // The /api/bundles endpoint returns raw OkfDocument values which have
  // source_id, entities, provenance, tags. BundleMeta is only from /api/search.
  // We derive display fields from the raw document.
  // ---------------------------------------------------------------------------
  function normalizeBundle(doc) {
    var sessionId = doc.source_id || doc.session_id || doc.id || '';
    var createdAt = doc.created_at || doc.timestamp || doc.created || '';
    var model = doc.model || doc.model_id || '';
    var tokenCount = doc.token_count || 0;
    var messageCount = doc.message_count || 0;
    var durationMs = doc.duration_ms || 0;
    var tags = Array.isArray(doc.tags) ? doc.tags : [];
    var entities = Array.isArray(doc.entities) ? doc.entities : [];
    var relations = Array.isArray(doc.relations) ? doc.relations : [];
    var provenance = doc.provenance || {};
    var corpus = provenance.corpus || '';

    // Try to extract metadata from nested locations
    if (!createdAt && doc.metadata) createdAt = doc.metadata.created_at || doc.metadata.timestamp || '';
    if (!model && doc.metadata) model = doc.metadata.model || doc.metadata.model_id || '';
    if (!tokenCount && doc.usage) tokenCount = doc.usage.total_tokens || 0;

    return {
      session_id: sessionId,
      created_at: createdAt,
      model: model,
      token_count: tokenCount,
      message_count: messageCount || entities.length,
      duration_ms: durationMs,
      tags: tags,
      corpus: corpus,
      entities: entities,
      relations: relations,
      provenance: provenance,
      _raw: doc
    };
  }

  // ---------------------------------------------------------------------------
  // Populate model and tag filter dropdowns from loaded data
  // ---------------------------------------------------------------------------
  function populateFilterOptions() {
    var models = {};
    var tags = {};

    allBundles.forEach(function (b) {
      if (b.model) models[b.model] = true;
      b.tags.forEach(function (t) { tags[t] = true; });
    });

    // Model filter
    var modelHtml = '<option value="">All models</option>';
    Object.keys(models).sort().forEach(function (m) {
      modelHtml += '<option value="' + escapeHtml(m) + '">' + escapeHtml(m) + '</option>';
    });
    modelFilter.innerHTML = modelHtml;

    // Tag filter
    var tagHtml = '<option value="">All tags</option>';
    Object.keys(tags).sort().forEach(function (t) {
      tagHtml += '<option value="' + escapeHtml(t) + '">' + escapeHtml(t) + '</option>';
    });
    tagFilter.innerHTML = tagHtml;
  }

  // ---------------------------------------------------------------------------
  // Apply all active filters and render
  // ---------------------------------------------------------------------------
  function applyFilters() {
    var query = searchInput.value.trim().toLowerCase();
    var model = modelFilter.value;
    var tag = tagFilter.value;
    var sort = sortSelect.value;

    filteredBundles = allBundles.filter(function (b) {
      // Text search on session_id, source_id, corpus
      if (query) {
        var haystack = (b.session_id + ' ' + b.corpus + ' ' + (b.provenance.source_id || '')).toLowerCase();
        if (haystack.indexOf(query) === -1) return false;
      }
      // Model filter
      if (model && b.model !== model) return false;
      // Tag filter (AND: bundle must contain the selected tag)
      if (tag && b.tags.indexOf(tag) === -1) return false;
      return true;
    });

    // Sort
    filteredBundles.sort(function (a, b) {
      switch (sort) {
        case 'newest':
          return (b.created_at || '').localeCompare(a.created_at || '');
        case 'oldest':
          return (a.created_at || '').localeCompare(b.created_at || '');
        case 'tokens-desc':
          return (b.token_count || 0) - (a.token_count || 0);
        case 'tokens-asc':
          return (a.token_count || 0) - (b.token_count || 0);
        case 'messages-desc':
          return (b.message_count || 0) - (a.message_count || 0);
        default:
          return 0;
      }
    });

    renderTable();
  }

  // ---------------------------------------------------------------------------
  // Render the session table
  // ---------------------------------------------------------------------------
  function renderTable() {
    if (filteredBundles.length === 0) {
      if (allBundles.length === 0) {
        sessionsContainer.innerHTML =
          '<div class="empty-state">' +
          '<p>No bundles found.</p>' +
          '<p>Start the daemon to begin capturing sessions:</p>' +
          '<code>sl-daemon serve --out ./okf-out --http-bind 127.0.0.1:8080</code>' +
          '</div>';
      } else {
        sessionsContainer.innerHTML =
          '<div class="empty-state">' +
          '<p>No bundles match the current filters.</p>' +
          '</div>';
      }
      resultCount.textContent = '0 results';
      return;
    }

    var html = '<table class="data" id="sessions"><thead><tr>' +
      '<th>Session ID</th>' +
      '<th>Source</th>' +
      '<th>Created</th>' +
      '<th>Model</th>' +
      '<th>Tokens</th>' +
      '<th>Events</th>' +
      '<th>Duration</th>' +
      '<th>Tags</th>' +
      '</tr></thead><tbody>';

    filteredBundles.forEach(function (b, idx) {
      var selected = b.session_id === selectedBundleId ? ' class="selected"' : '';
      html += '<tr data-idx="' + idx + '"' + selected + '>' +
        '<td>' + escapeHtml(b.session_id || '(unknown)') + '</td>' +
        '<td>' + escapeHtml(b.corpus || b.provenance.corpus || '') + '</td>' +
        '<td>' + formatTimestamp(b.created_at) + '</td>' +
        '<td>' + escapeHtml(b.model || '-') + '</td>' +
        '<td>' + formatNumber(b.token_count) + '</td>' +
        '<td>' + formatNumber(b.message_count) + '</td>' +
        '<td>' + formatDuration(b.duration_ms) + '</td>' +
        '<td>' + renderTags(b.tags) + '</td>' +
        '</tr>';
    });

    html += '</tbody></table>';
    sessionsContainer.innerHTML = html;

    resultCount.textContent = filteredBundles.length + ' of ' + allBundles.length + ' bundles';

    // Attach click handlers
    var rows = sessionsContainer.querySelectorAll('tbody tr');
    for (var i = 0; i < rows.length; i++) {
      rows[i].addEventListener('click', handleRowClick);
    }
  }

  // ---------------------------------------------------------------------------
  // Handle row click — open detail view
  // ---------------------------------------------------------------------------
  function handleRowClick(e) {
    var row = e.currentTarget;
    var idx = parseInt(row.getAttribute('data-idx'), 10);
    var bundle = filteredBundles[idx];
    if (!bundle) return;

    selectedBundleId = bundle.session_id;
    jsonViewActive = false;
    jsonView.hidden = true;
    document.getElementById('detail-view').hidden = false;
    toggleJsonBtn.classList.remove('active');

    showDetail(bundle);

    // Highlight selected row
    var allRows = sessionsContainer.querySelectorAll('tbody tr');
    for (var i = 0; i < allRows.length; i++) {
      allRows[i].classList.remove('selected');
    }
    row.classList.add('selected');
  }

  // ---------------------------------------------------------------------------
  // Show the detail panel for a bundle
  // ---------------------------------------------------------------------------
  function showDetail(bundle) {
    detailPanel.hidden = false;
    detailTitle.textContent = bundle.session_id || 'Session Detail';

    // Metadata grid
    detailMeta.innerHTML =
      '<dl>' +
      '<dt>Session ID</dt><dd>' + escapeHtml(bundle.session_id) + '</dd>' +
      '<dt>Source</dt><dd>' + escapeHtml(bundle.corpus || '-') + '</dd>' +
      '<dt>Created</dt><dd>' + formatTimestamp(bundle.created_at) + '</dd>' +
      '<dt>Model</dt><dd>' + escapeHtml(bundle.model || '-') + '</dd>' +
      '<dt>Tokens</dt><dd>' + formatNumber(bundle.token_count) + '</dd>' +
      '<dt>Messages</dt><dd>' + formatNumber(bundle.message_count) + '</dd>' +
      '<dt>Duration</dt><dd>' + formatDuration(bundle.duration_ms) + '</dd>' +
      '<dt>Tags</dt><dd>' + (bundle.tags.length ? renderTags(bundle.tags) : '<span style="color:var(--fg-dim)">none</span>') + '</dd>' +
      '<dt>Provenance</dt><dd>' + escapeHtml(bundle.provenance.corpus || '-') + ' / ' + escapeHtml(bundle.provenance.source_id || '-') + '</dd>' +
      '</dl>';

    // Entities
    if (bundle.entities.length > 0) {
      var entityHtml = '';
      bundle.entities.forEach(function (entity, i) {
        var typeClass = getTypeClass(entity.type);
        var propsStr = '';
        if (entity.properties && typeof entity.properties === 'object' && Object.keys(entity.properties).length > 0) {
          propsStr = '<div class="entity-props">' + escapeHtml(JSON.stringify(entity.properties, null, 2)) + '</div>';
        }
        entityHtml +=
          '<div class="entity-card">' +
          '<span class="entity-type ' + typeClass + '">' + escapeHtml(entity.type) + '</span>' +
          '<span class="entity-label">' + escapeHtml(entity.label || '') + '</span>' +
          '<div class="entity-id">' + escapeHtml(entity.id) + '</div>' +
          propsStr +
          '</div>';
      });
      entityList.innerHTML = entityHtml;
      document.getElementById('detail-entities').querySelector('h3').textContent =
        'Entities (' + bundle.entities.length + ')';
    } else {
      entityList.innerHTML = '<p style="color:var(--fg-dim)">No entities in this bundle.</p>';
      document.getElementById('detail-entities').querySelector('h3').textContent = 'Entities';
    }

    // Relations
    if (bundle.relations && bundle.relations.length > 0) {
      relationsSection.hidden = false;
      var relHtml = '';
      bundle.relations.forEach(function (rel) {
        relHtml +=
          '<div class="relation-row">' +
          '<span>' + escapeHtml(rel.source) + '</span>' +
          '<span class="relation-arrow">&rarr;</span>' +
          '<span class="relation-type">' + escapeHtml(rel.type) + '</span>' +
          '<span class="relation-arrow">&rarr;</span>' +
          '<span>' + escapeHtml(rel.target) + '</span>' +
          '</div>';
      });
      relationList.innerHTML = relHtml;
    } else {
      relationsSection.hidden = true;
      relationList.innerHTML = '';
    }

    // Raw JSON (hidden by default)
    jsonContent.textContent = JSON.stringify(bundle._raw, null, 2);

    // Scroll detail into view
    detailPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ---------------------------------------------------------------------------
  // Close the detail panel
  // ---------------------------------------------------------------------------
  function closeDetail() {
    detailPanel.hidden = true;
    selectedBundleId = null;
    jsonViewActive = false;

    var allRows = sessionsContainer.querySelectorAll('tbody tr');
    for (var i = 0; i < allRows.length; i++) {
      allRows[i].classList.remove('selected');
    }
  }

  // ---------------------------------------------------------------------------
  // Toggle between structured view and raw JSON
  // ---------------------------------------------------------------------------
  function toggleJsonView() {
    jsonViewActive = !jsonViewActive;
    jsonView.hidden = !jsonViewActive;
    document.getElementById('detail-view').hidden = jsonViewActive;
    toggleJsonBtn.classList.toggle('active', jsonViewActive);
  }

  // ---------------------------------------------------------------------------
  // UI helpers
  // ---------------------------------------------------------------------------
  function showLoading(msg) {
    sessionsContainer.innerHTML = '<div class="loading">' + escapeHtml(msg) + '</div>';
  }

  function updateStatus(msg) {
    statusText.textContent = msg;
  }

  function showError(title, detail) {
    errorContainer.hidden = false;
    errorContainer.innerHTML =
      '<div class="error-state">' +
      '<p>' + escapeHtml(title) + '</p>' +
      (detail ? '<code>' + escapeHtml(detail) + '</code>' : '') +
      '</div>';
  }

  function hideError() {
    errorContainer.hidden = true;
    errorContainer.innerHTML = '';
  }

  // ---------------------------------------------------------------------------
  // Formatting helpers
  // ---------------------------------------------------------------------------
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    var s = String(str);
    return s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatNumber(n) {
    if (!n) return '0';
    return Number(n).toLocaleString();
  }

  function formatTimestamp(ts) {
    if (!ts) return '-';
    try {
      var d = new Date(ts);
      if (isNaN(d.getTime())) return escapeHtml(ts);
      var year = d.getFullYear();
      var month = String(d.getMonth() + 1).padStart(2, '0');
      var day = String(d.getDate()).padStart(2, '0');
      var hours = String(d.getHours()).padStart(2, '0');
      var mins = String(d.getMinutes()).padStart(2, '0');
      return year + '-' + month + '-' + day + ' ' + hours + ':' + mins;
    } catch (_) {
      return escapeHtml(ts);
    }
  }

  function formatDuration(ms) {
    if (!ms) return '-';
    if (ms < 1000) return ms + 'ms';
    var secs = ms / 1000;
    if (secs < 60) return secs.toFixed(1) + 's';
    var mins = Math.floor(secs / 60);
    var remSecs = Math.floor(secs % 60);
    return mins + 'm ' + remSecs + 's';
  }

  function renderTags(tags) {
    if (!tags || tags.length === 0) return '';
    return tags.map(function (t) {
      return '<span class="tag-badge">' + escapeHtml(t) + '</span>';
    }).join('');
  }

  function getTypeClass(type) {
    if (!type) return '';
    var t = type.toLowerCase();
    if (t === 'intent') return 'intent';
    if (t === 'resource') return 'resource';
    if (t === 'state') return 'state';
    if (t === 'criteria') return 'criteria';
    if (t === 'gate') return 'gate';
    return '';
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', init);
})();
