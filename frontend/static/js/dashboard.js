document.addEventListener('DOMContentLoaded', function () {

  // ─────────────────────────────────────────────
  // Sidebar Toggle
  // ─────────────────────────────────────────────
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('collapsed');
    });
  }

  // ─────────────────────────────────────────────
  // Admin Bulk Upload Form
  // ─────────────────────────────────────────────
  const uploadForm   = document.getElementById('uploadForm');
  const fileInput    = document.getElementById('fileInput');
  const fileLabel    = document.getElementById('fileInputLabel');
  const uploadResult = document.getElementById('uploadResult');

  if (uploadForm) {
    fileInput.addEventListener('change', function () {
      if (this.files.length > 0) {
        fileLabel.textContent = Array.from(this.files).map(f => f.name).join(', ');
      } else {
        fileLabel.textContent = 'Choose XML files to upload';
      }
    });

    uploadForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      if (!fileInput.files.length) {
        showResult(uploadResult, 'Please select at least one file.', 'error');
        return;
      }

      // Show custom confirm modal
      const fileList = document.getElementById('confirmFileList');
      fileList.innerHTML = Array.from(fileInput.files)
        .map(f => `<li>${f.name}</li>`).join('');
      document.getElementById('bulkConfirmModal').style.display = 'flex';

      // Wait for user decision
      const userConfirmed = await new Promise(resolve => {
        document.getElementById('confirmUploadBtn').onclick = () => {
          document.getElementById('bulkConfirmModal').style.display = 'none';
          resolve(true);
        };
        document.getElementById('cancelUploadBtn').onclick = () => {
          document.getElementById('bulkConfirmModal').style.display = 'none';
          resolve(false);
        };
      });

      if (!userConfirmed) return;

      const overlay  = document.getElementById('bulkUploadOverlay');
      const countMsg = document.getElementById('overlayFileCount');
      const btn      = document.querySelector('#uploadForm .upload-button');

      countMsg.textContent = `Processing ${fileInput.files.length} file${fileInput.files.length > 1 ? 's' : ''}…`;
      overlay.style.display = 'flex';
      if (btn) btn.disabled = true;

      const formData = new FormData();
      for (let file of fileInput.files) formData.append('files', file);

      try {
        const res  = await fetch('/bulk-upload/', {
          method: 'POST',
          body: formData,
          headers: { 'X-CSRFToken': getCsrf() }
        });
        const data = await res.json();

        overlay.style.display = 'none';
        if (btn) btn.disabled = false;

        if (data.success) {
          let html = `<p class="result-ok">${data.message}</p><ul class="result-list">`;
          (data.results || []).forEach(r => {
            if (r.success) {
              html += `<li class="result-ok">${r.researcher} — ${r.total_records} records${r.note ? ' · ' + r.note : ''}</li>`;
            } else {
              html += `<li class="result-err">${r.filename}: ${r.error}</li>`;
            }
          });
          html += '</ul>';
          uploadResult.innerHTML = html;
          fileInput.value = '';
          fileLabel.textContent = 'Choose XML files to upload';
          setTimeout(() => location.reload(), 3000);
        } else {
          let html = `<p class="result-err">✗ ${data.message}</p><ul class="result-list">`;
          (data.results || []).forEach(r => {
            html += r.success
              ? `<li class="result-ok">${r.researcher}</li>`
              : `<li class="result-err">${r.filename}: ${r.error}</li>`;
          });
          html += '</ul>';
          uploadResult.innerHTML = html;
        }
      } catch (err) {
        overlay.style.display = 'none';
        if (btn) btn.disabled = false;
        showResult(uploadResult, `Error: ${err.message}`, 'error');
      }
    });
  }

  // ─────────────────────────────────────────────
  // Researcher CCV Upload Form
  // ─────────────────────────────────────────────
  const ccvForm         = document.getElementById('ccvForm');
  const ccvFileInput    = document.getElementById('ccvFileInput');
  const ccvFileLabel    = document.getElementById('ccvFileLabel');
  const ccvUploadStatus = document.getElementById('ccvUploadStatus');
  const ccvUploadResult = document.getElementById('ccvUploadResult');

  if (ccvForm) {
    ccvFileInput.addEventListener('change', function () {
      if (this.files.length > 0) {
        ccvFileLabel.textContent = this.files[0].name;
      }
    });

    ccvForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const file = ccvFileInput.files[0];
      if (!file) {
        setStatus(ccvUploadStatus, 'Please select a file.', 'error');
        return;
      }

      setStatus(ccvUploadStatus, `Uploading ${file.name}…`, 'info');

      const formData = new FormData();
      formData.append('files', file);

      try {
        const res  = await fetch('/researcher/upload-ccv/', {
          method: 'POST',
          body: formData,
          headers: { 'X-CSRFToken': getCsrf() }
        });
        const data = await res.json();

        if (data.success) {
          setStatus(ccvUploadStatus, 'Profile updated successfully!', 'success');
          if (ccvUploadResult) {
            const r = (data.results || [])[0];
            if (r && r.success) {
              ccvUploadResult.innerHTML = `
                <ul class="result-list">
                  <li>Education: ${r.education || 0} records</li>
                  <li>Funding: ${r.funding || 0} records</li>
                  <li>Publications: ${r.publications || 0} records</li>
                  <li>Activities: ${r.activities || 0} records</li>
                  <li>Recognitions: ${r.recognitions || 0} records</li>
                  <li>Projects: ${r.projects || 0} records</li>
                </ul>`;
            }
          }
          ccvForm.reset();
          ccvFileLabel.textContent = 'Choose CCV XML file';
          setTimeout(() => location.reload(), 2500);
        } else {
          const errMsg = (data.results || [])[0]?.error || data.error || 'Upload failed';
          setStatus(ccvUploadStatus, `✗ ${errMsg}`, 'error');
        }
      } catch (err) {
        setStatus(ccvUploadStatus, `✗ Error: ${err.message}`, 'error');
      }
    });
  }

  // ─────────────────────────────────────────────
  // Charts
  // ─────────────────────────────────────────────
  initCharts();
});


function initCharts() {

  // ── Researcher: Funding over last 3 years ─────
  const fundingCtx = document.getElementById('fundingChart');
  if (fundingCtx) {
    const data = window.fundingByYear || [];
    if (data.length > 0) {
      new Chart(fundingCtx, {
        type: 'line',
        data: {
          labels: data.map(r => r.year),
          datasets: [{
            label: 'Funding ($)',
            data: data.map(r => r.total),
            borderColor: '#C8102E',
            borderWidth: 2.5,
            backgroundColor: 'rgba(200, 16, 46, 0.12)',
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#C8102E',
            pointRadius: 4,
            pointHoverRadius: 6,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { callback: v => '$' + v.toLocaleString() }
            },
            x: {
              ticks: { maxRotation: 45 }
            }
          }
        }
      });
    }
  }

  // ── Admin: Grants by Organization ─────────────
  const adminOrgEl = document.getElementById('adminOrgChart');
  if (adminOrgEl) {
    const data = window.orgStats || [];
    if (data.length > 0) {
      const sorted = [...data].sort((a, b) => a.count - b.count);
      const chart = echarts.init(adminOrgEl);
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: p => `<b>${p[0].name}</b><br/>${p[0].value} grant${p[0].value !== 1 ? 's' : ''}`
        },
        grid: {
          left: 10, right: 50, top: 10, bottom: 10,
          containLabel: true
        },
        xAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { formatter: v => Number.isInteger(v) ? v : '' }
        },
        yAxis: {
          type: 'category',
          data: sorted.map(o => o.org),
          axisLabel: { fontSize: 13, color: '#374151', overflow: 'break', width: 260 }
        },
        series: [{
          type: 'bar',
          barMaxWidth: 40,
          data: sorted.map(o => o.count),
          itemStyle: { color: '#C8102E', borderRadius: [0, 4, 4, 0] },
          label: { show: true, position: 'right', color: '#374151', fontWeight: 600 }
        }]
      });
      window.addEventListener('resize', () => chart.resize());
    }
  }
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function getCsrf() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function showResult(el, message, type) {
  if (!el) return;
  el.innerHTML = `<p class="result-${type === 'error' ? 'err' : type === 'success' ? 'ok' : 'info'}">${message}</p>`;
}

function setStatus(el, message, type) {
  if (!el) return;
  el.textContent = message;
  el.className = `upload-status upload-status-${type}`;
}

function generateColors(n) {
  const palette = [
    '#C8102E','#E63950','#2563EB','#16A34A','#D97706',
    '#7C3AED','#0891B2','#DB2777','#65A30D','#EA580C'
  ];
  return Array.from({ length: n }, (_, i) => palette[i % palette.length]);
}