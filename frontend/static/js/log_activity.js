// log_activity.js

const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
let selectedType      = 'presentation';
let taggedUsers       = [];
let searchTimeout     = null;
let userChangedCategory = false; // track if user manually changed category

// ── Auto-detect category from title ──────────────────────
function autoDetectCategory(title) {
  const t = title.toLowerCase();
  if (t.includes('conference') || t.includes('symposium') ||
      t.includes('congress') || t.includes('summit') || t.includes('embc') ||
      t.includes('ieee') || t.includes('workshop on') || t.includes('meeting'))
    return 'conference';
  if (t.includes('outreach') || t.includes('community') ||
      t.includes('knowledge mobilization') || t.includes('workshop') ||
      t.includes('public engagement') || t.includes('seminar') ||
      t.includes('partnership'))
    return 'knowledge_mobilization';
  if (t.includes('broadcast') || t.includes('interview') ||
      t.includes('media') || t.includes('cbc') || t.includes('radio') ||
      t.includes('news') || t.includes('telegraph'))
    return 'media';
  if (t.includes('university') || t.includes('lecture') ||
      t.includes('academic') || t.includes('research talk'))
    return 'academic';
  return 'other';
}

document.getElementById('activityTitle').addEventListener('input', function () {
  if (!userChangedCategory) {
    const detected = autoDetectCategory(this.value);
    document.getElementById('activityCategory').value = detected;
    document.querySelectorAll('.cat-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.category === detected);
    });
    onCategoryChange();
  }
});

// ── Category selector ─────────────────────────────────────
document.querySelectorAll('.cat-btn').forEach(btn => {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('activityCategory').value = this.dataset.category;
    userChangedCategory = true;
    onCategoryChange();
  });
});

// Show/hide conference field + required marker based on category
function onCategoryChange() {
  const category   = document.getElementById('activityCategory').value;
  const group      = document.getElementById('conferenceGroup');
  const reqMarker  = document.getElementById('confRequired');

  if (category === 'conference') {
    group.style.display    = 'block';
    reqMarker.style.display = 'inline';
  } else {
    group.style.display    = 'none';
    reqMarker.style.display = 'none';
    document.getElementById('conferenceId').value = '';
    clearConferenceSelection();
  }
}

// ── Type selector ─────────────────────────────────────────
document.querySelectorAll('.type-btn').forEach(btn => {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    selectedType = this.dataset.type;
    document.getElementById('activityType').value = selectedType;
  });
});

// run on load
onCategoryChange();

// ── Load strategic objectives ─────────────────────────
fetch('/api/objectives/')
  .then(r => r.json())
  .then(data => {
    const container = document.getElementById('objectivesContainer');
    container.innerHTML = data.objectives.map(obj => `
      <label style="display:flex;align-items:center;gap:8px;padding:8px 14px;
                    border:1px solid #e8eaed;border-radius:20px;cursor:pointer;
                    font-size:14px;transition:all .2s;">
        <input type="checkbox" name="objective" value="${obj.id}"
               style="accent-color:#C8102E;">
        ${obj.name}
      </label>`).join('');

    container.querySelectorAll('input[name="objective"]').forEach(cb => {
      cb.addEventListener('change', function() {
        this.closest('label').style.background  = this.checked ? '#fff0f2' : '';
        this.closest('label').style.borderColor = this.checked ? '#C8102E' : '#e8eaed';
        this.closest('label').style.color       = this.checked ? '#C8102E' : '';
      });
    });
  });

// ── Conference search ─────────────────────────────────────
let confSearchTimeout     = null;
let selectedConferenceId  = null;
let pendingNewConferenceName = null;

document.getElementById('conferenceSearchInput').addEventListener('input', function () {
  clearTimeout(confSearchTimeout);
  const query    = this.value.trim();
  const createRow   = document.getElementById('createConferenceRow');
  const createLabel = document.getElementById('createConferenceLabel');

  if (query.length < 2) {
    document.getElementById('conferenceSearchResults').style.display = 'none';
    createRow.style.display = 'none';
    return;
  }

  confSearchTimeout = setTimeout(() => {
    fetch(`/api/conferences/search/?q=${encodeURIComponent(query)}`)
      .then(r => r.json())
      .then(data => {
        const results = document.getElementById('conferenceSearchResults');
        const list    = data.results || [];

        if (list.length === 0) {
          results.style.display = 'none';
          createLabel.textContent = query;
          createRow.style.display = 'block';
          return;
        }

        createRow.style.display = 'none';
        results.innerHTML = list.map(c => `
          <div class="peer-result-item"
               data-id="${c.id}" data-name="${c.display}">
            <span class="peer-result-name">${c.display}</span>
            ${c.location ? `<span class="peer-result-type">${c.location}</span>` : ''}
          </div>`).join('') +
          `<div class="peer-result-item" data-id="new" data-name="${query}"
                style="border-top:1px solid #f0f0f0;color:#C8102E;">
            <i class="bi bi-plus-circle"></i> Create "${query}"
          </div>`;
        results.style.display = 'block';
      });
  }, 300);
});

document.getElementById('conferenceSearchResults').addEventListener('click', function (e) {
  const item = e.target.closest('.peer-result-item');
  if (!item) return;
  const id   = item.dataset.id;
  const name = item.dataset.name;
  if (id === 'new') {
    createConference(document.getElementById('conferenceSearchInput').value.trim());
  } else {
    selectConference(id, name);
  }
});

document.getElementById('createConferenceBtn').addEventListener('click', function () {
  createConference(document.getElementById('conferenceSearchInput').value.trim());
});

function createConference(name) {
  pendingNewConferenceName = name;
  selectConference('pending', name);
}

function selectConference(id, name) {
  selectedConferenceId = id;
  document.getElementById('conferenceId').value = id;
  document.getElementById('selectedConferenceName').textContent = name;
  document.getElementById('selectedConference').style.display = 'block';
  document.getElementById('conferenceSearchInput').value = '';
  document.getElementById('conferenceSearchResults').style.display = 'none';
  document.getElementById('createConferenceRow').style.display = 'none';
}

function clearConferenceSelection() {
  selectedConferenceId     = null;
  pendingNewConferenceName = null;
  document.getElementById('conferenceId').value = '';
  document.getElementById('selectedConference').style.display = 'none';
  document.getElementById('conferenceSearchInput').value = '';
}

document.getElementById('clearConference')?.addEventListener('click', clearConferenceSelection);

// ── Peer search ───────────────────────────────────────────
document.getElementById('peerSearchInput').addEventListener('input', function () {
  clearTimeout(searchTimeout);
  const query = this.value.trim();
  if (query.length < 2) {
    document.getElementById('peerSearchResults').style.display = 'none';
    return;
  }
  searchTimeout = setTimeout(() => {
    fetch(`/api/peers/search/?q=${encodeURIComponent(query)}`)
      .then(r => r.json())
      .then(data => {
        const results  = document.getElementById('peerSearchResults');
        const filtered = (data.users || []).filter(u => !taggedUsers.find(t => t.id === u.id));
        if (!filtered.length) { results.style.display = 'none'; return; }
        results.innerHTML = filtered.map(u => `
          <div class="peer-result-item" data-id="${u.id}" data-name="${u.name}" data-type="${u.user_type}">
            <span class="peer-result-name">${u.name}</span>
            <span class="peer-result-type ${u.user_type}">${u.user_type}</span>
          </div>`).join('');
        results.style.display = 'block';
      });
  }, 300);
});

document.getElementById('peerSearchResults').addEventListener('click', function (e) {
  const item = e.target.closest('.peer-result-item');
  if (!item) return;
  taggedUsers.push({
    id: parseInt(item.dataset.id),
    name: item.dataset.name,
    user_type: item.dataset.type,
  });
  renderTaggedPeers();
  this.style.display = 'none';
  document.getElementById('peerSearchInput').value = '';
});

function renderTaggedPeers() {
  const container = document.getElementById('taggedPeers');
  container.innerHTML = taggedUsers.map(u => `
    <div class="tagged-peer-chip">
      <span>${u.name}</span>
      <span class="chip-type ${u.user_type}">${u.user_type}</span>
      <button class="chip-remove" data-id="${u.id}">&times;</button>
    </div>`).join('');
}

document.getElementById('taggedPeers').addEventListener('click', function (e) {
  if (e.target.classList.contains('chip-remove')) {
    taggedUsers = taggedUsers.filter(u => u.id !== parseInt(e.target.dataset.id));
    renderTaggedPeers();
  }
});

document.addEventListener('click', function (e) {
  if (!e.target.closest('.peer-search-box') && !e.target.closest('#peerSearchResults'))
    document.getElementById('peerSearchResults').style.display = 'none';
  if (!e.target.closest('#conferenceSearchInput') && !e.target.closest('#conferenceSearchResults')) {
    const r = document.getElementById('conferenceSearchResults');
    if (r) r.style.display = 'none';
  }
});

// ── Toggle buttons (invited / keynote) ───────────────────
document.querySelectorAll('.toggle-btn').forEach(btn => {
  btn.addEventListener('click', function () {
    const field = this.dataset.field;
    document.querySelectorAll(`.toggle-btn[data-field="${field}"]`)
      .forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    document.getElementById(
      field === 'invited' ? 'activityInvited' : 'activityKeynote'
    ).value = this.dataset.value;
  });
});

// ── Submit ────────────────────────────────────────────────
let similarActivityId = null; // store for link-me action

document.getElementById('submitActivity').addEventListener('click', function () {
  submitActivity(false);
});

async function submitActivity(force) {
  const title    = document.getElementById('activityTitle').value.trim();
  const date     = document.getElementById('activityDate').value;
  const category = document.getElementById('activityCategory').value;
  const status   = document.getElementById('formStatus');
  const btn      = document.getElementById('submitActivity');

  if (!title || !date) {
    status.textContent = 'Title and date are required.';
    status.style.color = 'red';
    return;
  }

  if (category === 'conference') {
    const confId = document.getElementById('conferenceId').value;
    if (!confId || confId === '') {
      status.textContent = 'Please select or create a conference.';
      status.style.color = 'red';
      document.getElementById('conferenceGroup').scrollIntoView({ behavior: 'smooth', block: 'center' });
      document.getElementById('conferenceSearchInput').focus();
      return;
    }
  }

  btn.disabled       = true;
  status.textContent = 'Saving...';
  status.style.color = '#666';

  // ── Create conference if pending ──────────────────────
  let conferenceId = document.getElementById('conferenceId').value || null;
  if (pendingNewConferenceName) {
    try {
      const confRes  = await fetch('/api/conferences/create/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ name: pendingNewConferenceName }),
      });
      const confData = await confRes.json();
      if (confData.success) conferenceId = confData.id;
    } catch (e) { /* non-fatal */ }
  }

  fetch('/api/activities/log/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({
      title,
      activity_type: selectedType,
      category,
      date,
      force,
      location:      document.getElementById('activityLocation').value.trim(),
      description:   document.getElementById('activityDescription').value.trim(),
      tagged_users:  taggedUsers.map(u => u.id),
      invited:       document.getElementById('activityInvited').value === 'true' ? true
                   : document.getElementById('activityInvited').value === 'false' ? false : null,
      keynote:       document.getElementById('activityKeynote').value === 'true' ? true
                   : document.getElementById('activityKeynote').value === 'false' ? false : null,
      audience:      document.getElementById('activityAudience').value || null,
      conference_id: conferenceId,
      objectives: [...document.querySelectorAll('input[name="objective"]:checked')]
                    .map(cb => parseInt(cb.value)),
    })
  })
  .then(r => r.json())
  .then(data => {
    // ── Already on profile (owner or tagged) ─────────────
    if (data.already_tagged) {
      status.textContent = data.message;
      status.style.color = '#f59e0b';
      btn.disabled = false;
      return;
    }

    // ── Similar activity found — show modal ───────────────
    if (data.similar_found) {
      btn.disabled = false;
      status.textContent = '';
      similarActivityId = data.similar.id;

      document.getElementById('similarTitle').textContent    = data.similar.title;
      document.getElementById('similarDate').textContent     = data.similar.date;
      document.getElementById('similarLocation').textContent = data.similar.location || '';
      document.getElementById('similarLoggedBy').textContent = data.similar.logged_by;

      const modal = document.getElementById('similarActivityModal');
      modal.style.display = 'flex';
      return;
    }

    // ── Success ───────────────────────────────────────────
    if (data.success) {
      status.textContent = `✓ ${data.message}`;
      status.style.color = 'green';
      setTimeout(() => { window.location.href = '/dashboard/'; }, 1500);
    } else {
      status.textContent = data.error || 'Error saving activity.';
      status.style.color = 'red';
      btn.disabled = false;
    }
  })
  .catch(() => {
    status.textContent = 'Error saving. Please try again.';
    status.style.color = 'red';
    btn.disabled = false;
  });
}

// ── Modal actions ─────────────────────────────────────────
document.getElementById('btnLinkMe').addEventListener('click', function () {
  if (!similarActivityId) return;
  this.disabled = true;
  this.textContent = 'Linking...';

  fetch(`/api/activities/${similarActivityId}/tag-me/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
  })
  .then(r => r.json())
  .then(data => {
    closeSimilarModal();
    const status = document.getElementById('formStatus');
    if (data.success) {
      status.textContent = `✓ ${data.message}`;
      status.style.color = 'green';
      setTimeout(() => { window.location.href = '/dashboard/'; }, 1500);
    } else {
      status.textContent = data.error || 'Could not link activity.';
      status.style.color = 'red';
    }
  })
  .catch(() => {
    closeSimilarModal();
    document.getElementById('formStatus').textContent = 'Error. Please try again.';
    document.getElementById('formStatus').style.color = 'red';
  });
});

document.getElementById('btnLogSeparately').addEventListener('click', function () {
  closeSimilarModal();
  submitActivity(true); // resubmit with force=true
});

document.getElementById('btnCancelSimilar').addEventListener('click', closeSimilarModal);

function closeSimilarModal() {
  document.getElementById('similarActivityModal').style.display = 'none';
  document.getElementById('btnLinkMe').disabled = false;
  document.getElementById('btnLinkMe').innerHTML = '<i class="bi bi-link-45deg"></i> Yes, link me';
  similarActivityId = null;
}