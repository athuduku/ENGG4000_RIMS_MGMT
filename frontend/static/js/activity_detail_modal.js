// Activity Detail Modal Functions

let currentActivityId = null;

function openActivityModal(activityData) {
  currentActivityId = activityData.id;

  const objSection = document.getElementById('objectivesSection');
  const objContainer = document.getElementById('activityObjectives');
  if (activityData.objectives && activityData.objectives.length > 0) {
      objContainer.innerHTML = activityData.objectives.map(o => `
          <span style="background:#fff0f2;color:#C8102E;border:1px solid #fecdd3;
                      border-radius:20px;padding:4px 12px;font-size:13px;">
              ${o}
          </span>`).join('');
      objSection.style.display = 'block';
  } else {
      objSection.style.display = 'none';
  }
  
  // ── Title ─────────────────────────────────────────────
  document.getElementById('activityTitle').textContent = activityData.title;

  // ── Type badge ────────────────────────────────────────
  const typeKey = activityData.activity_type || '';
  document.getElementById('activityType').innerHTML =
    `<span class="type-badge type-${typeKey}">
       ${TYPE_LABELS[typeKey] || typeKey}
     </span>`;

  // ── Category badge ────────────────────────────────────
  const categoryEl = document.getElementById('activityCategory');
  if (categoryEl) {
    const rawCategory = activityData.category || '';
    const catKey = rawCategory.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z_]/g, '');
    if (catKey) {
      categoryEl.innerHTML =
        `<span class="category-badge cat-${catKey}">
          ${CATEGORY_LABELS[catKey] || catKey}
        </span>`;
      categoryEl.style.display = 'inline-block';
    } else {
      categoryEl.style.display = 'none';
    }
  }

  // ── Source badge ──────────────────────────────────────
  const sourceEl = document.getElementById('activitySource');
  if (sourceEl) {
    const source = activityData.source || '';
    if (source === 'manual') {
      sourceEl.innerHTML = `<span style="
        display:inline-block;padding:2px 8px;border-radius:6px;
        font-size:18px;font-weight:700;background:#fef3c7;color:#92400e;
      ">Manual</span>`;
    } else if (source === 'ccv') {
      sourceEl.innerHTML = `<span style="
        display:inline-block;padding:2px 8px;border-radius:6px;
        font-size:18px;font-weight:700;background:#f3f4f6;color:#6b7280;
      ">CCV</span>`;
    } else {
      sourceEl.innerHTML = '';
    }
  }


  // ── Date ──────────────────────────────────────────────
  document.getElementById('activityDate').textContent = activityData.date || '-';

  // ── Details section ───────────────────────────────────
  const detailsSection = document.getElementById('detailsSection');
  const detailsGrid    = document.getElementById('activityDetails');

  const hasDetails = (
    activityData.description   ||
    activityData.location      ||
    activityData.audience      ||
    activityData.co_presenters ||
    (activityData.invited !== null && activityData.invited !== undefined) ||
    (activityData.keynote !== null && activityData.keynote !== undefined) ||
    (activityData.tagged_users && activityData.tagged_users.length > 0)
  );

  if (hasDetails) {
    detailsSection.style.display = 'block';
    detailsGrid.innerHTML = '';

    // ── Helper ─────────────────────────────────────────
    function addDetail(label, value, type = 'text') {
      if (value === null || value === undefined || value === '') return;
      if (Array.isArray(value) && value.length === 0) return;

      const box = document.createElement('div');
      box.className = 'detail-item-box';

      let valueHtml = '';

      if (type === 'yesno') {
        const isYes = value === true;
        valueHtml = `
          <span style="
            display:inline-block;padding:2px 10px;border-radius:6px;
            font-size:18px;font-weight:700;
            background:${isYes ? '#dcfce7' : '#f3f4f6'};
            color:${isYes ? '#166534' : '#6b7280'};
          ">${isYes ? 'Yes' : 'No'}</span>`;

          } else if (type === 'tags') {
              valueHtml = value.map(person => {
                const name = typeof person === 'string' ? person : person.name;
                const utype = typeof person === 'object' ? person.user_type : 'other';
                const style = utype === 'researcher'
                  ? 'background:#dbeafe;color:#1d4ed8;'
                  : utype === 'student'
                  ? 'background:#fce7f3;color:#9d174d;'
                  : 'background:#f3f4f6;color:#6b7280;';
                return `<span style="display:inline-flex;align-items:center;gap:4px;
                  padding:2px 10px;border-radius:20px;font-size:18px;font-weight:600;
                  ${style}margin:2px;">
                  <i class="bi bi-person-fill"></i> ${name}</span>`;
              }).join('');

      } else {
        valueHtml = `<div class="detail-value-text">${value}</div>`;
      }

      box.innerHTML = `
        <div class="detail-label">${label}</div>
        <div style="margin-top:4px;">${valueHtml}</div>
      `;

      detailsGrid.appendChild(box);
    }

    // ── Fields ─────────────────────────────────────────
    addDetail('Event / Description', activityData.description);
    addDetail('Location',            activityData.location);
    addDetail('Audience',            activityData.audience);
    addDetail('Co-Presenters',       activityData.co_presenters);

    if (activityData.invited !== null && activityData.invited !== undefined) {
      addDetail('Invited Speaker', activityData.invited, 'yesno');
    }
    if (activityData.keynote !== null && activityData.keynote !== undefined) {
      addDetail('Keynote', activityData.keynote, 'yesno');
    }
    if (activityData.tagged_users && activityData.tagged_users.length > 0) {
      addDetail('Tagged People', activityData.tagged_users, 'tags');
    }

  } else {
    detailsSection.style.display = 'none';
  }

  // ── Delete button — hide for CCV activities ───────────
  const deleteSection = document.getElementById('modalDeleteSection');
  if (deleteSection) {
    deleteSection.style.display =
      activityData.source === 'manual' ? 'flex' : 'none';
  }

  // ── Show modal ────────────────────────────────────────
  document.getElementById('activityDetailModal').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeActivityModal() {
  document.getElementById('activityDetailModal').classList.remove('active');
  document.body.style.overflow = 'auto';
  currentActivityId = null;
}

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') closeActivityModal();
});

function deleteFromModal() {
  const title = document.getElementById('activityTitle').textContent;
  if (!confirm(`Are you sure you want to delete "${title}"?`)) return;

  fetch(`/api/activities/delete/${currentActivityId}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      location.reload();
    } else {
      alert(d.error || 'Delete failed');
    }
  })
  .catch(() => alert('Delete failed. Please try again.'));
}