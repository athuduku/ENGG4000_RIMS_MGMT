const ITEMS_PER_PAGE = 10;
let currentPage   = 1;
let allCards      = [];
let filteredCards = [];

// ─────────────────────────────────────────────
// Abstract toggle
// ─────────────────────────────────────────────
function toggleAbstract(id) {
  const section = document.getElementById('abstract-section-' + id);
  const btn     = event.target.closest('.abstract-toggle');
  const isHidden = section.style.display === 'none';

  section.style.display = isHidden ? 'block' : 'none';
  btn.classList.toggle('active', isHidden);
  btn.querySelector('i').style.transform = isHidden ? 'rotate(180deg)' : '';
}

// ─────────────────────────────────────────────
// Pagination
// ─────────────────────────────────────────────
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

  document.querySelector('.pub-main-content')?.scrollTo(0, 0);
}

// ─────────────────────────────────────────────
// Search helper — supports AND / OR
// ─────────────────────────────────────────────
function advancedMatch(text, query) {
  if (!query) return true;
  text  = text.toLowerCase();
  query = query.toLowerCase().trim();

  if (query.includes(' and ')) {
    return query.split(' and ').every(t => text.includes(t.trim()));
  }
  if (query.includes(' or ')) {
    return query.split(' or ').some(t => text.includes(t.trim()));
  }
  return text.includes(query);
}

// ─────────────────────────────────────────────
// Main filter + sort
// ─────────────────────────────────────────────
function filterPublications() {
  const query          = document.getElementById('search-input').value;
  const selectedTypes  = [...document.querySelectorAll('.type-filter:checked')].map(e => e.value);
  const selectedStatus = [...document.querySelectorAll('.status-filter:checked')].map(e => e.value);
  const yearFrom       = parseInt(document.getElementById('year-from').value)  || 0;
  const yearTo         = parseInt(document.getElementById('year-to').value)    || 9999;
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

  // Sort
  const sortFns = {
    'recent':     (a, b) => parseInt(b.dataset.year)  - parseInt(a.dataset.year),
    'oldest':     (a, b) => parseInt(a.dataset.year)  - parseInt(b.dataset.year),
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

// ─────────────────────────────────────────────
// Build type filters dynamically
// ─────────────────────────────────────────────
function generateTypeFilters() {
  const typeNames = {
    journal:    'Journal Article',
    conference: 'Conference Paper',
    chapter:    'Book Chapter',
    report:     'Research Report',
    patent:     'Patent',
    other:      'Other',
  };

  const types = [...new Set(allCards.map(c => c.dataset.type).filter(Boolean))];
  const container = document.getElementById('type-filters-container');
  container.innerHTML = '';

  types.forEach(type => {
    const count = allCards.filter(c => c.dataset.type === type).length;
    const label = typeNames[type] || type;
    const div   = document.createElement('div');
    div.className = 'filter-item';
    div.innerHTML = `
      <input type="checkbox" id="type-${type}" class="type-filter" value="${type}" onchange="filterPublications()">
      <label for="type-${type}">${label}</label>
      <span class="filter-count">${count}</span>`;
    container.appendChild(div);
  });
}

// ─────────────────────────────────────────────
// Build status filters dynamically
// ─────────────────────────────────────────────
function generateStatusFilters() {
  const statusNames = {
    published:          'Published',
    revision_requested: 'Revision Requested',
    rejected:           'Rejected',
    accepted:           'Accepted',
    under_review:       'Under Review',
    pending:            'Pending',
    granted:            'Granted',
    draft:              'Draft',
  };

  // Use data-status attribute (reliable, no class scraping)
  const statuses = [...new Set(allCards.map(c => c.dataset.status).filter(Boolean))];
  const container = document.getElementById('status-filters-container');
  container.innerHTML = '';

  statuses.forEach(status => {
    const count = allCards.filter(c => c.dataset.status === status).length;
    const label = statusNames[status] || status;
    const div   = document.createElement('div');
    div.className = 'filter-item';
    div.innerHTML = `
      <input type="checkbox" id="status-${status}" class="status-filter" value="${status}" onchange="filterPublications()">
      <label for="status-${status}">${label}</label>
      <span class="filter-count">${count}</span>`;
    container.appendChild(div);
  });
}

// ─────────────────────────────────────────────
// Reset / Clear
// ─────────────────────────────────────────────
function resetFilters() {
  document.getElementById('search-input').value = '';
  document.querySelectorAll('.type-filter, .status-filter').forEach(el => el.checked = false);
  document.getElementById('year-from').value = '';
  document.getElementById('year-to').value   = '';
  document.getElementById('sort-by').value   = 'recent';
  document.getElementById('filter-all').checked = true;
  filterPublications();
}

function clearAllFilters() { resetFilters(); }

// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  allCards = Array.from(document.querySelectorAll('.publication-card'));
  generateTypeFilters();
  generateStatusFilters();
  filterPublications();
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

function updatePubStatus(id, status) {
  fetch(`/api/publications/${id}/update-status/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    body: JSON.stringify({ status })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      location.reload();
    } else {
      alert(d.error || 'Failed to update status');
    }
  })
  .catch(() => alert('Failed to update status'));
}

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

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.authors-text').forEach(el => {
    const btn = el.nextElementSibling;
    if (el.scrollHeight <= el.clientHeight + 2) {
      btn.style.display = 'none';
    }
  });
});