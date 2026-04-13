const ITEMS_PER_PAGE = 10;
let currentPage   = 1;
let allCards      = [];
let filteredCards = [];

// ── Display labels ────────────────────────────────────────────
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

// ── Pagination ────────────────────────────────────────────────
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

  const mainContent = document.querySelector('.main-content');
  if (mainContent) mainContent.scrollTop = 0;
}

// ── Search (AND / OR) ─────────────────────────────────────────
function advancedMatch(text, query) {
  if (!query) return true;
  text  = text.toLowerCase();
  query = query.toLowerCase().trim();
  if (query.includes(' and '))
    return query.split(' and ').every(t => text.includes(t.trim()));
  if (query.includes(' or '))
    return query.split(' or ').some(t => text.includes(t.trim()));
  return text.includes(query);
}

// ── Generate type filters ─────────────────────────────────────
function generateTypeFilters() {
  const types     = [...new Set(allCards.map(c => c.dataset.type).filter(Boolean))];
  const container = document.getElementById('type-filters-container');
  container.innerHTML = '';

  types.forEach(type => {
    const count = allCards.filter(c => c.dataset.type === type).length;
    const label = TYPE_LABELS[type] || type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ');
    const div   = document.createElement('div');
    div.className = 'filter-item';
    div.innerHTML = `
      <input type="checkbox" id="type-${type}" class="type-filter" value="${type}" onchange="filterActivities()">
      <label for="type-${type}">${label}</label>
      <span class="filter-count">${count}</span>`;
    container.appendChild(div);
  });
}

// ── Generate category filters ─────────────────────────────────
function generateCategoryFilters() {
  const categories = [...new Set(allCards.map(c => c.dataset.category).filter(Boolean))];
  const container  = document.getElementById('category-filters-container');
  container.innerHTML = '';

  categories.forEach(category => {
    const count = allCards.filter(c => c.dataset.category === category).length;
    const label = CATEGORY_LABELS[category] || category.replace(/_/g, ' ');
    const div   = document.createElement('div');
    div.className = 'filter-item';
    div.innerHTML = `
      <input type="checkbox" id="category-${category}" class="category-filter" value="${category}" onchange="filterActivities()">
      <label for="category-${category}">${label}</label>
      <span class="filter-count">${count}</span>`;
    container.appendChild(div);
  });
}


// ── Filter + sort ─────────────────────────────────────────────
function filterActivities() {
  const query              = document.getElementById('search-input').value;
  const selectedTypes      = [...document.querySelectorAll('.type-filter:checked')].map(e => e.value);
  const selectedCategories = [...document.querySelectorAll('.category-filter:checked')].map(e => e.value);
  const yearFrom           = parseInt(document.getElementById('year-from').value) || 0;
  const yearTo             = parseInt(document.getElementById('year-to').value)   || 9999;
  const sortBy             = document.getElementById('sort-by').value;

  allCards = Array.from(document.querySelectorAll('.activity-card'));

  filteredCards = allCards.filter(card => {
    const combined  = `${card.dataset.title} ${card.dataset.description || ''}`;
    const year      = parseInt(card.dataset.year) || 0;
    return (
      advancedMatch(combined, query) &&
      (selectedTypes.length      === 0 || selectedTypes.includes(card.dataset.type))     &&
      (selectedCategories.length === 0 || selectedCategories.includes(card.dataset.category)) &&
      year >= yearFrom && year <= yearTo
    );
  });

  // Sort
  const sortFns = {
    recent:     (a, b) => parseInt(b.dataset.year) - parseInt(a.dataset.year),
    oldest:     (a, b) => parseInt(a.dataset.year) - parseInt(b.dataset.year),
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

// ── Reset ─────────────────────────────────────────────────────
function resetFilters() {
  document.getElementById('search-input').value = '';
  document.querySelectorAll('.type-filter, .category-filter').forEach(el => el.checked = false);
  document.getElementById('year-from').value = '';
  document.getElementById('year-to').value   = '';
  document.getElementById('sort-by').value   = 'recent';
  document.getElementById('filter-all').checked = true;
  filterActivities();
}

function clearAllFilters() { resetFilters(); }

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  allCards = Array.from(document.querySelectorAll('.activity-card'));
  generateTypeFilters();
  generateCategoryFilters();
  filterActivities();

  // Click card → open modal
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