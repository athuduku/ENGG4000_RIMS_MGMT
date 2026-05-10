const ITEMS_PER_PAGE = 10;
let currentPage   = 1;
let allCards      = [];
let filteredCards = [];

/* ── Modal ───────────────────────────────────────────────────────────────────── */
function openModal(index) {
  closeModal();
  const modal = document.getElementById(`modal-${index}`);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal() {
  document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
  document.body.style.overflow = '';
}

/* ── Tab switching ───────────────────────────────────────────────────────────── */
function switchTab(btn, paneId) {
  const tabBar = btn.closest('.modal-tabs');
  const body   = btn.closest('.modal-panel').querySelector('.modal-body');

  tabBar.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');

  body.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.getElementById(paneId).classList.add('active');
}

/* ── Init ────────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  allCards      = Array.from(document.querySelectorAll('.apr-row'));
  filteredCards = [...allCards];

  initListPage({
    filterFn:         () => {},
    checkboxSelector: '',
    scrollSelector:   '.apr-table-wrap',
    filterContainers: [],
    animateRows:      true,
  });

  displayPage();

  // Row clicks → modal
  allCards.forEach((row, i) => {
    row.addEventListener('click', () => openModal(i));
    row.addEventListener('keydown', e => { if (e.key === 'Enter') openModal(i); });
  });

  // Overlay click → close
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
  });

  // Escape → close
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  // Tab buttons (delegated)
  document.addEventListener('click', e => {
    const tab = e.target.closest('.modal-tab');
    if (tab) switchTab(tab, tab.dataset.pane);
  });

  // Close buttons
  document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', closeModal);
});
});