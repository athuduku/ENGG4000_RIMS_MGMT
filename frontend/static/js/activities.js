const ITEMS_PER_PAGE = 10;
let currentPage   = 1;
let allCards      = [];
let filteredCards = [];

const TYPE_LABELS = {
  conference:             'Conference',
  knowledge_mobilization: 'Knowledge Mobilization',
  media:                  'Media',
  academic:               'Academic',
  presentation:           'Presentation',
  text_interview:         'Text Interview',
  broadcast:              'Broadcast Interview',
  other:                  'Other',
};

const CATEGORY_LABELS = {
  conference:             'Conference',
  knowledge_mobilization: 'Knowledge Mobilization',
  media:                  'Media / Interview',
  academic:               'Academic',
  presentation:           'Presentation',
  other:                  'Other',
};

// ── Filter group builders ─────────────────────────────────────────────────────
function generateTypeFilters() {
  buildFilterGroup('type-filters-container', 'type', 'type-filter', TYPE_LABELS, 'filterActivities');
}

function generateCategoryFilters() {
  buildFilterGroup('category-filters-container', 'category', 'category-filter', CATEGORY_LABELS, 'filterActivities');
}

// ── Filter + sort ─────────────────────────────────────────────────────────────
function filterActivities() {
  const query              = document.getElementById('search-input').value;
  const selectedTypes      = [...document.querySelectorAll('.type-filter:checked')].map(e => e.value);
  const selectedCategories = [...document.querySelectorAll('.category-filter:checked')].map(e => e.value);
  const yearFrom           = parseInt(document.getElementById('year-from').value) || 0;
  const yearTo             = parseInt(document.getElementById('year-to').value)   || 9999;
  const sortBy             = document.getElementById('sort-by').value;

  allCards = Array.from(document.querySelectorAll('.activity-card'));

  filteredCards = allCards.filter(card => {
    const combined = `${card.dataset.title} ${card.dataset.description || ''}`;
    const year     = parseInt(card.dataset.year) || 0;
    return (
      advancedMatch(combined, query) &&
      (selectedTypes.length      === 0 || selectedTypes.includes(card.dataset.type))         &&
      (selectedCategories.length === 0 || selectedCategories.includes(card.dataset.category)) &&
      year >= yearFrom && year <= yearTo
    );
  });

  const sortFns = {
    recent:       (a, b) => parseInt(b.dataset.year) - parseInt(a.dataset.year),
    oldest:       (a, b) => parseInt(a.dataset.year) - parseInt(b.dataset.year),
    'title-asc':  (a, b) => (a.dataset.title || '').localeCompare(b.dataset.title || ''),
    'title-desc': (a, b) => (b.dataset.title || '').localeCompare(a.dataset.title || ''),
  };
  if (sortFns[sortBy]) filteredCards.sort(sortFns[sortBy]);

  currentPage = 1;
  displayPage();

  const n = filteredCards.length;
  document.getElementById('results-count').textContent =
    `${n} activit${n !== 1 ? 'ies' : 'y'} found`;
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
  allCards = Array.from(document.querySelectorAll('.activity-card'));
  generateTypeFilters();
  generateCategoryFilters();
  initListPage({
    filterFn:         filterActivities,
    checkboxSelector: '.type-filter, .category-filter',
    scrollSelector:   '.main-content',
    filterContainers: ['type-filters-container', 'category-filters-container'],
  });
  filterActivities();

  document.querySelectorAll('.activity-card').forEach(card => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', function () {
      fetch(`/api/activities/${this.dataset.activityId}/`)
        .then(r => r.json())
        .then(data => openActivityModal(data))
        .catch(() => alert('Error loading activity details'));
    });
  });
});