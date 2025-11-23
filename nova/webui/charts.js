// charts.js - clean implementation for neon charts
(function(){
  const charts = [
    { id: 'chart-sistema', key: 'sistema', title: 'Sistema General' },
    { id: 'chart-cache', key: 'cache', title: 'Caché Inteligente' },
    { id: 'chart-opt', key: 'opt', title: 'Auto-Optimización' },
    { id: 'chart-modelos', key: 'modelos', title: 'Modelos y Rendimiento' },
    { id: 'chart-rend', key: 'rend', title: 'Rendimiento General' }
  ];

  window.loadCharts = async function(){
    console.log('Loading charts from http://localhost:8000/api/metrics/routing...');
    try {
      const response = await fetch('http://localhost:8000/api/metrics/routing');
      console.log('Metrics response status:', response.status);
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const data = await response.json();
      console.log('Metrics data received:', data);

      charts.forEach(chart => {
        const canvas = document.getElementById(chart.id);
        if (!canvas) {
          console.warn('Canvas not found:', chart.id);
          return;
        }
        const ctx = canvas.getContext('2d');
        ctx.canvas.height = 230; // Force height

        const series = data[chart.key];
        if (!series) {
          console.warn('Series not found for', chart.key);
          return;
        }

        new Chart(ctx, {
          type: 'line',
          data: {
            labels: data.labels || ['Ene','Feb','Mar','Abr','May'],
            datasets: [{
              label: chart.title,
              data: series,
              borderColor: 'linear-gradient(90deg, #00f5ff, #ff00ff, #ff9500)',
              backgroundColor: 'rgba(0,245,255,0.08)',
              tension: 0.35,
              borderWidth: 3,
              pointBackgroundColor: '#00f5ff',
              pointBorderColor: '#ff00ff',
              pointRadius: 5,
              pointHoverRadius: 8
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
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
        console.log('Rendered chart:', chart.id);
      });
    } catch (error) {
      console.error('Error loading charts:', error);
    }
  };

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(window.loadCharts, 200));
  } else {
    setTimeout(window.loadCharts, 200);
  }
  setInterval(window.loadCharts, 10000);
})();