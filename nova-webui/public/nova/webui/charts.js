// charts.js - create neon charts and expose update hooks
(function(){
  // charts.js — simplified guaranteed loader for Chart.js with forced canvas height
  (function(){
    const charts = [
      { id: 'chart-sistema', title: 'Sistema General' },
      { id: 'chart-cache', title: 'Caché Inteligente' },
      { id: 'chart-opt', title: 'Auto-Optimización' },
      { id: 'chart-modelos', title: 'Modelos y Rendimiento' },
      { id: 'chart-rend', title: 'Rendimiento General' }
    ];

    function createSampleChart(ctx, title){
      // ensure visible height
      try { ctx.canvas.height = 230; } catch(e){}

      return new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['Ene','Feb','Mar','Abr','May'],
          datasets: [{ label: title, data: [5,9,7,12,6], borderColor: '#00eaff', backgroundColor: 'rgba(0,234,255,0.08)', tension: 0.35 }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#ffffff' } } },
          scales: { x: { ticks: { color: '#ffffff' } }, y: { ticks: { color: '#ffffff' } } }
        }
      });
    }

    window.loadCharts = async function(){
      // Try to fetch real metrics; fall back to sample if fails
      let metrics = null;
      try {
        console.log('Fetching http://localhost:8000/api/metrics...');
        const r = await fetch('http://localhost:8000/api/metrics');
        if (r.ok) {
          metrics = await r.json();
          console.log('Metrics received:', metrics);
        } else {
          console.error('Failed to fetch metrics:', r.status);
        }
      } catch(e){ 
        console.error('Error fetching metrics:', e);
      }

      charts.forEach(c => {
        const el = document.getElementById(c.id);
        if (!el) return;
        const ctx = el.getContext('2d');
        // Map chart id to metric key: 'chart-sistema' -> 'sistema'
        const key = c.id.replace('chart-', '');
        // If metrics exist and include series, use them
        if (metrics && metrics[key]) {
          try { ctx.canvas.height = 230; } catch(e){}
          console.log(`Rendering chart ${c.id} with data:`, metrics[key]);
          new Chart(ctx, { 
            type: 'line', 
            data: { 
              labels: metrics.labels || ['Ene','Feb','Mar','Abr','May'], 
              datasets:[{ 
                label:c.title, 
                data: metrics[key], 
                borderColor:'#00eaff', 
                backgroundColor:'rgba(0,234,255,0.08)', 
                tension: 0.35 
              }] 
            }, 
            options:{ 
              responsive:true, 
              maintainAspectRatio:false,
              plugins: { legend: { labels: { color: '#ffffff' } } },
              scales: { x: { ticks: { color: '#ffffff' } }, y: { ticks: { color: '#ffffff' } } }
            } 
          });
        } else {
          console.log(`Using sample data for ${c.id}`);
          // sample
          createSampleChart(ctx, c.title);
        }
      });
    };

    // auto-init after DOM ready and refresh periodically
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { setTimeout(()=>window.loadCharts(), 200); }); else setTimeout(()=>window.loadCharts(),200);
    setInterval(()=>{ if (window.loadCharts) window.loadCharts(); }, 10000);
  })();
          optStatus.innerHTML = `\n                <strong>Última ejecución:</strong> ${metrics?.optimization?.last_run || 'Hace 2h'}<br>\n                <strong>Cambios aplicados:</strong> ${metrics?.optimization?.changes_applied || 0}<br>\n                <strong>Próxima:</strong> ${metrics?.optimization?.next_run || 'En 22h'}\n            `;
        }
      }

      // Expose a loader function and auto-refresh
      window.loadCharts = initCharts;

      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initCharts); else initCharts();
      setInterval(initCharts, 10000);
    })();
