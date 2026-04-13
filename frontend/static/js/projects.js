const ITEMS_PER_PAGE = 10;
let currentPage   = 1;
let allCards      = [];
let filteredCards = [];

function previousPage() {
  if (currentPage > 1) { currentPage--; displayPage(); }
}

function nextPage() {
  if (currentPage < Math.ceil(filteredCards.length / ITEMS_PER_PAGE)) {
    currentPage++;
    displayPage();
  }
}

function displayPage() {
  const start = (currentPage - 1) * ITEMS_PER_PAGE;
  const end   = start + ITEMS_PER_PAGE;

  allCards.forEach(c => c.style.display = 'none');
  filteredCards.slice(start, end).forEach(c => c.style.display = '');

  const totalPages = Math.ceil(filteredCards.length / ITEMS_PER_PAGE) || 1;
  document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
  document.getElementById('prev-btn').disabled = currentPage === 1;
  document.getElementById('next-btn').disabled = currentPage >= totalPages;
  document.querySelector('.main-content')?.scrollTo(0, 0);
}

function generateStatusFilters() {
  const statusNames = { awarded: 'Awarded', completed: 'Completed', pending: 'Pending' };
  const statuses = [...new Set(allCards.map(c => c.dataset.status).filter(Boolean))];
  const container = document.getElementById('status-filters-container');
  container.innerHTML = '';

  statuses.forEach(status => {
    const count = allCards.filter(c => c.dataset.status === status).length;
    const label = statusNames[status] || status;
    const div = document.createElement('div');
    div.className = 'filter-item';
    div.innerHTML = `
      <input type="checkbox" id="status-${status}" class="status-filter" value="${status}">
      <label for="status-${status}">${label}</label>
      <span class="filter-count">${count}</span>`;
    container.appendChild(div);
  });
}

function generateRoleFilters() {
  const roleNames  = { pi: 'Principal Investigator', co_pi: 'Co-Investigator', pa: 'Principal Applicant', co_app: 'Co-applicant' };
  const roleColors = { pi: '#d4edda', co_pi: '#ffe0b2', pa: '#f8d7da', co_app: '#fff3cd' };

  const roles = [...new Set(allCards.map(c => c.dataset.role).filter(Boolean))];
  const container = document.getElementById('role-filters-container');
  container.innerHTML = '';

  roles.forEach(role => {
    const count = allCards.filter(c => c.dataset.role === role).length;
    const label = roleNames[role] || role;
    const bg    = roleColors[role] || '#e2e3e5';
    const div = document.createElement('div');
    div.className = 'filter-item';
    div.innerHTML = `
      <input type="checkbox" id="role-${role}" class="role-filter" value="${role}">
      <label for="role-${role}" style="background:${bg};padding:6px 10px;border-radius:4px;font-weight:600;flex:1;margin:0;">${label}</label>
      <span class="filter-count">${count}</span>`;
    container.appendChild(div);
  });
}

function advancedMatch(text, query) {
  if (!query) return true;
  text  = text.toLowerCase();
  query = query.toLowerCase().trim();
  if (query.includes(' and ')) return query.split(' and ').every(t => text.includes(t.trim()));
  if (query.includes(' or '))  return query.split(' or ').some(t => text.includes(t.trim()));
  return text.includes(query);
}

function filterProjects() {
  const query    = document.getElementById('search-input').value;
  const statuses = [...document.querySelectorAll('.status-filter:checked')].map(e => e.value);
  const roles    = [...document.querySelectorAll('.role-filter:checked')].map(e => e.value);
  const yearFrom = parseInt(document.getElementById('year-from').value) || 0;
  const yearTo   = parseInt(document.getElementById('year-to').value)   || 9999;
  const sortBy   = document.getElementById('sort-by').value;

  filteredCards = allCards.filter(card => {
    const combined = `${card.dataset.title} ${card.dataset.team || ''}`;
    const year     = parseInt(card.dataset.year) || 0;
    return (
      advancedMatch(combined, query) &&
      (statuses.length === 0 || statuses.includes(card.dataset.status)) &&
      (roles.length    === 0 || roles.includes(card.dataset.role))      &&
      year >= yearFrom && year <= yearTo
    );
  });

  const sortFns = {
    recent:       (a, b) => parseInt(b.dataset.year) - parseInt(a.dataset.year),
    oldest:       (a, b) => parseInt(a.dataset.year) - parseInt(b.dataset.year),
    'title-asc':  (a, b) => a.dataset.title.localeCompare(b.dataset.title),
    'title-desc': (a, b) => b.dataset.title.localeCompare(a.dataset.title),
  };
  if (sortFns[sortBy]) filteredCards.sort(sortFns[sortBy]);

  currentPage = 1;
  displayPage();

  const n = filteredCards.length;
  document.getElementById('results-count').textContent =
    `${n} project${n !== 1 ? 's' : ''} found`;
}

function resetFilters() {
  document.getElementById('search-input').value = '';
  document.querySelectorAll('.status-filter, .role-filter').forEach(el => el.checked = false);
  document.getElementById('year-from').value    = '';
  document.getElementById('year-to').value      = '';
  document.getElementById('sort-by').value      = 'recent';
  document.getElementById('filter-all').checked = true;
  filterProjects();
}

function clearAllFilters() { resetFilters(); }

// ── Card clicks ───────────────────────────────
let _fetchInProgress = false;

function initCardClicks() {
  const list = document.getElementById('projects-list');
  if (!list) return;

  list.addEventListener('click', function (e) {
    if (e.target.closest('.sidebar') || e.target.closest('.search-section')) return;
    const card = e.target.closest('.project-card');
    if (!card || _fetchInProgress) return;

    _fetchInProgress = true;
    fetch(`/api/projects/${card.dataset.projectId}/`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(data => openProjectModal(data))
      .catch(err => console.error('Error loading project:', err))
      .finally(() => { _fetchInProgress = false; });
  });
}

// ── Static button wiring (replaces all onclick= attrs) ───
function initStaticButtons() {
  // Pagination
  document.getElementById('prev-btn')?.addEventListener('click', previousPage);
  document.getElementById('next-btn')?.addEventListener('click', nextPage);

  // Filters
  document.getElementById('filter-all')?.addEventListener('change', resetFilters);
  document.getElementById('search-input')?.addEventListener('keyup', filterProjects);
  document.getElementById('sort-by')?.addEventListener('change', filterProjects);
  document.getElementById('year-from')?.addEventListener('change', filterProjects);
  document.getElementById('year-to')?.addEventListener('change', filterProjects);

  // Clear filters button
  document.querySelector('.clear-filters-btn')?.addEventListener('click', clearAllFilters);

  // Filter checkboxes — delegated since they're generated dynamically
  document.getElementById('status-filters-container')
    ?.addEventListener('change', filterProjects);
  document.getElementById('role-filters-container')
    ?.addEventListener('change', filterProjects);
}


// ── Init ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  allCards = Array.from(document.querySelectorAll('.project-card'));
  generateStatusFilters();
  generateRoleFilters();
  filterProjects();
  initCardClicks();
  initStaticButtons();
});

function deleteItem(type, id, title) {
  if (!confirm(`Are you sure you want to delete "${title}"?`)) return;

  const urls = {
    activity: `/api/activities/delete/${id}/`,
    publication: `/publications/delete/${id}/`,
    project: `/api/projects/delete/${id}/`,
  };

  fetch(urls[type], {
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