const ITEMS_PER_PAGE = 10;
let currentPage = 1;
let allCards = [];
let filteredCards = [];

function advancedMatch(text, query) {
  if (!query) return true;

  query = query.toLowerCase();

  if (query.includes(" and ")) {
    return query.split(" and ").every(term =>
      text.includes(term.trim())
    );
  }

  if (query.includes(" or ")) {
    return query.split(" or ").some(term =>
      text.includes(term.trim())
    );
  }

  return text.includes(query);
}

function filterProjects() {
  const searchQuery = document.getElementById('search-input').value.toLowerCase();
  const sortBy = document.getElementById('sort-by').value;

  allCards = Array.from(document.querySelectorAll('.project-card'));

  filteredCards = allCards.filter(card => {
    const combinedText = card.dataset.title + " " + card.dataset.team;
    return advancedMatch(combinedText, searchQuery);
  });

  if (sortBy === 'recent') {
    filteredCards.sort((a, b) => parseInt(b.dataset.year) - parseInt(a.dataset.year));
  } else if (sortBy === 'oldest') {
    filteredCards.sort((a, b) => parseInt(a.dataset.year) - parseInt(b.dataset.year));
  } else if (sortBy === 'title-asc') {
    filteredCards.sort((a, b) => a.dataset.title.localeCompare(b.dataset.title));
  } else if (sortBy === 'title-desc') {
    filteredCards.sort((a, b) => b.dataset.title.localeCompare(a.dataset.title));
  }

  currentPage = 1;
  displayPage();
}

document.addEventListener('DOMContentLoaded', function() {
  allCards = Array.from(document.querySelectorAll('.project-card'));
  filterProjects();
});
