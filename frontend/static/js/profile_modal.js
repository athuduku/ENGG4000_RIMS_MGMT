function openProfileModal() {
  const modal = document.getElementById('profileModal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeProfileModal() {
  const modal = document.getElementById('profileModal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Close on ESC key
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') closeProfileModal();
});