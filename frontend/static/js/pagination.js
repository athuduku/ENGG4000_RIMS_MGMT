// ─── Shared list utilities for RIMS paginated pages ───────────────────────────

function advancedMatch(text, query) {
  if (!query) return true;
  text  = text.toLowerCase();
  query = query.toLowerCase().trim();
  if (query.includes(' and ')) return query.split(' and ').every(t => text.includes(t.trim()));
  if (query.includes(' or '))  return query.split(' or ').some(t => text.includes(t.trim()));
  return text.includes(query);
}

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
  const start      = (currentPage - 1) * ITEMS_PER_PAGE;
  const end        = start + ITEMS_PER_PAGE;
  const totalPages = Math.ceil(filteredCards.length / ITEMS_PER_PAGE) || 1;

  allCards.forEach(c => c.style.display = 'none');

  filteredCards.slice(start, end).forEach((c, i) => {
    c.style.display = '';
    if (window._animateRows) {
      c.style.opacity   = '0';
      c.style.transform = 'translateY(6px)';
      setTimeout(() => {
        c.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        c.style.opacity    = '1';
        c.style.transform  = 'translateY(0)';
      }, i * 40);
    }
  });

  document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
  document.getElementById('prev-btn').disabled = currentPage === 1;
  document.getElementById('next-btn').disabled = currentPage >= totalPages;

  if (window._scrollSelector)
    document.querySelector(window._scrollSelector)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildFilterGroup(containerId, dataAttr, cssClass, labels, onchange, styles = {}) {
  const values    = [...new Set(allCards.map(c => c.dataset[dataAttr]).filter(Boolean))];
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  values.forEach(val => {
    const count = allCards.filter(c => c.dataset[dataAttr] === val).length;
    const label = labels[val] || val.charAt(0).toUpperCase() + val.slice(1).replace(/_/g, ' ');
    const style = styles[val] ? `style="${styles[val]}"` : '';
    const div   = document.createElement('div');
    div.className = 'filter-item';
    div.innerHTML = `
      <input type="checkbox" id="${dataAttr}-${val}" class="${cssClass}" value="${val}" onchange="${onchange}()">
      <label for="${dataAttr}-${val}" ${style}>${label}</label>
      <span class="filter-count">${count}</span>`;
    container.appendChild(div);
  });
}

function resetFilters() {
  document.getElementById('search-input').value = '';
  document.querySelectorAll(window._checkboxSelector).forEach(el => el.checked = false);
  document.getElementById('year-from').value = '';
  document.getElementById('year-to').value   = '';
  document.getElementById('sort-by').value   = 'recent';
  const fa = document.getElementById('filter-all');
  if (fa) fa.checked = true;
  window._filterFn();
}

function clearAllFilters() { resetFilters(); }

function initListPage({ filterFn, checkboxSelector, scrollSelector, filterContainers = [], animateRows = false }) {
  window._filterFn         = filterFn;
  window._checkboxSelector = checkboxSelector;
  window._scrollSelector   = scrollSelector;
  window._animateRows      = animateRows;

  document.getElementById('prev-btn')?.addEventListener('click', previousPage);
  document.getElementById('next-btn')?.addEventListener('click', nextPage);
  document.getElementById('filter-all')?.addEventListener('change', resetFilters);
  document.getElementById('search-input')?.addEventListener('input', filterFn);
  document.getElementById('sort-by')?.addEventListener('change', filterFn);
  document.getElementById('year-from')?.addEventListener('change', filterFn);
  document.getElementById('year-to')?.addEventListener('change', filterFn);
  document.querySelector('.clear-filters-btn')?.addEventListener('click', resetFilters);

  filterContainers.forEach(id => {
    document.getElementById(id)?.addEventListener('change', filterFn);
  });
}