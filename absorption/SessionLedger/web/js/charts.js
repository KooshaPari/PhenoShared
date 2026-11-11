// SessionLedger charts — pure JS (no dependencies).

(function() {
  'use strict';

  function barChart(canvasId, data, opts) {
    opts = opts || {};
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var w = canvas.width;
    var h = canvas.height;
    var padding = 40;
    var chartW = w - 2 * padding;
    var chartH = h - 2 * padding;
    var max = Math.max.apply(null, data.map(function(d) { return d.value; })) || 1;
    var barW = chartW / data.length * 0.7;
    var gap = chartW / data.length * 0.3;

    ctx.fillStyle = opts.bg || '#0a0e1a';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = opts.axis || '#334155';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, h - padding);
    ctx.lineTo(w - padding, h - padding);
    ctx.stroke();

    data.forEach(function(d, i) {
      var barH = (d.value / max) * chartH;
      var x = padding + i * (barW + gap) + gap / 2;
      var y = h - padding - barH;
      ctx.fillStyle = opts.bar || '#60a5fa';
      ctx.fillRect(x, y, barW, barH);
      ctx.fillStyle = opts.label || '#94a3b8';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(d.label, x + barW / 2, h - padding + 14);
      ctx.fillText(d.value.toLocaleString(), x + barW / 2, y - 4);
    });
  }

  function lineChart(canvasId, data, opts) {
    opts = opts || {};
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var w = canvas.width;
    var h = canvas.height;
    var padding = 40;
    var chartW = w - 2 * padding;
    var chartH = h - 2 * padding;
    var max = Math.max.apply(null, data) || 1;
    var step = chartW / (data.length - 1);

    ctx.fillStyle = opts.bg || '#0a0e1a';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = opts.axis || '#334155';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, h - padding);
    ctx.lineTo(w - padding, h - padding);
    ctx.stroke();

    ctx.strokeStyle = opts.line || '#60a5fa';
    ctx.lineWidth = 2;
    ctx.beginPath();
    data.forEach(function(v, i) {
      var x = padding + i * step;
      var y = h - padding - (v / max) * chartH;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  document.addEventListener('DOMContentLoaded', function() {
    var toolCanvas = document.getElementById('tool-chart');
    if (toolCanvas) {
      barChart('tool-chart', [
        { label: 'claude_code', value: 58234 },
        { label: 'codex', value: 28941 },
        { label: 'cursor', value: 19547 },
        { label: 'forge', value: 12058 },
        { label: 'json_source', value: 18023 },
        { label: 'web', value: 6044 }
      ]);
    }
    var throughputCanvas = document.getElementById('throughput-chart');
    if (throughputCanvas) {
      lineChart('throughput-chart', [120, 145, 162, 198, 234, 289, 312, 287, 245, 198, 167, 142]);
    }
  });

  window.SessionLedgerCharts = { barChart: barChart, lineChart: lineChart };
})();