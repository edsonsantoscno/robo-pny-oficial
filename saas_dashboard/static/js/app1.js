// ========== INICIALIZAÇÃO ==========
console.log('✅ Dashboard carregado!');

// Atualiza status a cada 5 segundos
setInterval(updateStatus, 5000);
updateStatus();

// ========== ATUALIZAR STATUS ==========
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        document.getElementById('saldo-total').textContent = `$${data.cliente.saldo.toFixed(2)}`;
        document.getElementById('lucro-hoje').textContent = `+$${data.cliente.lucro_hoje.toFixed(2)}`;

        const pctLucro = ((data.cliente.lucro_hoje / data.cliente.saldo) * 100).toFixed(2);
        document.getElementById('lucro-pct').textContent = `+${pctLucro}%`;

        document.getElementById('meta-diaria').textContent = `$${data.cliente.meta_diaria.toFixed(2)}`;

        const falta = data.cliente.meta_diaria - data.cliente.lucro_hoje;
        document.getElementById('falta-meta').textContent = `Falta: $${falta.toFixed(2)}`;

        updateSignals();
        updateLogs();
    } catch (e) {
        console.error('Erro ao atualizar status:', e);
    }
}

// ========== ATUALIZAR ESTRATÉGIA ==========
async function updateStrategy() {
    const strategy = document.getElementById('strategy').value;
    try {
        const response = await fetch('/api/strategy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ strategy })
        });
        const data = await response.json();
        if (data.success) {
            showNotification(`✅ Estratégia alterada para: ${strategy}`, 'success');
        }
    } catch (e) {
        showNotification(`❌ Erro ao alterar estratégia`, 'error');
        console.error(e);
    }
}

// ========== ATUALIZAR STOP LOSS ==========
async function updateStopLoss() {
    const stopLoss = document.getElementById('stop-loss').value;
    try {
        const response = await fetch('/api/params', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stop_loss_percent: parseFloat(stopLoss) })
        });
        const data = await response.json();
        if (data.success) {
            showNotification(`✅ Stop Loss: ${stopLoss}%`, 'success');
        }
    } catch (e) {
        showNotification(`❌ Erro ao alterar Stop Loss`, 'error');
        console.error(e);
    }
}

// ========== ATUALIZAR TAKE PROFIT ==========
async function updateTakeProfit() {
    const takeProfit = document.getElementById('take-profit').value;
    try {
        const response = await fetch('/api/params', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ take_profit_percent: parseFloat(takeProfit) })
        });
        const data = await response.json();
        if (data.success) {
            showNotification(`✅ Take Profit: ${takeProfit}%`, 'success');
        }
    } catch (e) {
        showNotification(`❌ Erro ao alterar Take Profit`, 'error');
        console.error(e);
    }
}

// ========== ATUALIZAR % BANCA ==========
async function updatePercentBanca() {
    const percent = document.getElementById('percent-banca').value;
    try {
        const response = await fetch('/api/params', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quantidade_percentual: parseFloat(percent) })
        });
        const data = await response.json();
        if (data.success) {
            showNotification(`✅ % Banca: ${percent}%`, 'success');
        }
    } catch (e) {
        showNotification(`❌ Erro ao alterar % Banca`, 'error');
        console.error(e);
    }
}

// ========== INICIAR TRADING ==========
async function startTrading() {
    try {
        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('🚀 Trading iniciado!', 'success');
        }
    } catch (e) {
        showNotification('❌ Erro ao iniciar trading', 'error');
        console.error(e);
    }
}

// ========== PARAR TRADING ==========
async function stopTrading() {
    try {
        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('⏹️ Trading parado!', 'success');
        }
    } catch (e) {
        showNotification('❌ Erro ao parar trading', 'error');
        console.error(e);
    }
}

// ========== CARREGAR SINAIS ==========
async function updateSignals() {
    try {
        const response = await fetch('/api/signals');
        const signals = await response.json();
        const list = document.getElementById('signals-list');

        if (!signals || signals.length === 0) {
            list.innerHTML = '<div>Nenhum sinal ainda...</div>';
            return;
        }

        list.innerHTML = signals.map(s => `
            <div>
                <strong>[${s.operation_type}]</strong> ${s.symbol} @ $${parseFloat(s.price).toFixed(2)} | Qtd: ${parseFloat(s.quantity).toFixed(4)}
            </div>
        `).join('');
    } catch (e) {
        console.error('Erro ao carregar sinais:', e);
    }
}

// ========== CARREGAR LOGS ==========
async function updateLogs() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        const list = document.getElementById('logs-list');

        if (!data.logs || data.logs.length === 0) {
            list.innerHTML = '<div>Nenhum log ainda...</div>';
            return;
        }

        list.innerHTML = data.logs.map(log => `<div>> ${log.trim()}</div>`).join('');
        list.scrollTop = list.scrollHeight;
    } catch (e) {
        console.error('Erro ao carregar logs:', e);
    }
}

// ========== NOTIFICAÇÕES ==========
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ========== GRÁFICO DE PERFORMANCE ==========
const ctx = document.getElementById('performanceChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '23:59'],
        datasets: [{
            label: 'Banca USDT',
            data: [199.30, 199.35, 199.40, 199.44, 199.42, 199.45, 199.44],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.4,
            fill: true,
            pointRadius: 5,
            pointBackgroundColor: '#10b981',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverRadius: 7
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                labels: {
                    font: { size: 12, weight: '600' },
                    color: '#1f2937'
                }
            }
        },
        scales: {
            y: {
                beginAtZero: false,
                min: 199,
                max: 200,
                ticks: {
                    callback: function(value) {
                        return '$' + value.toFixed(2);
                    },
                    font: { size: 11 }
                },
                grid: {
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            },
            x: {
                ticks: {
                    font: { size: 11 }
                },
                grid: {
                    display: false
                }
            }
        }
    }
});