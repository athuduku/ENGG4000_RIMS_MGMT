const csrf = document.cookie.split(';')
  .map(c => c.trim())
  .find(c => c.startsWith('csrftoken='))
  ?.split('=')[1] || '';

function showToast(msg, type = 'success') {
  const t = document.getElementById('profileToast');
  t.className = 'toast ' + type;
  t.innerHTML = `<i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i> ${msg}`;
  setTimeout(() => { t.className = 'toast'; }, 4000);
}

function toggleSupStudents(btn) {
  const items   = document.querySelectorAll('.sup-item');
  const chevron = document.getElementById('supChevron');
  const hidden  = [...items].some((el, i) => i >= 3 && el.style.display === 'none');
  items.forEach((el, i) => {
    if (i >= 3) el.style.display = hidden ? 'block' : 'none';
  });
  chevron.className = hidden ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
  btn.innerHTML = hidden
    ? `<i class="bi bi-chevron-up" id="supChevron"></i> Show fewer`
    : `<i class="bi bi-chevron-down" id="supChevron"></i> Show all ${STUDENT_COUNT} students`;
}

function saveBasicInfo() {
  fetch('/api/profile/update-basic/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({
      first_name:   document.getElementById('firstName').value.trim(),
      last_name:    document.getElementById('lastName').value.trim(),
      email:        document.getElementById('email').value.trim(),
      organization: document.getElementById('organization')?.value.trim() || '',
    }),
  })
  .then(r => r.json())
  .then(d => d.success ? showToast('Profile updated.') : showToast(d.error || 'Failed.', 'error'))
  .catch(() => showToast('Network error.', 'error'));
}

function saveResearchInterests() {
  fetch('/api/profile/update-research-interests/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ research_interests: document.getElementById('researchInterests').value }),
  })
  .then(r => r.json())
  .then(d => d.success ? showToast('Research interests saved.') : showToast(d.error || 'Failed.', 'error'))
  .catch(() => showToast('Network error.', 'error'));
}
function saveEdiProfile() {
  fetch('/api/profile/update-edi/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({
      gender:              document.getElementById('ediGender').value,
      residency_status:    document.getElementById('ediResidency').value,
      indigenous_identity: document.getElementById('ediIndigenous').value,
      race_ethnicity:      document.getElementById('ediRaceEthnicity').value,
    }),
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      showToast('EDI profile saved. Thank you!');
      const banner = document.getElementById('ediBanner');
      if (banner) banner.style.display = 'none';
    } else {
      showToast(d.error || 'Failed.', 'error');
    }
  })
  .catch(() => showToast('Network error.', 'error'));
}

function saveConsent(checked) {
  fetch('/api/profile/update-consent/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ consent_to_share: checked })
  });
}

// ── Primary supervisor modal ──────────────────────────
function openSupervisorRequest() {
  document.getElementById('supervisorModal').style.display = 'flex';
}

function closeSupervisorModal() {
  document.getElementById('supervisorModal').style.display = 'none';
}

function sendSupervisorRequest() {
  const sup = document.getElementById('supervisorSelect').value;
  if (!sup) { showToast('Select a supervisor', 'error'); return; }
  fetch('/api/supervisor/request/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ supervisor_id: sup })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      showToast('Supervisor request sent');
      closeSupervisorModal();
    } else {
      showToast(d.error || 'Failed', 'error');
    }
  });
}

// ── Co-supervisor modal ───────────────────────────────
function openCoSupervisorModal() {
  document.getElementById('coSupervisorModal').style.display = 'flex';
}

function closeCoSupervisorModal() {
  document.getElementById('coSupervisorModal').style.display = 'none';
}

function sendCoSupervisorRequest() {
  const sup = document.getElementById('coSupervisorSelect').value;
  if (!sup) { showToast('Select a co-supervisor', 'error'); return; }
  fetch('/api/co-supervisor/request/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ supervisor_id: sup })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      showToast(d.message);
      closeCoSupervisorModal();
      setTimeout(() => location.reload(), 800);
    } else {
      showToast(d.error || 'Failed', 'error');
    }
  })
  .catch(() => showToast('Network error', 'error'));
}

function removeCoSupervisor(supervisorId, name) {
  if (!confirm(`Remove ${name} as co-supervisor?`)) return;
  fetch('/api/co-supervisor/remove/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ supervisor_id: supervisorId })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      showToast(`${name} removed as co-supervisor.`);
      setTimeout(() => location.reload(), 800);
    } else {
      showToast(d.error || 'Failed', 'error');
    }
  })
  .catch(() => showToast('Network error', 'error'));
}

// ── Researcher profile helpers ────────────────────────
function toggleAwards(btn) {
  const entries = document.querySelectorAll('.award-entry');
  const chevron = document.getElementById('awardsChevron');
  const hidden  = [...entries].some(e => e.style.display === 'none');
  entries.forEach((e, i) => {
    if (i >= 3) e.style.display = hidden ? 'block' : 'none';
  });
  chevron.className = hidden ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
  btn.innerHTML = hidden
    ? `<i class="bi bi-chevron-up" id="awardsChevron"></i> Show fewer`
    : `<i class="bi bi-chevron-down" id="awardsChevron"></i> Show all ${AWARD_COUNT} awards`;
}

function openSupEdit(id) {
  document.getElementById(`sup-edit-${id}`).style.display = 'block';
}

function closeSupEdit(id) {
  document.getElementById(`sup-edit-${id}`).style.display = 'none';
  document.getElementById(`sup-status-msg-${id}`).textContent = '';
}

function saveSupRecord(id) {
  const dept     = document.getElementById(`sup-dept-${id}`).value.trim();
  const expected = document.getElementById(`sup-expected-${id}`).value;
  const degree   = document.getElementById(`sup-degree-${id}`).value;
  const status   = document.getElementById(`sup-status-${id}`).value;
  const msg      = document.getElementById(`sup-status-msg-${id}`);
  msg.textContent = 'Saving...';
  msg.style.color = '#999';
  fetch(`/api/supervision/${id}/update/`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({
      department:        dept,
      expected_date:     expected || null,
      degree_type:       degree,
      status:            status,
      linked_student_id: document.getElementById(`sup-linked-${id}`).value || null,
    }),
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
        const card = document.getElementById(`sup-${id}`);
        const deptDisplay = card.querySelector('.sup-dept-display');
        
        if (dept) {
            deptDisplay.textContent = dept;
            deptDisplay.style.color = '#999';
            deptDisplay.style.fontStyle = 'normal';
        } else {
            // leave it — page reload will show student fallback correctly
            deptDisplay.textContent = 'No department set';
            deptDisplay.style.color = '#ccc';
            deptDisplay.style.fontStyle = 'italic';
        }
        
        card.querySelector('.sup-expected-display').textContent = expected ? ` · Expected ${expected}` : '';
        if (d.updated) {
            card.querySelector('.sup-degree-display').textContent =
                document.getElementById(`sup-degree-${id}`).options[
                    document.getElementById(`sup-degree-${id}`).selectedIndex
                ].text;
        }
        msg.textContent = '✓ Saved';
        msg.style.color = 'green';
        setTimeout(() => closeSupEdit(id), 1200);
        } else {
            msg.textContent = d.error || 'Failed to save.';
            msg.style.color = 'red';
        }
    })
  .catch(() => {
    msg.textContent = 'Network error.';
    msg.style.color = 'red';
  });
}

function saveAcademicInfo() {
  fetch('/api/profile/update-academic/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({
      degree_level:      document.getElementById('academicDegreeLevel').value,
      department:        document.getElementById('academicDepartment').value.trim(),
      start_date:        document.getElementById('academicStartDate').value || null,
      expected_end_date: document.getElementById('academicExpectedEnd').value || null,
      thesis_title:      document.getElementById('academicThesisTitle').value.trim(),
      graduation_date:   document.getElementById('academicGraduationDate').value || null,
    }),
  })
  .then(r => r.json())
  .then(d => d.success ? showToast('Academic info saved.') : showToast(d.error || 'Failed.', 'error'))
  .catch(() => showToast('Network error.', 'error'));
}