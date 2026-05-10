const ITEMS_PER_PAGE = 10;
let currentPage   = 1;
let allCards      = [];
let filteredCards = [];

// ── Filter group builders ─────────────────────────────────────────────────────
function generateStatusFilters() {
  buildFilterGroup('status-filters-container', 'status', 'status-filter', {
    awarded:   'Awarded',
    completed: 'Completed',
    pending:   'Pending',
  }, 'filterProjects');
}

function generateRoleFilters() {
  const roleStyle = 'padding:6px 10px;border-radius:4px;font-weight:600;flex:1;margin:0;';
  buildFilterGroup('role-filters-container', 'role', 'role-filter', {
    pi:     'Principal Investigator',
    co_pi:  'Co-Investigator',
    pa:     'Principal Applicant',
    co_app: 'Co-applicant',
  }, 'filterProjects', {
    pi:     `background:#d4edda;${roleStyle}`,
    co_pi:  `background:#ffe0b2;${roleStyle}`,
    pa:     `background:#f8d7da;${roleStyle}`,
    co_app: `background:#fff3cd;${roleStyle}`,
  });
}

// ── Filter + sort ─────────────────────────────────────────────────────────────
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

// ── Card click → modal ────────────────────────────────────────────────────────
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

// ── Delete ────────────────────────────────────────────────────────────────────
function deleteItem(type, id, title) {
  if (!confirm(`Are you sure you want to delete "${title}"?`)) return;
  const urls = {
    activity:    `/api/activities/delete/${id}/`,
    publication: `/publications/delete/${id}/`,
    project:     `/api/projects/delete/${id}/`,
  };
  fetch(urls[type], {
    method: 'POST',
    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
  })
  .then(r => r.json())
  .then(d => { if (d.success) location.reload(); else alert(d.error || 'Delete failed'); })
  .catch(() => alert('Delete failed. Please try again.'));
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  allCards = Array.from(document.querySelectorAll('.project-card'));
  generateStatusFilters();
  generateRoleFilters();
  initListPage({
    filterFn:         filterProjects,
    checkboxSelector: '.status-filter, .role-filter',
    scrollSelector:   '.main-content',
    filterContainers: ['status-filters-container', 'role-filters-container'],
  });
  filterProjects();
  initCardClicks();
});