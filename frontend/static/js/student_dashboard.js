

document.addEventListener('DOMContentLoaded', function () {

  // ── Peer conference chart ─────────────────────────────────
  const peerData = window.peerByYear || [];
  if (peerData.length > 0) {
    const ctx = document.getElementById('peerConferenceChart');

    if (ctx && peerData && peerData.length > 0) {

      const chart2d = ctx.getContext('2d');

      // Dynamic gradient (based on canvas height)
      const gradient = chart2d.createLinearGradient(0, 0, 0, ctx.height);
      gradient.addColorStop(0, 'rgba(200, 16, 46)');

      // Destroy previous chart if exists (important for reloads)
      if (ctx._chartInstance) {
        ctx._chartInstance.destroy();
      }

      ctx._chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: peerData.map(d => d.year),
          datasets: [{
            label: 'Conferences',
            data: peerData.map(d => d.count),
            backgroundColor: gradient,
            borderColor: '#C8102E',
            borderWidth: 0,
            borderRadius: 6,
            borderSkipped: false,
            maxBarThickness: 52,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,

          plugins: {
            legend: { display: false },

            tooltip: {
              backgroundColor: '#1a1a2e',
              titleColor: '#fff',
              bodyColor: '#ddd',
              padding: 12,
              cornerRadius: 8,
              displayColors: false,

              callbacks: {
                title: items => `Year ${items[0].label}`,
                label: item => `${item.raw} conference${item.raw !== 1 ? 's' : ''} attended`
              }
            }
          },

          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                stepSize: 1,
                color: '#9ca3af',
                font: { size: 13 }
              },
              grid: { color: '#f3f4f6' },
              border: { display: false }
            },

            x: {
              ticks: {
                color: '#6b7280',
                font: { size: 13, weight: '600' }
              },
              grid: { display: false },
              border: { display: false }
            }
          }
        }
      });

    } else {
      console.warn("No peerData available for chart");
    }
  }

  // ── CCV upload ────────────────────────────────────────────
  const ccvForm   = document.getElementById('ccvForm');
  const ccvStatus = document.getElementById('ccvUploadStatus');
  const ccvLabel  = document.getElementById('ccvFileLabel');
  const ccvInput  = document.getElementById('ccvFileInput');

  if (ccvInput) {
    ccvInput.addEventListener('change', function () {
      ccvLabel.textContent = this.files[0]?.name || 'Choose CCV XML file';
    });
  }

  if (ccvForm && document.body.dataset.userType === 'student') {
    ccvForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const formData = new FormData(this);
      ccvStatus.textContent = 'Uploading...';

      fetch('/student/upload-ccv/', {
        method: 'POST',
        headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
        body: formData
      })
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            ccvStatus.textContent = 'Profile updated successfully!';
            ccvStatus.style.color = 'green';
            setTimeout(() => location.reload(), 1500);
          } else {
            ccvStatus.textContent = data.error || 'Upload failed.';
            ccvStatus.style.color = 'red';
          }
        })
        .catch(() => {
          ccvStatus.textContent = 'Upload failed. Please try again.';
          ccvStatus.style.color = 'red';
        });
    });
  }
});

window.reviewSupervisorRequest = function(requestId, action, notifId) {
  fetch(`/api/supervisor/review/${requestId}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ action })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      // Replace buttons with status text
      const item = document.getElementById(`notif-${notifId}`);
      const actions = item?.querySelector('.notif-sup-actions');
      if (actions) {
        actions.innerHTML = action === 'approved'
          ? '<span class="notif-sup-done approved"><i class="bi bi-check-circle-fill"></i> Approved</span>'
          : '<span class="notif-sup-done rejected"><i class="bi bi-x-circle-fill"></i> Declined</span>';
      }
      loadNotifications();
    }
  }).catch(() => {});
};