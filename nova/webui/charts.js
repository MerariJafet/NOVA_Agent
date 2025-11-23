// charts.js - cyberpunk crossed graphs with neon gradients
(function(){
  const chartConfigs = [
    {
      id: 'chart-sistema',
      title: 'Sistema General',
      type: 'line',
      datasets: [
        { key: 'cpu', label: 'CPU %', color: ['#00f5ff', '#ff00ff'] },
        { key: 'ram', label: 'RAM %', color: ['#ff00ff', '#ff9500'] },
        { key: 'gpu', label: 'GPU %', color: ['#ff9500', '#00f5ff'] },
        { key: 'temp', label: 'Temp °C', color: ['#00ff00', '#ff0000'] }
      ]
    },
    {
      id: 'chart-cache',
      title: 'Caché Inteligente',
      type: 'line',
      datasets: [
        { key: 'hit_rate', label: 'Hit Rate %', color: ['#00ff00', '#00f5ff'] },
        { key: 'size_mb', label: 'Tamaño MB', color: ['#ff9500', '#ff00ff'] }
      ]
    },
    {
      id: 'chart-opt',
      title: 'Auto-Optimización',
      type: 'line',
      datasets: [
        { key: 'dolphin', label: 'Dolphin', color: ['#ff0000', '#ff9500'] },
        { key: 'mixtral', label: 'Mixtral', color: ['#0000ff', '#00f5ff'] },
        { key: 'moondream', label: 'Moondream', color: ['#00ff00', '#ff00ff'] },
        { key: 'claude', label: 'Claude', color: ['#800080', '#ff0000'] }
      ]
    },
    {
      id: 'chart-modelos',
      title: 'Modelos y Rendimiento',
      type: 'line',
      datasets: [
        { key: 'tokens_per_second', label: 'Tokens/s', color: ['#ffff00', '#ff0000'] },
        { key: 'latency_ms', label: 'Latencia ms', color: ['#ff0000', '#00f5ff'] }
      ]
    },
    {
      id: 'chart-rend',
      title: 'Rendimiento General',
      type: 'doughnut',
      data: ['avg_rating', 'queries_per_minute'],
      labels: ['Rating Promedio', 'Queries/min'],
      colors: ['#00f5ff', '#ff00ff', '#ff9500', '#00ff00', '#ff0000', '#0000ff']
    }
  ];

  window.loadCharts = async function(){
    console.log('Loading cyberpunk charts from http://localhost:8000/api/metrics/full...');
    try {
      const response = await fetch('http://localhost:8000/api/metrics/full');
      console.log('Metrics response status:', response.status);
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const data = await response.json();
      console.log('Full metrics data received:', data);

      chartConfigs.forEach(config => {
        const canvas = document.getElementById(config.id);
        if (!canvas) {
          console.warn('Canvas not found:', config.id);
          return;
        }
        const ctx = canvas.getContext('2d');
        ctx.canvas.height = 230;

        if (config.type === 'doughnut') {
          // Doughnut chart for general
          const chartData = [
            data.general.avg_rating * 20, // Scale to 100
            data.general.queries_per_minute
          ];
          new Chart(ctx, {
            type: 'doughnut',
            data: {
              labels: config.labels,
              datasets: [{
                data: chartData,
                backgroundColor: config.colors,
                borderColor: config.colors.map(c => c.replace(')', ',0.8)').replace('rgb', 'rgba')),
                borderWidth: 2
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { labels: { color: '#ffffff' } }
              }
            }
          });
        } else {
          // Line charts with gradients
          const datasets = config.datasets.map(ds => {
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, ds.color[0]);
            gradient.addColorStop(1, ds.color[1]);

            let seriesData;
            if (config.id === 'chart-sistema') {
              seriesData = data.system[ds.key];
            } else if (config.id === 'chart-cache') {
              seriesData = data.cache[ds.key];
            } else if (config.id === 'chart-opt') {
              seriesData = data.models[ds.key];
            } else if (config.id === 'chart-modelos') {
              seriesData = data.performance[ds.key];
            }

            return {
              label: ds.label,
              data: seriesData,
              borderColor: gradient,
              backgroundColor: 'rgba(0,245,255,0.08)',
              tension: 0.35,
              borderWidth: 3,
              pointBackgroundColor: ds.color[0],
              pointBorderColor: ds.color[1],
              pointRadius: 5,
              pointHoverRadius: 8,
              fill: false
            };
          });

          new Chart(ctx, {
            type: 'line',
            data: {
              labels: data.labels,
              datasets: datasets
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              animation: {
                duration: 2000,
                easing: 'easeInOutQuart'
              },
              plugins: {
                legend: { labels: { color: '#ffffff' } },
                tooltip: {
                  backgroundColor: 'rgba(0,0,0,0.8)',
                  titleColor: '#00f5ff',
                  bodyColor: '#ffffff'
                }
              },
              scales: {
                x: {
                  ticks: { color: '#ffffff' },
                  grid: { color: 'rgba(0,245,255,0.2)' }
                },
                y: {
                  ticks: { color: '#ffffff' },
                  grid: { color: 'rgba(255,0,255,0.2)' }
                }
              }
            }
          });
        }
        console.log('Rendered cyberpunk chart:', config.id);
      });
    } catch (error) {
      console.error('Error loading cyberpunk charts:', error);
    }
  };

  // Auto-init with smooth animations
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(window.loadCharts, 200));
  } else {
    setTimeout(window.loadCharts, 200);
  }
  setInterval(window.loadCharts, 10000);
})();