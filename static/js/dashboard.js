/**
 * ARA Dashboard v2.6 - Dynamic Flow System
 * Implementation: Infinite Scroll + Multi-Chart Analytics
 */

document.addEventListener('DOMContentLoaded', () => {
    const cyan = '#00f2ff';
    const gold = '#d29922';
    const green = '#3fb950';
    const red = '#ff4d4d';

    let currentPage = 1;
    let isLoading = false;
    let hasMore = true;
    
    // Chart references
    let solChart = null;
    let statusChart = null;
    let workerChart = null;

    const taskContainer = document.getElementById('task-container');
    const sentinel = document.getElementById('loading-sentinel');

    // --- CHART INITIALIZATION ---
    function updateCharts(data) {
        // 1. Inference Flow (Line Chart)
        const ctxFlow = document.getElementById('solChart');
        if (ctxFlow) {
            if (solChart) solChart.destroy();
            solChart = new Chart(ctxFlow, {
                type: 'line',
                data: {
                    labels: data.chart_labels || [],
                    datasets: [{
                        data: data.chart_data || [],
                        borderColor: cyan,
                        borderWidth: 2,
                        pointRadius: 2,
                        pointBackgroundColor: cyan,
                        tension: 0.4,
                        fill: true,
                        backgroundColor: 'rgba(0, 242, 255, 0.05)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { 
                            display: true, 
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#444', font: { size: 8 } }
                        }
                    }
                }
            });
        }

        // 2. Node Clusters (Doughnut)
        const ctxNodes = document.getElementById('statusChart');
        if (ctxNodes) {
            if (statusChart) statusChart.destroy();
            statusChart = new Chart(ctxNodes, {
                type: 'doughnut',
                data: {
                    labels: ['IDLE', 'ACTIVE', 'SYNCED'],
                    datasets: [{
                        data: [data.pendientes || 0, data.procesando || 0, data.exitos || 0],
                        backgroundColor: [gold, cyan, green],
                        hoverOffset: 10,
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '80%',
                    plugins: { legend: { display: false } }
                }
            });
        }

        // 3. Worker Performance (Bar Chart)
        const ctxWorker = document.getElementById('workerChart');
        if (ctxWorker && data.workers_stats) {
            if (workerChart) workerChart.destroy();
            const wLabels = data.workers_stats.map(w => w.pk);
            const wExitos = data.workers_stats.map(w => w.exitos);
            const wFallos = data.workers_stats.map(w => w.fallos);

            workerChart = new Chart(ctxWorker, {
                type: 'bar',
                data: {
                    labels: wLabels,
                    datasets: [
                        {
                            label: 'SYNCED',
                            data: wExitos,
                            backgroundColor: green,
                            borderRadius: 4
                        },
                        {
                            label: 'FAILED',
                            data: wFallos,
                            backgroundColor: red,
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { 
                            stacked: true, 
                            display: false 
                        },
                        y: { 
                            stacked: true,
                            ticks: { color: '#8b949e', font: { size: 9, family: 'JetBrains Mono' } },
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    }

    // --- DATA FETCHING ---
    async function loadStats() {
        try {
            console.log("Fetching stats...");
            const res = await fetch('/api/stats');
            if (!res.ok) throw new Error(`HTTP Error: ${res.status}`);
            const data = await res.json();
            console.log("Stats received:", data);
            
            document.getElementById('stat-volumen').textContent = (data.volumen || 0).toFixed(4);
            document.getElementById('stat-pendientes').textContent = data.pendientes || 0;
            document.getElementById('stat-procesando').textContent = data.procesando || 0;
            document.getElementById('stat-exitos').textContent = data.exitos || 0;

            updateCharts(data);
        } catch (e) { 
            console.error("Error loading stats:", e); 
        }
    }

    async function loadTasks(reset = false) {
        if (isLoading || (!hasMore && !reset)) return;
        isLoading = true;
        if (reset) {
            currentPage = 1;
            taskContainer.innerHTML = '';
            hasMore = true;
        }

        try {
            const res = await fetch(`/api/tareas?page=${currentPage}&limit=10`);
            const data = await res.json();
            
            if (!data.tareas || data.tareas.length === 0) {
                hasMore = false;
                sentinel.innerHTML = '<span>//_END_OF_BLOCKCHAIN_RECORDS</span>';
            } else {
                data.tareas.forEach(t => renderTask(t));
                currentPage++;
                hasMore = data.has_more;
                if (!hasMore) {
                    sentinel.innerHTML = '<span>//_END_OF_BLOCKCHAIN_RECORDS</span>';
                }
            }
        } catch (e) {
            console.error("Error loading tasks:", e);
        } finally {
            isLoading = false;
        }
    }

    function renderTask(t) {
        const card = document.createElement('div');
        card.className = 'glass-panel task-card';
        card.innerHTML = `
            <div style="display:flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="display:flex; align-items: center;">
                        <span class="status-indicator ${t.estado}"></span>
                        <span style="font-family: var(--font-tech); font-size: 0.7rem; color: var(--text-ghost);">TASK_ID: ${t.id}</span>
                    </div>
                    <h3 style="margin: 10px 0; font-weight: 600; font-size: 1.1rem;">${t.tarea}</h3>
                </div>
                <div style="text-align: right;">
                    <span style="font-family: var(--font-tech); color: var(--gold-24k); font-weight: 700;">${t.pago_total} SOL</span>
                </div>
            </div>

            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div class="code-block">
                    <small style="display:block; color: #444; margin-bottom: 5px;">>_INPUT_HASH</small>
                    ${t.pago_tx_cliente ? (t.pago_tx_cliente.substring(0, 25) + "...") : "WAITING_FOR_TX..."}
                </div>
                ${t.tx_hash_worker ? `
                <div class="code-block" style="border-color: rgba(63, 185, 80, 0.3);">
                    <small style="display:block; color: var(--green-signal); margin-bottom: 5px;">>_SETTLEMENT_HASH</small>
                    <span style="color: var(--green-signal);">${t.tx_hash_worker[0].substring(0, 25)}...</span>
                </div>
                ` : ''}
            </div>

            ${t.resultado ? `
            <div class="code-block" style="margin-top: 15px; background: #080a0d; color: #adbac7; border-left: 2px solid var(--green-signal);">
                <pre style="margin:0; white-space: pre-wrap;">${t.resultado.substring(0, 600)}${t.resultado.length > 600 ? '...' : ''}</pre>
            </div>
            ` : ''}
        `;
        taskContainer.appendChild(card);
    }

    // --- INTERSECTION OBSERVER ---
    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            loadTasks();
        }
    }, { threshold: 0.1 });

    observer.observe(sentinel);

    // --- INITIAL LOAD & REFRESH ---
    loadStats();
    setInterval(loadStats, 10000);
});