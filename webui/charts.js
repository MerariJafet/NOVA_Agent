// charts.js - cyberpunk crossed graphs with neon gradients and real-time scrolling
(function(){
  const chartInstances = {};
  const chartDataBuffers = {}; // Store historical data for scrolling effect
  const MAX_POINTS = 100; // Number of points to display

  const chartConfigs = [
    {
      id: 'chart-sistema',
      title: 'Sistema General',
      type: 'line',
      datasets: [
        { key: 'cpu', label: 'CPU %', color: '#00BFFF' }, // Deep Sky Blue
        { key: 'ram', label: 'RAM %', color: '#1E90FF' }, // Dodger Blue
        { key: 'gpu', label: 'GPU %', color: '#00FF7F' }, // Spring Green
        { key: 'temp', label: 'Temp °C', color: '#32CD32' }  // Lime Green
      ]
    },
    {
      id: 'chart-cache',
      title: 'Caché Inteligente',
      type: 'line',
      datasets: [
        { key: 'hit_rate', label: 'Hit Rate %', color: '#00008B' }, // Dark Blue
        { key: 'size_mb', label: 'Tamaño MB', color: '#006400' }  // Dark Green
      ]
    },
    {
      id: 'chart-opt',
      title: 'Auto-Optimización',
      type: 'line',
      datasets: [
        { key: 'dolphin', label: 'Dolphin', color: '#00CED1' }, // Dark Turquoise
        { key: 'mixtral', label: 'Mixtral', color: '#008080' }, // Teal
        { key: 'moondream', label: 'Moondream', color: '#20B2AA' }, // Light Sea Green
        { key: 'claude', label: 'Claude', color: '#48D1CC' }  // Medium Turquoise
      ]
    },
    {
      id: 'chart-modelos',
      title: 'Modelos y Rendimiento',
      type: 'line',
      datasets: [
        { key: 'tokens_per_second', label: 'Tokens/s', color: '#00FA9A' }, // Medium Spring Green
        { key: 'latency_ms', label: 'Latencia ms', color: '#00FF00' }  // Lime
      ]
    },
    {
      id: 'chart-rend',
      title: 'Rendimiento General',
      type: 'doughnut',
      data: ['avg_rating', 'queries_per_minute'],
      labels: ['Rating Promedio', 'Queries/min'],
      colors: ['#00BFFF', '#00FF7F']  // Deep Sky Blue, Spring Green
    }
  ];

  // Function to generate next point based on last value
  function generateNextPoint(lastValue, variation = 5) {
    const noise = (Math.random() - 0.5) * variation * 2;
    const trend = (Math.random() - 0.5) * variation * 0.5;
    return Math.max(0, lastValue + noise + trend);
  }

  window.loadCharts = async function(){
    console.log('Loading cyberpunk scrolling charts from http://localhost:8000/api/metrics/full...');
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
          const chartData = [
            data.general.avg_rating * 20, // Scale to 100
            data.general.queries_per_minute
          ];

          if (chartInstances[config.id]) {
            const chart = chartInstances[config.id];
            chart.data.datasets[0].data = chartData;
            chart.update();
          } else {
            chartInstances[config.id] = new Chart(ctx, {
              type: 'doughnut',
              data: {
                labels: config.labels,
                datasets: [{
                  data: chartData,
                  backgroundColor: config.colors,
                  borderColor: config.colors.map(c => c.replace(')', ',0.8)').replace('rgb', 'rgba')),
                  borderWidth: 3,
                  hoverBorderWidth: 5,
                  hoverBorderColor: '#ffffff',
                  // 3D effect with cutout and shadow
                  cutout: '60%', // Creates a ring for 3D appearance
                  shadowOffsetX: 3,
                  shadowOffsetY: 3,
                  shadowBlur: 10,
                  shadowColor: 'rgba(0,0,0,0.5)'
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { 
                    labels: { 
                      color: '#ffffff',
                      font: { size: 14, weight: 'bold' }
                    },
                    position: 'bottom'
                  },
                  tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.9)',
                    titleColor: '#00f5ff',
                    bodyColor: '#ffffff',
                    cornerRadius: 10,
                    displayColors: false,
                    callbacks: {
                      label: function(context) {
                        return context.label + ': ' + context.parsed.toFixed(1);
                      }
                    }
                  }
                },
                // 3D rotation effect
                rotation: -90,
                circumference: 360,
                animation: {
                  animateRotate: true,
                  animateScale: true
                }
              }
            });
          }
        } else {
          // Initialize or update data buffers for scrolling effect
          if (!chartDataBuffers[config.id]) {
            chartDataBuffers[config.id] = {};
            config.datasets.forEach(ds => {
              let initialData;
              if (config.id === 'chart-sistema') {
                initialData = data.system[ds.key];
              } else if (config.id === 'chart-cache') {
                initialData = data.cache[ds.key];
              } else if (config.id === 'chart-opt') {
                initialData = data.models[ds.key];
              } else if (config.id === 'chart-modelos') {
                initialData = data.performance[ds.key];
              }
              chartDataBuffers[config.id][ds.key] = [...initialData];
            });
          } else {
            // Add new points and remove old ones for scrolling effect
            config.datasets.forEach(ds => {
              const buffer = chartDataBuffers[config.id][ds.key];
              const lastValue = buffer[buffer.length - 1];
              const newPoint = generateNextPoint(lastValue);
              buffer.push(newPoint);
              if (buffer.length > MAX_POINTS) {
                buffer.shift(); // Remove oldest point
              }
            });
          }

          const datasets = config.datasets.map(ds => {
            const seriesData = chartDataBuffers[config.id][ds.key];
            
            const baseColor = ds.color;
            
            // Create futuristic gradient with depth effect
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, baseColor + 'CC'); // Semi-transparent top
            gradient.addColorStop(0.5, baseColor + '66');
            gradient.addColorStop(1, baseColor + '33'); // Faded bottom for depth

            return {
              label: ds.label,
              data: seriesData,
              borderColor: baseColor,
              backgroundColor: gradient,
              tension: 0.3, // Smooth curves
              borderWidth: 3,
              pointBackgroundColor: baseColor,
              pointBorderColor: baseColor,
              pointRadius: 0, // Hide points for clean look
              pointHoverRadius: 6,
              fill: true // Area fill for modern look
            };
          });

          const labels = Array.from({length: MAX_POINTS}, (_, i) => (i + 1).toString());

          if (chartInstances[config.id]) {
            const chart = chartInstances[config.id];
            chart.data.labels = labels;
            chart.data.datasets.forEach((ds, idx) => {
              ds.data = datasets[idx].data;
            });
            chart.update('none'); // Update without animation for smooth scrolling
          } else {
            chartInstances[config.id] = new Chart(ctx, {
              type: 'line',
              data: {
                labels: labels,
                datasets: datasets
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                  duration: 0, // Disable animation for real-time feel
                  easing: 'linear'
                },
                plugins: {
                  legend: { labels: { color: '#ffffff' } },
                  tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.9)',
                    titleColor: '#00f5ff',
                    bodyColor: '#ffffff',
                    cornerRadius: 10,
                    displayColors: false
                  }
                },
                scales: {
                  x: {
                    display: false, // Hide x-axis for cleaner look
                    grid: { display: false }
                  },
                  y: {
                    ticks: { color: '#ffffff', font: { size: 12 } },
                    grid: { color: 'rgba(0,245,255,0.1)' },
                    beginAtZero: true
                  }
                },
                elements: {
                  point: {
                    hoverBorderWidth: 3
                  }
                }
              }
            });
          }
        }
        console.log('Rendered scrolling cyberpunk chart:', config.id);
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
})();
