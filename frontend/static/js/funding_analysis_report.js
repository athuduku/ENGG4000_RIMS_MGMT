// funding_analysis_report.js

document.addEventListener('DOMContentLoaded', function () {
  initializeTimelineChart();
  initializeFundingTrendChart();
  initializeGrantsTable();
  renderPIChart();

  // Resize charts when collapsed sections are opened
  document.querySelectorAll('.section-header').forEach(header => {
    header.addEventListener('click', () => {
      setTimeout(() => {
        ['fundingChart', 'piChart', 'depletionChart'].forEach(id => {
          const el  = document.getElementById(id);
          const ch  = el && echarts.getInstanceByDom(el);
          if (ch) ch.resize();
        });
      }, 200);
    });
  });
});

// ── Year filter (server-side reload) ─────────────────────────────
function applyTimelineFilter() {
  const from = document.getElementById('timeline-year-from').value;
  const to   = document.getElementById('timeline-year-to').value;
  window.location.href = `?year_from=${from}&year_to=${to}`;
}

// ── Tab switching ─────────────────────────────────────────────────
// Accepts either a tab id string (legacy) or (id, buttonEl)
function switchTab(tabId, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-${tabId}`).classList.add('active');

  // Support both calling styles
  if (btn) {
    btn.classList.add('active');
  } else {
    // Fallback: find by onclick attribute
    const found = document.querySelector(`.tab-btn[onclick*="'${tabId}'"]`);
    if (found) found.classList.add('active');
  }
}

// ── Secured funding timeline chart ───────────────────────────────
function initializeTimelineChart() {
  const data = window.timelineChartData || [];
  if (!data.length) return;

  const chart = echarts.init(document.getElementById('depletionChart'));
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        let s = `<b>${params[0].axisValue}</b><br/>`;
        params.forEach(p => {
          const val = p.seriesIndex === 0
            ? '$' + Number(p.value).toLocaleString()
            : p.value + ' grants';
          s += `${p.marker} ${p.seriesName}: <b>${val}</b><br/>`;
        });
        return s;
      }
    },
    legend: { data: ['Secured Funding', 'Active Grants'], bottom: 4, textStyle: { fontSize: 12 } },
    grid:   { left: 16, right: 16, top: 16, bottom: 48, containLabel: true },
    xAxis:  { type: 'category', data: data.map(d => d.year), axisLabel: { fontSize: 12 } },
    yAxis: [
      {
        type: 'value', name: 'Funding ($)',
        axisLabel: { fontSize: 11, formatter: v => '$' + (v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'K' : v) }
      },
      {
        type: 'value', name: 'Grants',
        axisLabel: { fontSize: 11 }
      }
    ],
    series: [
      {
        name: 'Secured Funding', type: 'bar',
        data: data.map(d => d.funding),
        itemStyle: { color: '#C8102E', borderRadius: [3,3,0,0] }
      },
      {
        name: 'Active Grants', type: 'line',
        data: data.map(d => d.grants),
        yAxisIndex: 1, smooth: true,
        itemStyle: { color: '#3B82F6' },
        lineStyle: { width: 2 },
        symbol: 'circle', symbolSize: 6
      }
    ]
  });
  window.addEventListener('resize', () => chart.resize());
}

// ── New grants by year chart ──────────────────────────────────────
function initializeFundingTrendChart() {
  const data = window.fundingTrendData || [];
  if (!data.length) return;

  const chart = echarts.init(document.getElementById('fundingChart'));
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: p => `<b>${p[0].axisValue}</b><br/>${p[0].marker} $${Number(p[0].value).toLocaleString()}`
    },
    grid:  { left: 16, right: 16, top: 16, bottom: 32, containLabel: true },
    xAxis: { type: 'category', data: data.map(d => d.year), axisLabel: { fontSize: 12 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11, formatter: v => '$' + (v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'K' : v) } },
    series: [{
      type: 'line', data: data.map(d => d.amount),
      smooth: true,
      itemStyle: { color: '#C8102E' },
      lineStyle: { width: 2 },
      areaStyle: { color: 'rgba(200,16,46,0.08)' },
      symbol: 'circle', symbolSize: 6
    }]
  });
  window.addEventListener('resize', () => chart.resize());
}

// ── Grants table ──────────────────────────────────────────────────
const PAGE_SIZE = 10;
let allGrants      = [];
let filteredGrants = [];
let grantsPage     = 1;

function getGrantStatus(g) {
  const y = new Date().getFullYear();
  if (g.end_year < y)                            return 'Completed';
  if (g.start_year <= y && g.end_year >= y)      return 'Active';
  return 'Upcoming';
}

const STATUS_STYLES = {
  Active:    { css: 'status-active' },
  Completed: { css: 'status-completed' },
  Upcoming:  { css: 'status-upcoming' },
};

function initializeGrantsTable() {
  allGrants      = window.grantsData || [];
  filteredGrants = [...allGrants];
  renderGrantsPage();
}

function setRoleFilter(val) {
  document.getElementById('pi-role-filter').value = val;
  ['all','pi'].forEach(id => {
    const btn = document.getElementById(`pi-role-${id}`);
    if (btn) btn.className = val === id ? 'btn-sm btn-red' : 'btn-sm btn-ghost';
  });

  const notes = {
    all: 'Showing all roles — Total Grant includes full project value for Co-PI/Co-App grants.',
    pi:  'Showing PI/PA roles only — excludes grants where researcher is Co-PI or Co-Applicant.',
  };
  const noteEl = document.getElementById('pi-role-note-text');
  if (noteEl) noteEl.textContent = notes[val];

  renderPIChart();
}

function applyTableFilters() {
  const title  = (document.getElementById('filter-title')?.value  || '').toLowerCase();
  const org    = (document.getElementById('filter-org')?.value    || '').toLowerCase();
  const pi     = (document.getElementById('filter-pi')?.value     || '').toLowerCase();
  const status =  document.getElementById('filter-status')?.value || '';
  const sort   =  document.getElementById('sort-by')?.value       || '';

  filteredGrants = allGrants.filter(g =>
    g.title.toLowerCase().includes(title) &&
    g.organization.toLowerCase().includes(org) &&
    (g.pi || '').toLowerCase().includes(pi) &&
    (!status || getGrantStatus(g) === status)
  );

  const sortMap = {
    'title-asc':   (a,b) => a.title.localeCompare(b.title),
    'title-desc':  (a,b) => b.title.localeCompare(a.title),
    'amount-desc': (a,b) => b.amount - a.amount,
    'amount-asc':  (a,b) => a.amount - b.amount,
    'start-asc':   (a,b) => a.start_year - b.start_year,
    'start-desc':  (a,b) => b.start_year - a.start_year,
  };
  if (sortMap[sort]) filteredGrants.sort(sortMap[sort]);

  grantsPage = 1;
  renderGrantsPage();
}

function clearTableFilters() {
  ['filter-title', 'filter-org', 'filter-pi'].forEach(id => {
      const el = document.getElementById(id); if (el) el.value = '';
  });
  ['filter-status', 'sort-by'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  filteredGrants = [...allGrants];
  grantsPage = 1;
  renderGrantsPage();
}

function roleTag(role) {
  const map = {
    'Principal Investigator': { label: 'PI',      bg: '#ecfdf5', color: '#065f46', border: '#a7f3d0' },
    'Co-Investigator':        { label: 'Co-PI',   bg: '#eff6ff', color: '#1e40af', border: '#bfdbfe' },
    'Principal Applicant':    { label: 'PA',      bg: '#ecfdf5', color: '#065f46', border: '#a7f3d0' },
    'Co-applicant':           { label: 'Co-Ap',  bg: '#eff6ff', color: '#1e40af', border: '#bfdbfe' },
    'Other':                  { label: 'Other',   bg: '#f9fafb', color: '#6b7280', border: '#e5e7eb' },
  };
  const t = map[role] || { label: role || '—', bg: '#f9fafb', color: '#6b7280', border: '#e5e7eb' };
  return `<span style="
    background:${t.bg};color:${t.color};border:1px solid ${t.border};
    padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap;
  ">${t.label}</span>`;
}

function renderGrantsPage() {
  
  const start = (grantsPage - 1) * PAGE_SIZE;
  const page  = filteredGrants.slice(start, start + PAGE_SIZE);
  const tbody = document.getElementById('grants-table-body');
  if (!tbody) return;

  if (!page.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#9ca3af;padding:20px;">No grants match your filters.</td></tr>';
  } else {
    tbody.innerHTML = page.map(g => {
      const status     = getGrantStatus(g);
      const stStyle    = STATUS_STYLES[status];
      const currPrefix = g.currency === 'USD' ? 'USD ' : '';
      const ibme       = g.amount_to_ibme != null ? `${currPrefix}$${g.amount_to_ibme.toLocaleString()}` : '—';
      const shortTitle = g.title.length > 56 ? g.title.slice(0, 75) + '…' : g.title;
      const grantSt    = g.status?.trim() ? `<span style="font-size:11px;color:#9ca3af;display:block;margin-top:2px;">${g.status}</span>` : '';
      return `<tr>
        <td title="${g.title.replace(/"/g,'&quot;')}">${shortTitle}</td>
        <td>${g.organization}</td>
        <td>${g.pi}</td>
        <td>${roleTag(g.role)}</td>
        <td class="amt">${currPrefix}$${g.amount.toLocaleString()}</td>
        <td>${ibme}</td>
        <td><strong>${g.start_year}</strong></td>
        <td><strong>${g.end_year}</strong></td>
        <td><span class="${stStyle.css}">${status}</span>${grantSt}</td>
      </tr>`;
    }).join('');
  }

  const total = Math.ceil(filteredGrants.length / PAGE_SIZE) || 1;
  document.getElementById('grants-page-info').textContent =
    `Page ${grantsPage} of ${total} (${filteredGrants.length} grants)`;
  document.getElementById('prev-grants-btn').disabled = grantsPage === 1;
  document.getElementById('next-grants-btn').disabled = grantsPage >= total;
}

function previousGrantsPage() { if (grantsPage > 1)                                            { grantsPage--; renderGrantsPage(); } }
function nextGrantsPage()     { if (grantsPage < Math.ceil(filteredGrants.length / PAGE_SIZE)) { grantsPage++; renderGrantsPage(); } }

// ── CSV export ────────────────────────────────────────────────────
function exportCSV() {
  if (!filteredGrants.length) { alert('No grants to export.'); return; }
  const hdr  = ['Title','Organization','Currency','Amount','To IBME','Start','End','Status'];
  const rows = filteredGrants.map(g => [
    `"${g.title.replace(/"/g,'""')}"`,
    `"${g.organization.replace(/"/g,'""')}"`,
    g.currency || 'CAD', g.amount,
    g.amount_to_ibme ?? '', g.start_year, g.end_year, getGrantStatus(g)
  ]);
  const csv  = [hdr, ...rows].map(r => r.join(',')).join('\n');
  const a    = Object.assign(document.createElement('a'), {
    href:     URL.createObjectURL(new Blob([csv], { type: 'text/csv' })),
    download: 'funding_analysis.csv',
  });
  a.click(); URL.revokeObjectURL(a.href);
}

// ── Grants by researcher (PI) chart ──────────────────────────────
let activeCurrencyFilter = 'all';

function setCurrencyFilter(val) {
  activeCurrencyFilter = val;
  ['all','cad','usd'].forEach(id => {
    const btn = document.getElementById(`toggle-${id}`);
    if (btn) btn.className = val.toLowerCase() === id ? 'btn-sm btn-red' : 'btn-sm btn-ghost';
  });
  const warn = document.getElementById('pi-currency-warning');
  if (warn) warn.style.display = val === 'all' ? 'flex' : 'none';
  renderPIChart();
}


function renderPIChart() {
  const yearFrom   = parseInt(document.getElementById('pi-year-from')?.value) || window.minYear || 0;
  const yearTo     = parseInt(document.getElementById('pi-year-to')?.value)   || window.maxYear || 9999;
  const currFilter = activeCurrencyFilter.toUpperCase();
  const roleFilter = document.getElementById('pi-role-filter')?.value || 'all'; 
  const data       = window.byPIData || [];

  const filtered = data.map(row => {
    const active = row.grants.filter(g => {
      if (!g.start || g.start < yearFrom || g.start > yearTo) return false;
      if (currFilter === 'CAD' && g.currency === 'USD') return false;
      if (currFilter === 'USD' && g.currency !== 'USD') return false;
      if (roleFilter === 'pi' && !['pi', 'pa'].includes(g.role)) return false; 
      return true;
    });

    const amount         = active.reduce((s,g) => s + (g.grant_total || g.amount || 0), 0);
    const amount_to_ibme = active.reduce((s,g) => s + (g.amount_to_ibme || 0), 0);
    const amount_kept    = row.amount_kept || 0;

    return { pi: row.pi, amount, amount_to_ibme, amount_kept };
  }).filter(r => r.amount > 0).sort((a,b) => a.amount - b.amount);

  const chartEl = document.getElementById('piChart');
  if (!chartEl) return;
  const chart = echarts.getInstanceByDom(chartEl) || echarts.init(chartEl);

  const pfx   = currFilter === 'USD' ? 'USD ' : currFilter === 'CAD' ? 'CAD ' : '';
  const fmtV  = v => pfx + '$' + (v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'K' : v);
  const fmtTT = v => pfx + '$' + Number(v).toLocaleString();

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        let s = `<b>${params[0].name}</b><br/>`;
        params.forEach(p => { s += `${p.marker} ${p.seriesName}: <b>${fmtTT(p.value)}</b><br/>`; });
        return s;
      }
    },
    legend: { data: ['Total Grant', 'Amount to IBME', 'Kept at IBME'], bottom: 4, textStyle: { fontSize: 12 } },
    grid:   { left: 16, right: 16, top: 20, bottom: 80, containLabel: true },
    xAxis: {
      type: 'category',
      data: filtered.map(r => r.pi),
      axisLabel: { fontSize: 12, color: '#374151', rotate: filtered.length > 4 ? 20 : 0, interval: 0 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, formatter: v => fmtV(v) }
    },
    series: [
      {
        name: 'Total Grant', type: 'bar', barGap: '5%', barCategoryGap: '35%',
        data: filtered.map(r => r.amount),
        itemStyle: { color: '#2563EB', borderRadius: [4,4,0,0] },
        label: { show: true, position: 'top', fontSize: 11, formatter: p => fmtV(p.value) }
      },
      {
        name: 'Amount to IBME', type: 'bar',
        data: filtered.map(r => r.amount_to_ibme),
        itemStyle: { color: '#C8102E', borderRadius: [4,4,0,0] },
        label: { show: true, position: 'top', fontSize: 11, formatter: p => p.value > 0 ? fmtV(p.value) : '' }
      },
      {
        name: 'Kept at IBME', type: 'bar',
        data: filtered.map(r => r.amount_kept),
        itemStyle: { color: '#9CA3AF', borderRadius: [4,4,0,0] },
        label: { show: true, position: 'top', fontSize: 11, formatter: p => p.value > 0 ? fmtV(p.value) : '' }
      }
    ]
  });

  window.addEventListener('resize', () => chart.resize());

  // Companion table
  const tbody = document.getElementById('pi-table-body');
  if (tbody) {
    tbody.innerHTML = [...filtered].reverse().map(r => `
      <tr>
        <td><strong>${r.pi}</strong></td>
        <td class="amt">${pfx}$${Number(r.amount).toLocaleString()}</td>
        <td class="amt-green">${pfx}$${Number(r.amount_to_ibme).toLocaleString()}</td>
        <td>${r.amount_kept > 0 ? pfx + '$' + Number(r.amount_kept).toLocaleString() : '—'}</td>
      </tr>
    `).join('');
  }
}