// notifications.js — Full-page notification logic

const listEl   = document.getElementById('notifPageList');
const csrf = document.querySelector('meta[name="csrf-token"]')?.content;

let allNotifs     = [];
let currentFilter = 'all';

/* ═══════════════════════════════════════
   Helpers
   ═══════════════════════════════════════ */

function getNotifMeta(message) {
  const msg = message.toLowerCase();

  if (msg.includes('requested') && msg.includes('supervisor'))
    return { cls: 'supervisor', icon: 'bi-person-plus-fill', label: 'Request' };

  if (msg.includes('approved your supervisor') || 
    msg.includes('was approved') || 
    msg.includes('has been approved') ||
    msg.includes('assigned as your supervisor'))
    return { cls: 'approved', icon: 'bi-check-circle-fill', label: 'Approved' };

  if (msg.includes('rejected your supervisor') || msg.includes('was rejected') || msg.includes('has been rejected'))
    return { cls: 'rejected', icon: 'bi-x-circle-fill', label: 'Rejected' };

  if (msg.includes('submitted a new activity'))
    return { cls: 'review', icon: 'bi-clipboard-check', label: 'Review' };

  return { cls: 'info', icon: 'bi-info-circle-fill', label: 'Info' };
}

function isSupervisorRequest(message) {
  return message.toLowerCase().includes('requested') && 
         message.toLowerCase().includes('supervisor');
}

function isActivitySubmission(message) {
  return message.toLowerCase().includes('submitted a new activity');
}

function filterNotifs(notifs) {
  switch (currentFilter) {
    case 'unread':   return notifs.filter(n => !n.is_read);
    case 'approved': return notifs.filter(n => 
      n.message.toLowerCase().includes('approved your supervisor') ||
      n.message.toLowerCase().includes('was approved') ||
      n.message.toLowerCase().includes('has been approved') ||
      n.message.toLowerCase().includes('assigned as your supervisor')
    );
    case 'rejected': return notifs.filter(n => n.message.toLowerCase().includes('was rejected') || n.message.toLowerCase().includes('has been rejected'));
    case 'requests': return notifs.filter(n => isSupervisorRequest(n.message));
    case 'reviews':  return notifs.filter(n => isActivitySubmission(n.message));
    default:         return notifs;
  }
}

/* ═══════════════════════════════════════
   Render
   ═══════════════════════════════════════ */

function render() {
  const filtered = filterNotifs(allNotifs);
  const unread   = allNotifs.filter(n => !n.is_read).length;

  // Header badge
  const badge = document.getElementById('notifPageBadge');
  if (badge) {
    badge.textContent = unread;
    badge.style.display = unread > 0 ? 'inline-block' : 'none';
  }

  // Unread count on tab
  const unreadCount = document.getElementById('filterUnreadCount');
  if (unreadCount) unreadCount.textContent = unread > 0 ? `(${unread})` : '';

  // Empty
  if (filtered.length === 0) {
    const msgs = {
      all:      'No notifications yet',
      unread:   'No unread notifications',
      approved: 'No approval notifications',
      rejected: 'No rejection notifications',
      requests: 'No supervisor requests',
      reviews:  'No activity reviews',
    };
    listEl.innerHTML = `
      <div class="notif-empty-state">
        <i class="bi bi-bell-slash"></i>
        <p>${msgs[currentFilter] || 'Nothing here'}</p>
      </div>`;
    return;
  }

  listEl.innerHTML = filtered.map(n => {
    const meta    = getNotifMeta(n.message);
    const isSup   = isSupervisorRequest(n.message);

    return `
      <div class="notif-card ${n.is_read ? '' : 'unread'}" id="notif-${n.id}">
        <div class="notif-card-icon ${meta.cls}">
          <i class="bi ${meta.icon}"></i>
        </div>
        <div class="notif-card-content">
          <div class="notif-card-message">${n.message}</div>
          <div class="notif-card-meta">
            <span class="notif-card-type ${meta.cls}">${meta.label}</span>
            <span>${n.created_at}</span>
          </div>
          ${isSup ? (n.request_id ? `
            <div class="notif-card-actions" id="supActions-${n.id}">
                <button class="notif-card-btn approve" onclick="reviewRequest(${n.request_id}, 'approve', ${n.id})">
                    <i class="bi bi-check2"></i> Approve
                </button>
                <button class="notif-card-btn reject" onclick="reviewRequest(${n.request_id}, 'reject', ${n.id})">
                    <i class="bi bi-x"></i> Decline
                </button>
            </div>
          ` : `
            <div class="notif-card-resolved">
                <i class="bi bi-check-circle-fill"></i> Already responded to this request
            </div>
          `) : ''}
        </div>
        <button class="notif-card-dismiss" onclick="dismissNotif(${n.id})" title="Dismiss">
          <i class="bi bi-x"></i>
        </button>
      </div>`;
  }).join('');
}

/* ═══════════════════════════════════════
   Fetch
   ═══════════════════════════════════════ */

function loadNotifications() {
  fetch('/api/notifications/')
    .then(r => r.json())
    .then(data => {
      allNotifs = data.notifications || [];
      render();
    })
    .catch(() => {
      listEl.innerHTML = `
        <div class="notif-empty-state">
          <i class="bi bi-exclamation-triangle"></i>
          <p>Failed to load notifications</p>
        </div>`;
    });
}

/* ═══════════════════════════════════════
   Actions
   ═══════════════════════════════════════ */

// Mark all read
document.getElementById('markAllReadBtn')?.addEventListener('click', () => {
  fetch('/api/notifications/mark-read/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrf }
  }).then(() => loadNotifications()).catch(() => {});
});

// Clear all
document.getElementById('clearAllBtn')?.addEventListener('click', () => {
  if (!confirm('Clear all notifications? This cannot be undone.')) return;
  fetch('/api/notifications/clear/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrf }
  }).then(() => loadNotifications()).catch(() => {});
});

// Dismiss single (animated)
window.dismissNotif = function(id) {
  const el = document.getElementById(`notif-${id}`);
  if (el) el.classList.add('dismissing');

  setTimeout(() => {
    fetch(`/api/notifications/${id}/dismiss/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf }
    }).then(() => {
      allNotifs = allNotifs.filter(n => n.id !== id);
      render();
    }).catch(() => {});
  }, 300);
};

// Supervisor review
window.reviewRequest = function(requestId, action, notifId) {
  fetch(`/api/supervisor/review/${requestId}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ action })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      const actionsEl = document.getElementById(`supActions-${notifId}`);
      if (actionsEl) {
        actionsEl.innerHTML = action === 'approve'
          ? '<span class="notif-card-reviewed approved"><i class="bi bi-check-circle-fill"></i> Approved</span>'
          : '<span class="notif-card-reviewed rejected"><i class="bi bi-x-circle-fill"></i> Declined</span>';
      }
      setTimeout(loadNotifications, 800);
    }
  }).catch(() => {});
};

// Activity review
window.reviewActivity = function(activityId, action, notifId) {
  const reason = action === 'reject' ? (prompt('Reason for rejection (optional):') || '') : '';
  fetch(`/api/activities/review/${activityId}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ action, reason })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      const actionsEl = document.getElementById(`actActions-${notifId}`);
      if (actionsEl) {
        actionsEl.innerHTML = action === 'approve'
          ? '<span class="notif-card-reviewed approved"><i class="bi bi-check-circle-fill"></i> Approved</span>'
          : '<span class="notif-card-reviewed rejected"><i class="bi bi-x-circle-fill"></i> Rejected</span>';
      }
      setTimeout(loadNotifications, 800);
    }
  }).catch(() => {});
};

/* ═══════════════════════════════════════
   Filter tabs
   ═══════════════════════════════════════ */

const filterMap = {
  filterAll:      'all',
  filterUnread:   'unread',
  filterApproved: 'approved',
  filterRejected: 'rejected',
  filterRequests: 'requests',
  filterReviews: 'reviews',
};

Object.entries(filterMap).forEach(([btnId, filterKey]) => {
  document.getElementById(btnId)?.addEventListener('click', function() {
    currentFilter = filterKey;
    document.querySelectorAll('.notif-filter-tab').forEach(t => t.classList.remove('active'));
    this.classList.add('active');
    render();
  });
});

/* ═══════════════════════════════════════
   Init
   ═══════════════════════════════════════ */

loadNotifications();
setInterval(loadNotifications, 60000);