// ─────────────────────────────────────────────
// funding_analysis_report.js
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
  const currentYear = new Date().getFullYear();
  const fromInput = document.getElementById('timeline-year-from');
  const toInput   = document.getElementById('timeline-year-to');

  if (fromInput && toInput) {
    fromInput.value = currentYear - 3;
    toInput.value   = currentYear;
  }

  initializeTimelineChart();
  initializeFundingTrendChart();
  initializeGrantsTable();
  renderPIChart();
  applyDepletionFilter();

  // Fix chart rendering inside collapsed sections
  document.querySelectorAll('.section-header').forEach(header => {
    header.addEventListener('click', function () {
      const section = this.parentElement;
      setTimeout(() => {
        ['fundingChart', 'piChart', 'depletionChart'].forEach(id => {
          const el = section.querySelector(`#${id}`);
          if (!el) return;
          let chart = echarts.getInstanceByDom(el);
          if (chart) chart.resize();
        });
      }, 200);
    });
  });
});

// ── Timeline filter (page reload for server-side data) ──
function applyTimelineFilter() {
  const yearFrom = document.getElementById('timeline-year-from').value;
  const yearTo   = document.getElementById('timeline-year-to').value;
  window.location.href = `?year_from=${yearFrom}&year_to=${yearTo}`;
}

// ── Depletion table filter ─────────────────────
function applyDepletionFilter() {
  const from = parseInt(document.getElementById('timeline-year-from')?.value) || 0;
  const to   = parseInt(document.getElementById('timeline-year-to')?.value)   || 9999;
  document.querySelectorAll('.depletion-table tbody tr').forEach(row => {
    const year = parseInt(row.children[0]?.innerText || '');
    row.style.display = (!isNaN(year) && year >= from && year <= to) ? '' : 'none';
  });
}

// ── Timeline chart ────────────────────────────
function initializeTimelineChart() {
  const data = window.timelineChartData || [];
  if (!data.length) return;

  const chart = echarts.init(document.getElementById('depletionChart'));
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Secured Funding ($)', 'Active Grants'], bottom: 0 },
    xAxis: { type: 'category', data: data.map(d => d.year) },
    yAxis: [{ type: 'value' }, { type: 'value' }],
    series: [
      {
        name: 'Secured Funding ($)', type: 'bar',
        data: data.map(d => d.funding),
        itemStyle: { color: '#C8102E' }
      },
      {
        name: 'Active Grants', type: 'line',
        data: data.map(d => d.grants),
        smooth: true, yAxisIndex: 1,
        itemStyle: { color: '#3B82F6' },
        lineStyle: { width: 3 },
        symbol: 'circle', symbolSize: 8
      }
    ]
  });
  window.addEventListener('resize', () => chart.resize());
}

// ── Funding trend chart ───────────────────────
function initializeFundingTrendChart() {
  const data = window.fundingTrendData || [];
  if (!data.length) return;

  const chart = echarts.init(document.getElementById('fundingChart'));
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.map(d => d.year) },
    yAxis: { type: 'value' },
    series: [{
      type: 'line', data: data.map(d => d.amount),
      smooth: true, itemStyle: { color: '#C8102E' }
    }]
  });
  window.addEventListener('resize', () => chart.resize());
}

// ── Grants table ──────────────────────────────
const GRANTS_PER_PAGE = 10;
let allGrants      = [];
let filteredGrants = [];
let currentGrantsPage = 1;

function getGrantStatus(grant) {
  const year = new Date().getFullYear();
  if (grant.end_year < year)                              return 'Completed';
  if (grant.start_year <= year && grant.end_year >= year) return 'Active';
  return 'Upcoming';
}

const STATUS_STYLES = {
  Active:    { bg: 'rgba(40,167,69,0.12)',  color: '#28a745' },
  Completed: { bg: 'rgba(108,117,125,0.12)', color: '#6c757d' },
  Upcoming:  { bg: 'rgba(255,193,7,0.15)',  color: '#d39e00' },
};

function initializeGrantsTable() {
  allGrants      = window.grantsData || [];
  filteredGrants = [...allGrants];
  displayGrantsPage();
}

function applyTableFilters() {
  const titleFilter  = document.getElementById('filter-title')?.value.toLowerCase()  || '';
  const orgFilter    = document.getElementById('filter-org')?.value.toLowerCase()    || '';
  const statusFilter = document.getElementById('filter-status')?.value               || '';
  const sortBy       = document.getElementById('sort-by')?.value                     || '';

  filteredGrants = allGrants.filter(grant => {
    const status = getGrantStatus(grant);
    return (
      grant.title.toLowerCase().includes(titleFilter) &&
      grant.organization.toLowerCase().includes(orgFilter) &&
      (statusFilter === '' || status === statusFilter)
    );
  });

  const sortMap = {
    'title-asc':  (a,b) => a.title.localeCompare(b.title),
    'title-desc': (a,b) => b.title.localeCompare(a.title),
    'org-asc':    (a,b) => a.organization.localeCompare(b.organization),
    'org-desc':   (a,b) => b.organization.localeCompare(a.organization),
    'start-asc':  (a,b) => a.start_year - b.start_year,
    'start-desc': (a,b) => b.start_year - a.start_year,
    'end-asc':    (a,b) => a.end_year - b.end_year,
    'end-desc':   (a,b) => b.end_year - a.end_year,
    'amount-asc': (a,b) => a.amount - b.amount,
    'amount-desc':(a,b) => b.amount - a.amount,
  };
  if (sortMap[sortBy]) filteredGrants.sort(sortMap[sortBy]);

  currentGrantsPage = 1;
  displayGrantsPage();
}

function clearTableFilters() {
  ['filter-title', 'filter-org'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  ['filter-status', 'sort-by'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  filteredGrants = [...allGrants];
  currentGrantsPage = 1;
  displayGrantsPage();
}

function displayGrantsPage() {
  const start = (currentGrantsPage - 1) * GRANTS_PER_PAGE;
  const page  = filteredGrants.slice(start, start + GRANTS_PER_PAGE);
  const tbody = document.getElementById('grants-table-body');
  if (!tbody) return;

  if (!page.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#999;">No grants match your filters</td></tr>';
  } else {
    tbody.innerHTML = page.map(grant => {
      const status      = getGrantStatus(grant);
      const style       = STATUS_STYLES[status];
      const grantStatus = grant.status && grant.status.trim() !== ''
        ? `<span style="font-size:13px;color:#666;">${grant.status}</span>` : '';
      const ibme = grant.amount_to_ibme != null
        ? `$${grant.amount_to_ibme.toLocaleString()}` : '—';
      const shortTitle = grant.title.length > 55
        ? grant.title.substring(0, 55) + '…' : grant.title;

      return `
        <tr>
          <td title="${grant.title.replace(/"/g, '&quot;')}">${shortTitle}</td>
          <td>${grant.organization}</td>
          <td class="amount-cell">$${grant.amount.toLocaleString()}</td>
          <td class="amount-cell">${ibme}</td>
          <td><strong>${grant.start_year}</strong></td>
          <td><strong>${grant.end_year}</strong></td>
          <td>
            <div style="display:flex;flex-direction:column;gap:4px;justify-content:center;">
              <span style="background:${style.bg};color:${style.color};padding:4px 10px;border-radius:4px;font-weight:600;font-size:13px;white-space:nowrap;">
                ${status}
              </span>
              ${grantStatus}
            </div>
          </td>
        </tr>`;
    }).join('');
  }

  const total = Math.ceil(filteredGrants.length / GRANTS_PER_PAGE) || 1;
  document.getElementById('grants-page-info').textContent =
    `Page ${currentGrantsPage} of ${total} (${filteredGrants.length} grants)`;
  document.getElementById('prev-grants-btn').disabled = currentGrantsPage === 1;
  document.getElementById('next-grants-btn').disabled = currentGrantsPage >= total;
}

function previousGrantsPage() {
  if (currentGrantsPage > 1) { currentGrantsPage--; displayGrantsPage(); }
}

function nextGrantsPage() {
  if (currentGrantsPage < Math.ceil(filteredGrants.length / GRANTS_PER_PAGE)) {
    currentGrantsPage++;
    displayGrantsPage();
  }
}

// ── Export CSV ─────────────────────────────────
function exportCSV() {
  if (!filteredGrants.length) { alert('No grants to export.'); return; }

  const headers = ['Title', 'Organization', 'Amount', 'To IBME', 'Start Year', 'End Year', 'Status'];
  const rows = filteredGrants.map(g => [
    `"${g.title.replace(/"/g, '""')}"`,
    `"${g.organization.replace(/"/g, '""')}"`,
    g.amount,
    g.amount_to_ibme != null ? g.amount_to_ibme : '',
    g.start_year,
    g.end_year,
    getGrantStatus(g)
  ]);

  const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'funding_analysis.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// ── Tab switching ─────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.add('active');
  document.querySelector(`[onclick="switchTab('${tab}')"]`).classList.add('active');
}

// ── Grants by PI chart ────────────────────────
function renderPIChart() {
  const yearFrom = parseInt(document.getElementById('pi-year-from')?.value) || window.minYear || 0;
  const yearTo   = parseInt(document.getElementById('pi-year-to')?.value)   || window.maxYear || 9999;
  const data     = window.byPIData || [];
  const currentYear = new Date().getFullYear();

  const filtered = data.map(row => {
    // Filter grants by year range
    const activeGrants = row.grants.filter(g =>
      g.start && g.start >= yearFrom && g.start <= yearTo
    );

    // Use ALL grants for this PI — no role filtering
    const amount = activeGrants.reduce((s, g) => s + (g.amount || 0), 0);
    const amount_to_ibme = activeGrants.reduce((s, g) => s + (g.amount_to_ibme || 0), 0);
    const amount_stayed_ibme = activeGrants.reduce((s, g) => {
      if (g.end && g.end >= currentYear) {
        return s + (g.amount_to_ibme || 0);
      }
      return s;
    }, 0);

    return { pi: row.pi, amount, amount_to_ibme, amount_stayed_ibme };
  })
  .filter(r => r.amount > 0)
  .sort((a, b) => a.amount - b.amount);

  const chartEl = document.getElementById('piChart');
  if (!chartEl) return;

  const chart = echarts.getInstanceByDom(chartEl) || echarts.init(chartEl);

  const fmtAmt = v => '$' + (
    v >= 1000000 ? (v / 1000000).toFixed(1) + 'M' :
    v >= 1000    ? (v / 1000).toFixed(0) + 'K' :
    v
  );

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        let s = `<b>${params[0].name}</b><br/>`;
        params.forEach(p => {
          s += `${p.marker}${p.seriesName}: $${Number(p.value).toLocaleString()}<br/>`;
        });
        return s;
      }
    },
    legend: {
      data: ['Total Grant', 'Amount to IBME', 'Stayed at IBME'],
      bottom: 0
    },
    grid: { left: 10, right: 80, top: 10, bottom: 40, containLabel: true },
    xAxis: { type: 'value', axisLabel: { formatter: fmtAmt } },
    yAxis: {
      type: 'category',
      data: filtered.map(r => r.pi),
      axisLabel: { fontSize: 13, color: '#374151' }
    },
    series: [
      {
        name: 'Total Grant', type: 'bar',
        data: filtered.map(r => r.amount),
        itemStyle: { color: '#2563EB', borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', formatter: p => fmtAmt(p.value) }
      },
      {
        name: 'Amount to IBME', type: 'bar',
        data: filtered.map(r => r.amount_to_ibme),
        itemStyle: { color: '#C8102E', borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', formatter: p => p.value > 0 ? fmtAmt(p.value) : '' }
      },
      {
        name: 'Stayed at IBME', type: 'bar',
        data: filtered.map(r => r.amount_stayed_ibme),
        itemStyle: { color: '#9CA3AF', borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', formatter: p => p.value > 0 ? fmtAmt(p.value) : '' }
      }
    ]
  });

  window.addEventListener('resize', () => chart.resize());

  // ── Table update ─────────────────────────
  const tbody = document.getElementById('pi-table-body');
  if (tbody) {
    tbody.innerHTML = [...filtered].reverse().map(r => `
      <tr>
        <td><strong>${r.pi}</strong></td>
        <td class="amount-cell">$${Number(r.amount).toLocaleString()}</td>
        <td class="amount-cell">$${Number(r.amount_to_ibme).toLocaleString()}</td>
      </tr>
    `).join('');
  }
}