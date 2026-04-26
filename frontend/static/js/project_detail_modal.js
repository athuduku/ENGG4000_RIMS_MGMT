// project_detail_modal.js

let currentProjectId = null;
let currentUserType  = null;
const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

// ── Per-project cache (invalidated on any mutation) ───────────
const projectCache = {};

function invalidateCache(projectId) {
  delete projectCache[projectId];
}

// ── Helpers ───────────────────────────────────────────────────
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function showEl(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'block';
}

function hideEl(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

function setSection(sectionId, value, populateFn) {
  const el = document.getElementById(sectionId);
  if (!el) return;
  if (value) { el.style.display = 'block'; populateFn(); }
  else        { el.style.display = 'none'; }
}

function fmtMoney(n) {
  return n ? `$${Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '—';
}

// ── Modal tabs ────────────────────────────────────────────────
function activateProjectTab(tabId) {
    document.querySelectorAll('.project-tab-btn').forEach(btn =>
        btn.classList.toggle('active', btn.dataset.tab === tabId)
    );
    document.querySelectorAll('.project-tab-pane').forEach(pane =>
        pane.classList.toggle('active', pane.id === tabId)
    );

    if (tabId === 'teamTab') {
        loadExternalMembers(currentProjectId);
        loadTaggedMembers(currentProjectId);
    }

    if (tabId === 'outputsTab') {
        loadLinkedItems(currentProjectId);
    }

    if (tabId === 'fundingTab') {
      const cached = projectCache[currentProjectId];
      if (cached?.funding) {
          displayFundingRecords(
              cached.funding.funding_records,
              cached.funding.computed_total,
              window.currentProjectData?.funding_kept_by_unb
          );
      } else {
          fetch(`/api/project/${currentProjectId}/funding/`)
              .then(r => r.json())
              .then(data => {
                  // ← FIX: ensure cache entry exists before setting
                  if (!projectCache[currentProjectId]) {
                      projectCache[currentProjectId] = {};
                  }
                  projectCache[currentProjectId].funding = data;
                  displayFundingRecords(
                      data.funding_records,
                      data.computed_total,
                      data.funding_kept_by_unb
                  );
                  if (data.computed_total) {
                      setText('fundingTotalValue',    fmtMoney(data.computed_total));
                      setText('fundingReceivedValue', fmtMoney(data.computed_ibme));
                  }
              });
      }
  }
    
}

function resetProjectModalTabs() {
  activateProjectTab('overviewTab');
}

// ── Open modal ────────────────────────────────────────────────
// Phase 1: paint everything we already have from projectData instantly.
// Phase 2: fire the three API calls after the modal is visible.
function openProjectModal(projectData) {
  currentProjectId = projectData.id;
  window.currentProjectData = projectData;

  resetProjectModalTabs();

  // Title & status
  setText('projectTitle', projectData.title);

  const statusSelect = document.getElementById('projectStatusSelect');
  if (statusSelect && projectData.status) statusSelect.value = projectData.status;

  const statusBadge   = document.getElementById('projectStatus');
  const statusDisplay = document.getElementById('projectStatusDisplay');
  if (projectData.is_active) {
    const html = `<span class="status-badge status-active"><i class="bi bi-circle-fill" style="font-size:8px;"></i> Active</span>`;
    statusBadge.innerHTML = html;
    if (statusDisplay) statusDisplay.innerHTML = html;
  } else {
    const s    = projectData.status || 'completed';
    const nice = s.charAt(0).toUpperCase() + s.slice(1);
    const html = `<span class="status-badge status-${s}">${nice}</span>`;
    statusBadge.innerHTML = html;
    if (statusDisplay) statusDisplay.innerHTML = html;
  }

  // Header badges
  const ftEl = document.getElementById('projectFundingType');
  if (ftEl) {
    if (projectData.funding_type) {
      ftEl.innerHTML = `<span class="funding-type-badge">${projectData.funding_type}</span>`;
      ftEl.style.display = 'inline-block';
    } else {
      ftEl.style.display = 'none';
    }
  }
  document.getElementById('projectRole').innerHTML =
    `<span class="role-badge role-${projectData.role}">${projectData.role_display}</span>`;

  // Summary
  setSection('summarySection', projectData.summary, () =>
    setText('projectSummary', projectData.summary)
  );

  // Dates
  setText('projectStartDate', projectData.start_date || '-');
  setText('projectEndDate',   projectData.end_date   || '-');

  // Funding summary display + inputs
  setText('fundingOrgValue',      projectData.funding_organization || '—');
  setText('fundingTypeValue',     projectData.funding_type         || '—');
  setText('fundingTotalValue',    fmtMoney(projectData.total_funding));
  setText('fundingReceivedValue', fmtMoney(projectData.funding_received));
  setText('fundingStartValue',    projectData.start_date || '—');
  setText('fundingEndValue',      projectData.end_date   || '—');
  setVal('fundingOrgInput',      projectData.funding_organization || '');
  setVal('fundingTypeInput',     projectData.funding_type         || '');
  setVal('fundingTotalInput',    projectData.total_funding        || '');
  setVal('fundingReceivedInput', projectData.funding_received     || '');
  setVal('fundingStartInput',    projectData.start_date           || '');
  setVal('fundingEndInput',      projectData.end_date             || '');
  setText('fundingCurrencyValue', projectData.currency || 'CAD');

  // Kept by UNB
  const keptVal = projectData.funding_kept_by_unb;
  setText('keptByUnbValue', fmtMoney(keptVal));
  setVal('keptByUnbInput', keptVal || '');
  showEl('keptByUnbDisplay');
  hideEl('keptByUnbEdit');

  // Description
  setSection('descriptionSection', projectData.description, () =>
    setText('projectDescription', projectData.description)
  );

  // Conception
  const conceptionSection = document.getElementById('conceptionSection');
  if (conceptionSection) {
    if (currentUserType === 'student') {
      conceptionSection.style.display = 'none';
    } else {
      conceptionSection.style.display = 'block';
      const conception = projectData.conception || '';
      setText('projectConception', conception || 'No conception notes yet.');
      setVal('conceptionTextarea', conception);
      showEl('conceptionDisplay');
      hideEl('conceptionEdit');
    }
  }

  // Next steps
  const nextSteps = projectData.next_steps || '';
  setText('projectNextSteps', nextSteps || 'No next steps defined yet.');
  setVal('nextStepsTextarea', nextSteps);
  showEl('nextStepsDisplay');
  hideEl('nextStepsEdit');

  // IP activities
  const ipSection = document.getElementById('ipSection');
  if (ipSection) {
    ipSection.style.display = 'block';
    const ip = projectData.ip_activities || '';
    setText('projectIPActivities', ip || 'No IP activities recorded.');
    setVal('ipTextarea', ip);
    showEl('ipDisplay');
    hideEl('ipEdit');
  }

  function loadHQP(projectData) {
    requestAnimationFrame(() => {
      const tagged = projectData.tagged_members || [];

      const hqp = tagged.filter(m => m.is_hqp);

      document.getElementById('hqpSummary').innerHTML = `
        <div class="hqpSummaryVal">
          Total HQP: ${hqp.length}
        </div>
      `;


      setTimeout(() => {
        renderTaggedMembers(tagged);
      }, 0);
    });
  }

  // HQP summary — from projectData, no fetch needed
  const hqpSection = document.getElementById('hqpSection');
  if (hqpSection) {
    hqpSection.style.display = 'block';

    document.getElementById('hqpSummary').innerHTML = 'Loading HQP...';

    loadHQP(projectData);
  }

  // Loading placeholders for the three deferred sections
  const pubList = document.getElementById('linkedPublicationsList');
  if (pubList) pubList.innerHTML = '<p class="no-data-text">Loading...</p>';
  const actList = document.getElementById('linkedActivitiesList');
  if (actList) actList.innerHTML = '<p class="no-data-text">Loading...</p>';
  const memberList = document.getElementById('externalMembersList');
  if (memberList) memberList.innerHTML = '<p class="no-data-text">Loading...</p>';

  // Open modal — everything above is synchronous so this paints instantly
  const modal = document.getElementById('projectDetailModal');
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
  document.querySelector('.project-detail-content')?.scrollTo({ top: 0, behavior: 'instant' });

  // Defer the three API calls until after the browser has painted
  setTimeout(() => loadDeferredData(projectData), 0);
}

// ── Deferred data loading with cache ─────────────────────────
function loadDeferredData(projectData) {
  const id = projectData.id;

    if (projectCache[id]) {
        renderFromCache(projectCache[id], projectData);
        return;
    }

    const cache = projectCache[id] = {};


  fetch(`/api/projects/${id}/linked/`)
    .then(r => r.json())
    .then(data => {
      cache.linked = data;
      requestAnimationFrame(() => {
        renderLinkedPublications(data.publications || []);
        renderLinkedActivities(data.activities    || []);
      });
    })
    .catch(() => { renderLinkedPublications([]); renderLinkedActivities([]); });

  fetch(`/api/projects/${id}/team-members/`)
    .then(r => r.json())
    .then(data => {
      cache.members = data;
      requestAnimationFrame(() => renderExternalMembers(data.members || []));
    })
    .catch(() => renderExternalMembers([]));
}

function displayFundingRecords(fundingRecords, totalFunding, keptByUnb) {
  const container = document.getElementById('fundingRecordsContainer');
  if (!container) return;

  if (!fundingRecords || !fundingRecords.length) {
    container.innerHTML = '';
    return;
  }

  let totalReceived   = 0;
  let researcherTotal = 0;
  let grantTotalSum   = 0;

  container.innerHTML = fundingRecords.map((f, i) => {
    totalReceived   += parseFloat(f.amount_to_ibme) || 0;
    researcherTotal += parseFloat(f.amount)         || 0;
    grantTotalSum   += parseFloat(f.grant_total || f.amount) || 0;

    // Show researcher's portion in the record row, not the full project total
    const displayAmt = f.amount > 0 ? f.amount : (f.grant_total || 0);

    const label = f.organization
      ? `${f.funding_type ? f.funding_type + ' — ' : ''}${f.organization}`
      : `${f.funding_type ? f.funding_type + ' — ' : ''}Source ${i + 1}`;

    return `
      <div class="funding-record">
        <div class="funding-record-header">
          <span class="funding-record-label">${label}</span>
          <span class="funding-record-dates">${f.start_date || ''} to ${f.end_date || ''}</span>
        </div>
        <div class="funding-record-amount">${fmtMoney(displayAmt)}</div>
      </div>`;
  }).join('');

  // ── Determine display mode ────────────────────────────────────
  const isCoI     = researcherTotal === 0 && grantTotalSum > 0;
  const isPartial = researcherTotal > 0 && grantTotalSum > 0
                    && researcherTotal < grantTotalSum * 0.99;
  const isFull    = !isCoI && !isPartial;

  const displayTotal = isCoI ? grantTotalSum : researcherTotal;

  // Percentage against full project total, not researcher portion
  const pctBase = grantTotalSum > 0 ? grantTotalSum : displayTotal;
  const pct = pctBase > 0
    ? Math.min(Math.round((totalReceived / pctBase) * 100), 100)
    : 0;

  // Project total row — shown for partial Co-I grants
  const projectTotalRow = isPartial ? `
    <div class="funding-total-item">
      <span class="funding-total-label">Total project funding</span>
      <span class="funding-total-value" style="color:var(--muted);font-size:18px;">
        ${fmtMoney(grantTotalSum)}
      </span>
    </div>` : '';

  const totalLabel = isCoI
    ? 'Total project funding'
    : isPartial
      ? 'Researcher portion (CCV records)'
      : 'Total (from CCV records)';

  const allocationNote = isCoI ? `
    <div style="font-size:12px;color:#9ca3af;margin-top:4px;display:flex;align-items:center;gap:4px;">
      <i class="bi bi-info-circle" style="font-size:11px;"></i>
      Researcher's allocated portion: $0 — funds held by lead institution
    </div>` : '';

  container.innerHTML += `
    <div class="funding-totals">
      <div class="funding-totals-grid">
        ${projectTotalRow}
        <div class="funding-total-item">
          <span class="funding-total-label">${totalLabel}</span>
          <span class="funding-total-value">${fmtMoney(displayTotal)}</span>
          ${allocationNote}
        </div>
        <div class="funding-total-item">
          <span class="funding-total-label">Awarded to IBME</span>
          <span class="funding-total-value received">
            ${totalReceived > 0 ? fmtMoney(totalReceived) : '—'}
          </span>
        </div>
        ${keptByUnb ? `
        <div class="funding-total-item">
          <span class="funding-total-label">Kept by IBME</span>
          <span class="funding-total-value received">${fmtMoney(keptByUnb)}</span>
        </div>` : ''}
      </div>
      <div class="funding-progress-bar">
        <div class="funding-progress-fill" style="width:${pct}%"></div>
      </div>
      <span class="funding-percent-label">${pct}% Awarded to IBME</span>
    </div>`;
}

// ── Funding summary edit ──────────────────────────────────────
function editFundingSummary() { hideEl('fundingSummaryDisplay'); showEl('fundingSummaryEdit'); }
function cancelEditFunding()  { hideEl('fundingSummaryEdit'); showEl('fundingSummaryDisplay'); }

function saveFundingSummary() {
  const total    = parseFloat(document.getElementById('fundingTotalInput').value || 0);
  const received = parseFloat(document.getElementById('fundingReceivedInput').value || 0);

  if (total < 0) {
    showToast('Total funding cannot be negative.');
    return;
  }
  if (received < 0) {
    showToast('Awarded to IBME cannot be negative.');
    return;
  }
  if (received > total && total > 0) {
    showToast('Awarded to IBME cannot exceed total funding.');
    return;
  }

  const payload = {
    funding_organization: document.getElementById('fundingOrgInput').value.trim(),
    funding_type:         document.getElementById('fundingTypeInput').value.trim(),
    currency:             document.getElementById('fundingCurrencyInput').value || 'CAD',
    total_funding:        document.getElementById('fundingTotalInput').value    || null,
    funding_received:     document.getElementById('fundingReceivedInput').value || null,
    start_date:           document.getElementById('fundingStartInput').value    || null,
    end_date:             document.getElementById('fundingEndInput').value      || null,
  };


  fetch(`/api/projects/${currentProjectId}/update-funding/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify(payload),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        invalidateCache(currentProjectId);

        setText('fundingOrgValue',      payload.funding_organization || '—');
        setText('fundingTypeValue',     payload.funding_type         || '—');
        const curr = payload.currency === 'USD' ? 'USD ' : '';
        setText('fundingTotalValue',    curr + fmtMoney(payload.total_funding));
        setText('fundingReceivedValue', curr + fmtMoney(payload.funding_received));
        setText('fundingCurrencyValue', payload.currency || 'CAD');
        setVal('fundingCurrencyInput',  payload.currency || 'CAD');
        setText('fundingStartValue',    payload.start_date || '—');
        setText('fundingEndValue',      payload.end_date   || '—');
        setText('projectStartDate',     payload.start_date || '-');
        setText('projectEndDate',       payload.end_date   || '-');

        const ftEl = document.getElementById('projectFundingType');
        if (ftEl) {
          if (payload.funding_type) {
            ftEl.innerHTML = `<span class="funding-type-badge">${payload.funding_type}</span>`;
            ftEl.style.display = 'inline-block';
          } else {
            ftEl.style.display = 'none';
          }
        }
        cancelEditFunding();
      } else {
        showToast('Error saving: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(() => showToast('Error saving funding'));
}

// ── Kept by UNB ───────────────────────────────────────────────
function saveKeptByUnb() {
  const val = document.getElementById('keptByUnbInput').value;
  fetch(`/api/projects/${currentProjectId}/update-kept-by-unb/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ funding_kept_by_unb: val }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        invalidateCache(currentProjectId);
        setText('keptByUnbValue', fmtMoney(val));
        hideEl('keptByUnbEdit');
        showEl('keptByUnbDisplay');
      } else {
        showToast('Error saving: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(() => showToast('Error saving kept by IBME'));
}

// ── Conception ────────────────────────────────────────────────
function editConception()       { hideEl('conceptionDisplay'); showEl('conceptionEdit'); }
function cancelEditConception() { hideEl('conceptionEdit'); showEl('conceptionDisplay'); }

function saveConception() {
  const conception = document.getElementById('conceptionTextarea').value;
  fetch(`/api/projects/${currentProjectId}/update-conception/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ conception }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        setText('projectConception', conception || 'No conception notes yet.');
        cancelEditConception();
      } else {
        showToast('Error saving conception: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(() => showToast('Error saving conception'));
}

// ── Next steps ────────────────────────────────────────────────
function editNextSteps()       { hideEl('nextStepsDisplay'); showEl('nextStepsEdit'); }
function cancelEditNextSteps() { hideEl('nextStepsEdit'); showEl('nextStepsDisplay'); }

function saveNextSteps() {
  const nextSteps = document.getElementById('nextStepsTextarea').value;
  fetch(`/api/projects/${currentProjectId}/update-next-steps/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ next_steps: nextSteps }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        setText('projectNextSteps', nextSteps || 'No next steps defined yet.');
        cancelEditNextSteps();
      } else {
        showToast('Error saving next steps');
      }
    })
    .catch(() => showToast('Error saving next steps'));
}

// ── Close modal ───────────────────────────────────────────────
function closeProjectModal() {
  document.getElementById('projectDetailModal').classList.remove('active');
  document.body.style.overflow = '';
  currentProjectId = null;

  ['pubSearchInput', 'actSearchInput', 'hqpSearchInput'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['pubSearchResults', 'actSearchResults', 'hqpSearchResults'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });

  resetProjectModalTabs();
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeProjectModal();
});

// ── Wire up static buttons ────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  document.querySelector('.project-detail-overlay')?.addEventListener('click', closeProjectModal);
  document.getElementById('modalCloseBtn')?.addEventListener('click', closeProjectModal);

  document.querySelectorAll('.project-tab-btn').forEach(btn =>
    btn.addEventListener('click', function () { activateProjectTab(this.dataset.tab); })
  );

  // Funding summary
  document.getElementById('editFundingBtn')?.addEventListener('click', editFundingSummary);
  document.getElementById('saveFundingBtn')?.addEventListener('click', saveFundingSummary);
  document.getElementById('cancelFundingBtn')?.addEventListener('click', cancelEditFunding);

  // Kept by UNB
  document.getElementById('editKeptByUnbBtn')?.addEventListener('click', () => {
    hideEl('keptByUnbDisplay'); showEl('keptByUnbEdit');
  });
  document.getElementById('cancelKeptByUnbBtn')?.addEventListener('click', () => {
    hideEl('keptByUnbEdit'); showEl('keptByUnbDisplay');
  });
  document.getElementById('saveKeptByUnbBtn')?.addEventListener('click', saveKeptByUnb);

  // Conception
  document.getElementById('editConceptionBtn')?.addEventListener('click', editConception);
  document.getElementById('saveConceptionBtn')?.addEventListener('click', saveConception);
  document.getElementById('cancelConceptionBtn')?.addEventListener('click', cancelEditConception);

  // Next steps
  document.getElementById('editNextStepsBtn')?.addEventListener('click', editNextSteps);
  document.getElementById('saveNextStepsBtn')?.addEventListener('click', saveNextSteps);
  document.getElementById('cancelNextStepsBtn')?.addEventListener('click', cancelEditNextSteps);

  // IP activities
  document.getElementById('editIPBtn')?.addEventListener('click', () => {
    hideEl('ipDisplay'); showEl('ipEdit');
  });
  document.getElementById('cancelIPBtn')?.addEventListener('click', () => {
    hideEl('ipEdit'); showEl('ipDisplay');
  });
  document.getElementById('saveIPBtn')?.addEventListener('click', () => {
    const ip = document.getElementById('ipTextarea').value;
    fetch(`/api/projects/${currentProjectId}/update-ip/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ ip_activities: ip }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          setText('projectIPActivities', ip || 'No IP activities recorded.');
          hideEl('ipEdit'); showEl('ipDisplay');
        } else {
          showToast('Error saving IP activities: ' + (data.error || 'Unknown error'));
        }
      })
      .catch(() => showToast('Error saving IP activities'));
  });

  // Status
  document.getElementById('saveStatusBtn')?.addEventListener('click', function () {
    const status = document.getElementById('projectStatusSelect').value;
    fetch(`/api/projects/${currentProjectId}/update-status/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ status }),
    })
      .then(r => r.json())
      .then(d => {
        if (!d.success) { showToast(d.error || 'Failed to update status'); return; }

        invalidateCache(currentProjectId);

        // Update the modal header badge
        const statusBadge   = document.getElementById('projectStatus');
        const statusDisplay = document.getElementById('projectStatusDisplay');
        const isNowActive   = status === 'awarded';
        const labels        = { awarded: 'Active', completed: 'Completed', pending: 'Pending', submitted: 'Submitted', rejected: 'Rejected' };
        const html = isNowActive
          ? `<span class="status-badge status-active"><i class="bi bi-circle-fill" style="font-size:8px;"></i> Active</span>`
          : `<span class="status-badge status-${status}">${labels[status] || status}</span>`;
        if (statusBadge)   statusBadge.innerHTML   = html;
        if (statusDisplay) statusDisplay.innerHTML = html;

        // Update the card on the list behind the modal
        const card = document.querySelector(`.project-card[data-project-id="${currentProjectId}"]`);
        if (card) {
          card.dataset.status = status;
          const badgeEl = card.querySelector('.active-badge, .status-badge');
          if (badgeEl) {
            if (isNowActive) {
              badgeEl.className  = 'active-badge';
              badgeEl.innerHTML  = '<i class="bi bi-circle-fill" style="font-size:8px;"></i> Active';
            } else {
              badgeEl.className    = `status-badge status-${status}`;
              badgeEl.textContent  = labels[status] || status;
            }
          }
          // Also sync the inline select on the card if it exists
          const inlineSelect = card.querySelector('.inline-status-select');
          if (inlineSelect) inlineSelect.value = status;
        }
      })
      .catch(() => showToast('Failed to update status'));
  });

  // Publication search
  const pubInput = document.getElementById('pubSearchInput');
  if (pubInput) {
    pubInput.addEventListener('focus', function () {
      if (this.value.trim().length === 0) showRecentPublications();
    });
    pubInput.addEventListener('input', handlePubSearch);
  }

  // Activity search
  const actInput = document.getElementById('actSearchInput');
  if (actInput) {
    actInput.addEventListener('focus', function () {
      if (this.value.trim().length === 0) showRecentActivities();
    });
    actInput.addEventListener('input', handleActSearch);
  }

  // HQP search
  const hqpInput = document.getElementById('hqpSearchInput');
  if (hqpInput) {
    hqpInput.addEventListener('input', function () {
      clearTimeout(hqpSearchTimer);
      const q          = this.value.trim();
      const resultsBox = document.getElementById('hqpSearchResults');
      if (q.length < 2) { resultsBox.style.display = 'none'; return; }

      hqpSearchTimer = setTimeout(() => {
        fetch(`/api/peers/search/?q=${encodeURIComponent(q)}`)
          .then(r => r.json())
          .then(data => {
            const users    = data.users || [];
            const tagged   = Array.from(document.querySelectorAll('[id^="tagged-member-"]'))
              .map(el => parseInt(el.id.replace('tagged-member-', '')));
            const filtered = users.filter(u => !tagged.includes(u.id));

            if (!filtered.length) {
              resultsBox.innerHTML     = '<p class="link-no-results">No users found.</p>';
              resultsBox.style.display = 'block';
              return;
            }
            resultsBox.innerHTML = filtered.map(u => `
              <div class="link-search-result-item">
                <div class="link-result-info">
                  <div class="link-result-title">${u.name}</div>
                  <div class="link-result-meta">
                    <span style="background:${u.user_type === 'student' ? '#dbeafe' : '#e0f2fe'};
                      color:${u.user_type === 'student' ? '#1d4ed8' : '#0369a1'};
                      padding:1px 6px;border-radius:4px;font-size:11px;font-weight:600;">
                      ${u.user_type}
                    </span>
                  </div>
                </div>
                <button class="btn-link-item" onclick="tagMember(${u.id})">+ Tag</button>
              </div>
            `).join('');
            resultsBox.style.display = 'block';
          });
      }, 300);
    });
  }

  // Close dropdowns on outside click
  document.addEventListener('click', function (e) {
    [['#pubSearchInput','#pubSearchResults'],
     ['#actSearchInput','#actSearchResults'],
     ['#hqpSearchInput','#hqpSearchResults']].forEach(([input, results]) => {
      if (!e.target.closest(input) && !e.target.closest(results)) {
        const r = document.querySelector(results);
        if (r) r.style.display = 'none';
      }
    });
  });
});

// ── HQP tagging ───────────────────────────────────────────────
let hqpSearchTimer = null;

function tagMember(userId) {
  fetch(`/api/projects/${currentProjectId}/tag-member/${userId}/`, {
    method: 'POST', headers: { 'X-CSRFToken': csrf },
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        invalidateCache(currentProjectId);
        document.getElementById('hqpSearchInput').value           = '';
        document.getElementById('hqpSearchResults').style.display = 'none';
        loadTaggedMembers(currentProjectId);
      } else {
        showToast('Error tagging member: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(() => showToast('Error tagging member'));
}

function untagMember(userId) {
  fetch(`/api/projects/${currentProjectId}/untag-member/${userId}/`, {
    method: 'POST', headers: { 'X-CSRFToken': csrf },
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        invalidateCache(currentProjectId);
        loadTaggedMembers(currentProjectId);
      } else {
        showToast('Error removing member: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(() => showToast('Error removing member'));
}

function loadTaggedMembers(projectId) {
  fetch(`/api/projects/${projectId}/tagged-members/`)
    .then(r => r.json())
    .then(data => renderTaggedMembers(data.members || []))
    .catch(() => {});
}

function renderTaggedMembers(members) {
  const list  = document.getElementById('taggedMembersList');
  const badge = document.getElementById('hqpCount');
  if (!list) return;

  const hqp = members.filter(m => m.is_hqp);
  if (badge) badge.textContent = hqp.length;

  list.innerHTML = members.length === 0
    ? '<p class="link-empty-msg">No members tagged yet.</p>'
    : members.map(m => `
        <div class="linked-item-card" id="tagged-member-${m.id}">
          <div class="linked-item-info">
            <div class="linked-item-title">${m.name}</div>
            <div class="linked-item-meta">
              ${m.is_hqp
                ? `<span style="background:#dbeafe;color:#1d4ed8;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:600;">HQP</span>`
                : `<span style="background:#f3f4f6;color:#6b7280;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:600;">Collaborator</span>`
              }
              ${m.degree_display ? ` · ${m.degree_display}` : ''}
              ${m.department     ? ` · ${m.department}`     : ''}
            </div>
          </div>
          <button class="btn-unlink" onclick="untagMember(${m.id})">
            <i class="bi bi-x"></i> Remove
          </button>
        </div>`).join('');
}

// ── Recent pubs / activities on focus ─────────────────────────
function showRecentPublications() {
  const resultsBox = document.getElementById('pubSearchResults');
  if (!resultsBox || !currentProjectId) return;
  fetch(`/api/projects/${currentProjectId}/search-pubs/?q=&recent=1`)
    .then(r => r.json())
    .then(data => renderPubResults(data.results || [], resultsBox, 'Recent publications'))
    .catch(() => {});
}

function showRecentActivities() {
  const resultsBox = document.getElementById('actSearchResults');
  if (!resultsBox || !currentProjectId) return;
  fetch(`/api/projects/${currentProjectId}/search-acts/?q=&recent=1`)
    .then(r => r.json())
    .then(data => renderActResults(data.results || [], resultsBox, 'Recent activities'))
    .catch(() => {});
}

// ── Search handlers ───────────────────────────────────────────
let pubSearchTimer = null;

function handlePubSearch() {
  clearTimeout(pubSearchTimer);
  const q          = document.getElementById('pubSearchInput').value.trim();
  const resultsBox = document.getElementById('pubSearchResults');
  if (q.length === 0) { showRecentPublications(); return; }
  if (q.length < 2)   { resultsBox.style.display = 'none'; return; }
  pubSearchTimer = setTimeout(() => {
    fetch(`/api/projects/${currentProjectId}/search-pubs/?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(data => renderPubResults(data.results || [], resultsBox))
      .catch(() => {});
  }, 300);
}

let actSearchTimer = null;

function handleActSearch() {
  clearTimeout(actSearchTimer);
  const q          = document.getElementById('actSearchInput').value.trim();
  const resultsBox = document.getElementById('actSearchResults');
  if (q.length === 0) { showRecentActivities(); return; }
  if (q.length < 2)   { resultsBox.style.display = 'none'; return; }
  actSearchTimer = setTimeout(() => {
    fetch(`/api/projects/${currentProjectId}/search-acts/?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(data => renderActResults(data.results || [], resultsBox))
      .catch(() => {});
  }, 300);
}

// ── Render helpers ────────────────────────────────────────────
function renderPubResults(results, resultsBox, heading = null) {
  const headingHtml = heading ? `<div class="link-results-heading">${heading}</div>` : '';
  resultsBox.innerHTML = results.length === 0
    ? '<p class="link-no-results">No publications found.</p>'
    : headingHtml + results.map(p => `
        <div class="link-search-result-item">
          <div class="link-result-info">
            <div class="link-result-title" title="${p.title}">${p.title}</div>
            <div class="link-result-meta">${p.type}${p.year ? ' · ' + p.year : ''}${p.journal ? ' · ' + p.journal : ''}</div>
          </div>
          <button class="btn-link-item ${p.linked ? 'already-linked' : ''}"
                  onclick="linkPublication(${p.id})" ${p.linked ? 'disabled' : ''}>
            ${p.linked ? 'Linked ✓' : '+ Link'}
          </button>
        </div>`).join('');
  resultsBox.style.display = 'block';
}

function renderActResults(results, resultsBox, heading = null) {
  const headingHtml = heading ? `<div class="link-results-heading">${heading}</div>` : '';
  resultsBox.innerHTML = results.length === 0
    ? '<p class="link-no-results">No activities found.</p>'
    : headingHtml + results.map(a => `
        <div class="link-search-result-item">
          <div class="link-result-info">
            <div class="link-result-title" title="${a.title}">${a.title}</div>
            <div class="link-result-meta">${a.category} · ${a.date}</div>
          </div>
          <button class="btn-link-item ${a.linked ? 'already-linked' : ''}"
                  onclick="linkActivity(${a.id})" ${a.linked ? 'disabled' : ''}>
            ${a.linked ? 'Linked ✓' : '+ Link'}
          </button>
        </div>`).join('');
  resultsBox.style.display = 'block';
}

// ── Linked items ──────────────────────────────────────────────
function loadLinkedItems(projectId) {
  fetch(`/api/projects/${projectId}/linked/`)
    .then(r => r.json())
    .then(data => {
      renderLinkedPublications(data.publications || []);
      renderLinkedActivities(data.activities    || []);
    })
    .catch(() => {});
}

function renderLinkedPublications(pubs) {
  const list  = document.getElementById('linkedPublicationsList');
  const badge = document.getElementById('linkedPubCount');
  if (!list || !badge) return;
  badge.textContent = pubs.length;
  list.innerHTML = pubs.length === 0
    ? '<p class="link-empty-msg">No publications linked yet.</p>'
    : pubs.map(p => `
        <div class="linked-item-card" id="linked-pub-${p.id}">
          <div class="linked-item-info">
            <div class="linked-item-title" title="${p.title}">${p.title}</div>
            <div class="linked-item-meta">${p.type}${p.year ? ' · ' + p.year : ''}${p.journal ? ' · ' + p.journal : ''}</div>
          </div>
          <button class="btn-unlink" onclick="unlinkPublication(${p.id})">
            <i class="bi bi-x"></i> Unlink
          </button>
        </div>`).join('');
}

function renderLinkedActivities(acts) {
  const list  = document.getElementById('linkedActivitiesList');
  const badge = document.getElementById('linkedActCount');
  if (!list || !badge) return;
  badge.textContent = acts.length;
  list.innerHTML = acts.length === 0
    ? '<p class="link-empty-msg">No activities linked yet.</p>'
    : acts.map(a => `
        <div class="linked-item-card" id="linked-act-${a.id}">
          <div class="linked-item-info">
            <div class="linked-item-title" title="${a.title}">${a.title}</div>
            <div class="linked-item-meta">${a.category} · ${a.date}</div>
          </div>
          <button class="btn-unlink" onclick="unlinkActivity(${a.id})">
            <i class="bi bi-x"></i> Unlink
          </button>
        </div>`).join('');
}

// ── Link / unlink (all invalidate cache) ─────────────────────
function linkPublication(pubId) {
  fetch(`/api/projects/${currentProjectId}/link-pub/${pubId}/`, {
    method: 'POST', headers: { 'X-CSRFToken': csrf },
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        invalidateCache(currentProjectId);
        document.getElementById('pubSearchInput').value           = '';
        document.getElementById('pubSearchResults').style.display = 'none';
        loadLinkedItems(currentProjectId);
      }
    })
    .catch(() => {});
}

function unlinkPublication(pubId) {
  fetch(`/api/projects/${currentProjectId}/unlink-pub/${pubId}/`, {
    method: 'POST', headers: { 'X-CSRFToken': csrf },
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) { invalidateCache(currentProjectId); loadLinkedItems(currentProjectId); }
    })
    .catch(() => {});
}

function linkActivity(actId) {
  fetch(`/api/projects/${currentProjectId}/link-act/${actId}/`, {
    method: 'POST', headers: { 'X-CSRFToken': csrf },
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        invalidateCache(currentProjectId);
        document.getElementById('actSearchInput').value           = '';
        document.getElementById('actSearchResults').style.display = 'none';
        loadLinkedItems(currentProjectId);
      }
    })
    .catch(() => {});
}

function unlinkActivity(actId) {
  fetch(`/api/projects/${currentProjectId}/unlink-act/${actId}/`, {
    method: 'POST', headers: { 'X-CSRFToken': csrf },
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) { invalidateCache(currentProjectId); loadLinkedItems(currentProjectId); }
    })
    .catch(() => {});
}

// ── Delete project ────────────────────────────────────────────
function deleteProjectFromModal() {
  const title = document.getElementById('projectTitle').textContent;
  if (!confirm(`Are you sure you want to delete "${title}"?`)) return;
  fetch(`/api/projects/delete/${currentProjectId}/`, {
    method: 'POST', headers: { 'X-CSRFToken': csrf },
  })
    .then(r => r.json())
    .then(d => { if (d.success) { location.reload(); } else { showToast(d.error || 'Delete failed'); } })
    .catch(() => showToast('Delete failed. Please try again.'));
}

// ── External / CCV collaborators ──────────────────────────────
const PARTNER_COLORS = {
  academic:   { bg: '#dbeafe', color: '#1d4ed8' },
  industry:   { bg: '#dcfce7', color: '#166534' },
  community:  { bg: '#fef3c7', color: '#92400e' },
  government: { bg: '#ede9fe', color: '#5b21b6' },
  other:      { bg: '#f3f4f6', color: '#6b7280' },
};

function loadExternalMembers(projectId) {
  fetch(`/api/projects/${projectId}/team-members/`)
    .then(r => r.json())
    .then(data => renderExternalMembers(data.members || []))
    .catch(() => {});
}

function renderExternalMembers(members) {
  const list  = document.getElementById('externalMembersList');
  const badge = document.getElementById('externalMembersCount');
  if (!list) return;
  if (badge) badge.textContent = members.length;

  list.innerHTML = members.length === 0
    ? '<p class="link-empty-msg">No collaborators or partners yet.</p>'
    : members.map(m => {
        const pt      = m.partner_type || 'academic';
        const c       = PARTNER_COLORS[pt] || PARTNER_COLORS.other;
        const ptLabel = m.partner_type_display || pt;
        const isCCV   = m.is_academic_collaborator && !m.manually_added;
        return `
          <div class="linked-item-card" id="external-member-${m.id}">
            <div class="linked-item-info">
              <div class="linked-item-title">
                ${m.name}
                ${isCCV ? `<span style="font-size:10px;color:#bbb;margin-left:6px;font-weight:500;">CCV</span>` : ''}
              </div>
              <div class="linked-item-meta">
                <span style="background:${c.bg};color:${c.color};padding:1px 6px;border-radius:4px;font-size:11px;font-weight:600;">
                  ${ptLabel}
                </span>
                ${m.role_display ? ` · ${m.role_display}` : ''}
              </div>
            </div>
            ${isCCV
              ? `<span style="font-size:11px;color:#bbb;padding:4px 8px;">CCV managed</span>`
              : `<button class="btn-unlink" onclick="removeExternalMember(${m.id})">
                   <i class="bi bi-x"></i> Remove
                 </button>`
            }
          </div>`;
      }).join('');
}

function addExternalMember() {
  const name        = document.getElementById('newMemberName').value.trim();
  const role        = document.getElementById('newMemberRole').value;
  const partnerType = document.getElementById('newMemberPartnerType').value;
  if (!name) { document.getElementById('newMemberName').focus(); return; }

  fetch(`/api/projects/${currentProjectId}/add-member/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ name, role, partner_type: partnerType }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        invalidateCache(currentProjectId);
        document.getElementById('newMemberName').value        = '';
        document.getElementById('newMemberRole').value        = 'other';
        document.getElementById('newMemberPartnerType').value = 'academic';
        loadExternalMembers(currentProjectId);
      } else {
        showToast(data.error || 'Error adding member');
      }
    })
    .catch(() => showToast('Error adding member'));
}

function removeExternalMember(memberId) {
  fetch(`/api/projects/${currentProjectId}/remove-member/${memberId}/`, {
    method: 'POST', headers: { 'X-CSRFToken': csrf },
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        invalidateCache(currentProjectId);
        loadExternalMembers(currentProjectId);
      } else {
        showToast(data.error || 'Error removing member');
      }
    })
    .catch(() => showToast('Error removing member'));
}

function showToast(message, type = 'error') {
  const existing = document.getElementById('projectToast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'projectToast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    z-index: 9999;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    background: ${type === 'success' ? '#dcfce7' : '#fee2e2'};
    color: ${type === 'success' ? '#166534' : '#991b1b'};
    border: 1px solid ${type === 'success' ? '#86efac' : '#fca5a5'};
    transition: opacity 0.3s;
  `;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
}