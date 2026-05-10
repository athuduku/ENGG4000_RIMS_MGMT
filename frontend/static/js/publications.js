const ITEMS_PER_PAGE = 10;
let currentPage   = 1;
let allCards      = [];
let filteredCards = [];

// ── Filter group builders ─────────────────────────────────────────────────────
function generateTypeFilters() {
  buildFilterGroup('type-filters-container', 'type', 'type-filter', {
    journal:    'Journal Article',
    conference: 'Conference Paper',
    chapter:    'Book Chapter',
    report:     'Research Report',
    patent:     'Patent',
    other:      'Other',
  }, 'filterPublications');
}

function generateStatusFilters() {
  buildFilterGroup('status-filters-container', 'status', 'status-filter', {
    published:          'Published',
    revision_requested: 'Revision Requested',
    rejected:           'Rejected',
    accepted:           'Accepted',
    under_review:       'Under Review',
    pending:            'Pending',
    granted:            'Granted',
    draft:              'Draft',
  }, 'filterPublications');
}

// ── Filter + sort ─────────────────────────────────────────────────────────────
function filterPublications() {
  const query          = document.getElementById('search-input').value;
  const selectedTypes  = [...document.querySelectorAll('.type-filter:checked')].map(e => e.value);
  const selectedStatus = [...document.querySelectorAll('.status-filter:checked')].map(e => e.value);
  const yearFrom       = parseInt(document.getElementById('year-from').value) || 0;
  const yearTo         = parseInt(document.getElementById('year-to').value)   || 9999;
  const sortBy         = document.getElementById('sort-by').value;

  filteredCards = allCards.filter(card => {
    const combined = `${card.dataset.title} ${card.dataset.authors} ${card.dataset.journal}`;
    const year     = parseInt(card.dataset.year);
    return (
      advancedMatch(combined, query) &&
      (selectedTypes.length  === 0 || selectedTypes.includes(card.dataset.type))   &&
      (selectedStatus.length === 0 || selectedStatus.includes(card.dataset.status)) &&
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
    `${n} publication${n !== 1 ? 's' : ''} found`;
}

// ── Abstract toggle ───────────────────────────────────────────────────────────
function toggleAbstract(id) {
  const section  = document.getElementById('abstract-section-' + id);
  const btn      = event.target.closest('.abstract-toggle');
  const isHidden = section.style.display === 'none';
  section.style.display = isHidden ? 'block' : 'none';
  btn.classList.toggle('active', isHidden);
  btn.querySelector('i').style.transform = isHidden ? 'rotate(180deg)' : '';
}

// ── Authors show more/less ────────────────────────────────────────────────────
function toggleAuthors(btn) {
  const text = btn.previousElementSibling;
  if (text.classList.contains('expanded')) {
    text.classList.remove('expanded');
    btn.innerText = 'Show more';
  } else {
    text.classList.add('expanded');
    btn.innerText = 'Show less';
  }
}

// ── Status update ─────────────────────────────────────────────────────────────
function updatePubStatus(id, status) {
  fetch(`/api/publications/${id}/update-status/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
    },
    body: JSON.stringify({ status }),
  })
  .then(r => r.json())
  .then(d => { if (d.success) location.reload(); else alert(d.error || 'Failed to update status'); })
  .catch(() => alert('Failed to update status'));
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
  allCards = Array.from(document.querySelectorAll('.publication-card'));
  generateTypeFilters();
  generateStatusFilters();
  initListPage({
    filterFn:         filterPublications,
    checkboxSelector: '.type-filter, .status-filter',
    scrollSelector:   '.pub-main-content',
    filterContainers: ['type-filters-container', 'status-filters-container'],
  });
  filterPublications();

  document.querySelectorAll('.authors-text').forEach(el => {
    if (el.scrollHeight <= el.clientHeight + 2)
      el.nextElementSibling.style.display = 'none';
  });
});