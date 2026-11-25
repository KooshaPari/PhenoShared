// pheno-harness charts — pure JS (no dependencies).

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

    ctx.fillStyle = opts.bg || '#ffffff';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = opts.axis || '#e7e5e4';
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
      ctx.fillStyle = opts.bar || '#ea580c';
      ctx.fillRect(x, y, barW, barH);
      ctx.fillStyle = opts.label || '#57534e';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(d.label, x + barW / 2, h - padding + 14);
      ctx.fillText(d.value + '%', x + barW / 2, y - 4);
    });
  }

  document.addEventListener('DOMContentLoaded', function() {
    var suiteCanvas = document.getElementById('suite-chart');
    if (suiteCanvas) {
      barChart('suite-chart', [
        { label: 'swe-lite', value: 71 },
        { label: 'cybench', value: 64 },
        { label: 'intercode', value: 88 },
        { label: 'apex', value: 52 },
        { label: 'dsbench', value: 67 },
        { label: 'ml-dev', value: 73 },
        { label: 'swe-ver-mini', value: 58 },
        { label: 'tau-airline', value: 81 },
        { label: 'swe-ver', value: 49 },
        { label: 'terminal', value: 76 },
        { label: 'arc-agi-2', value: 34 },
        { label: 'mswe', value: 61 },
        { label: 'anthropic', value: 79 },
        { label: 'forge-stack', value: 68 }
      ]);
    }
  });

  window.PhenoCharts = { barChart: barChart };
})();