console.log('✅ Dashboard carregado com sucesso!');

// Atualiza o status completo a cada 5 segundos de forma contínua
setInterval(updateStatus, 5000);
updateStatus();

// Carrega os parâmetros salvos logo na primeira inicialização da página
loadCurrentParams();

// ========== ATUALIZAR STATUS EM TEMPO REAL ==========
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error(`HTTP erro! Status: ${response.status}`);
        const data = await response.json();

        // Extração segura de dados numéricos com fallback contra valores nulos
        const saldo = parseFloat(data.cliente.saldo) || 0.0;
        const lucroHoje = parseFloat(data.cliente.lucro_hoje) || 0.0;
        const metaDiaria = parseFloat(data.cliente.meta_diaria) || 0.0;

        document.getElementById('saldo-total').textContent = `$${saldo.toFixed(2)}`;
        document.getElementById('lucro-hoje').textContent = `${lucroHoje >= 0 ? '+' : ''}$${lucroHoje.toFixed(2)}`;

        // Trava de segurança: impede erro de divisão por zero (NaN / Infinity)
        const pctLucro = saldo > 0 ? ((lucroHoje / saldo) * 100).toFixed(2) : "0.00";
        document.getElementById('lucro-pct').textContent = `+${pctLucro}%`;

        document.getElementById('meta-diaria').textContent = `$${metaDiaria.toFixed(2)}`;

        const falta = metaDiaria - lucroHoje;
        document.getElementById('falta-meta').textContent = falta > 0 ? `Falta: $${falta.toFixed(2)}` : "🎯 Meta Atingida!";

        // --- SINCRONIZAÇÃO DINÂMICA DO SINALIZADOR VISUAL DO STATUS ---
        const statusElement = document.getElementById('status-text');
        const indicatorElement = document.querySelector('.status-indicator') || document.getElementById('status-dot');
        
        if (data.mestre.bot_active) {
            statusElement.textContent = "ATIVO";
            statusElement.className = "text-success fw-bold";
            if (indicatorElement) {
                indicatorElement.style.backgroundColor = "#10b981";
                indicatorElement.style.boxShadow = "0 0 12px #10b981";
            }
        } else {
            statusElement.textContent = "PARADO";
            statusElement.className = "text-danger fw-bold";
            if (indicatorElement) {
                indicatorElement.style.backgroundColor = "#ef4444";
                indicatorElement.style.boxShadow = "0 0 12px #ef4444";
            }
        }

        // Executa a atualização das listas internas de suporte
        updateSignals();
        updateLogs();
    } catch (e) {
        console.error('❌ Erro crítico ao atualizar status no painel:', e);
    }
}

// ========== CARREGAR PARAMETROS SALVOS NO INPUT (GET) ==========
async function loadCurrentParams() {
    try {
        const response = await fetch('/api/params');
        if (response.ok) {
            const data = await response.json();
            // Preenche os campos do HTML de forma automática com as regras salvas
            if (document.getElementById('strategy')) document.getElementById('strategy').value = data.estrategia || "PNY";
            if (document.getElementById('stop-loss')) document.getElementById('stop-loss').value = data.stop_loss_percent || 4.0;
            if (document.getElementById('take-profit')) document.getElementById('take-profit').value = data.take_profit_percent || 2.0;
            if (document.getElementById('percent-banca')) document.getElementById('percent-banca').value = data.quantidade_percentual || 100;
        }
    } catch (e) {
        console.error("Erro ao carregar parâmetros iniciais:", e);
    }
}

// ========== ENVIAR ATUALIZAÇÃO DA ESTRATÉGIA (POST) ==========
async function updateStrategy() {
    const strategyElement = document.getElementById('strategy');
    if (!strategyElement) return;
    const strategy = strategyElement.value;
    
    try {
        const response = await fetch('/api/strategy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ strategy })
        });
        const data = await response.json();
        if (data.success) {
            showNotification(`✅ Inteligência do Robô alterada para: ${strategy}`, 'success');
        }
    } catch (e) {
        showNotification(`❌ Falha na conexão ao alterar estratégia`, 'error');
        console.error(e);
    }
}

// ========== ENVIAR ATUALIZAÇÃO DE CONFIGURAÇÃO DE RISCO GERAL ==========
async function saveTradingParams() {
    // Captura os valores digitados nas caixas de input do formulário HTML
    const stopLoss = document.getElementById('stop-loss') ? parseFloat(document.getElementById('stop-loss').value) : 4.0;
    const takeProfit = document.getElementById('take-profit') ? parseFloat(document.getElementById('take-profit').value) : 2.0;
    const percentBanca = document.getElementById('percent-banca') ? parseFloat(document.getElementById('percent-banca').value) : 100.0;

    try {
        const response = await fetch('/api/params', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                stop_loss_percent: stopLoss,
                take_profit_percent: takeProfit,
                quantidade_percentual: percentBanca
            })
        });
        const data = await response.json();
        if (data.success) {
            showNotification('✅ Novas travas de Risco salvas e aplicadas!', 'success');
        }
    } catch (e) {
        showNotification('❌ Erro ao salvar configurações de risco', 'error');
        console.error(e);
    }
}

// ========== BOTÃO: INICIAR TRADING (POST) ==========
async function startTrading() {
    try {
        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('🚀 Comando de início enviado! Inicializando varredura...', 'success');
            updateStatus();
        }
    } catch (e) {
        showNotification('❌ Erro de rede ao iniciar trading', 'error');
        console.error(e);
    }
}

// ========== BOTÃO: PARAR TRADING (POST) ==========
async function stopTrading() {
    try {
        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('⏹️ Comando de pausa enviado! Robô em modo de espera.', 'warning');
            updateStatus();
        }
    } catch (e) {
        showNotification('❌ Erro de rede ao interromper trading', 'error');
        console.error(e);
    }
}

// ========== CARREGAR LISTA DE SINAIS DO SUPABASE ==========
async function updateSignals() {
    try {
        const response = await fetch('/api/signals');
        const signals = await response.json();
        const list = document.getElementById('signals-list');
        if (!list) return;

        if (!signals || !Array.isArray(signals) || signals.length === 0) {
            list.innerHTML = '<div class="text-muted p-2">Nenhum sinal emitido hoje...</div>';
            return;
        }

        list.innerHTML = signals.map(s => {
            const preco = parseFloat(s.price) || 0.0;
            const tipo = s.operation_type ? s.operation_type.toUpperCase() : 'BUY';
            const corTipo = tipo === 'BUY' ? 'text-success' : 'text-danger';
            
            return `<div class="p-1 border-bottom border-secondary" style="font-size: 0.9rem;">
                <span class="${corTipo} fw-bold">[${tipo}]</span> 
                <strong class="text-white">${s.symbol || 'BTCUSDT'}</strong> @ $${preco.toFixed(4)}
            </div>`;
        }).join('');
    } catch (e) {
        console.error('Erro ao processar lista de sinais:', e);
    }
}

// ========== CARREGAR BOX PRETA DE LOGS DO CONSOLE ==========
async function updateLogs() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        const list = document.getElementById('logs-list') || document.getElementById('terminal-box');
        if (!list) return;

        if (!data.logs || !Array.isArray(data.logs) || data.logs.length === 0) {
            list.innerHTML = '<div class="text-muted">> Aguardando primeira transmissão de logs do servidor VPS...</div>';
            return;
        }

        list.innerHTML = data.logs.map(log => `<div>> ${log.trim()}</div>`).join('');
        
        // Força a caixa de texto a rolar automaticamente para o final (Scroll down)
        list.scrollTop = list.scrollHeight;
    } catch (e) {
        console.error('Erro ao renderizar terminal de logs:', e);
    }
}

// ========== EXIBIÇÃO AUTOMÁTICA DE TOASTS NOTIFICAÇÕES ==========
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'warning' ? 'fa-exclamation-triangle' : 'fa-times-circle'} me-2"></i>${message}`;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 3500);
}

// ========== GERENCIADOR DO GRÁFICO CHART.JS ==========
const performanceElement = document.getElementById('performanceChart');
if (performanceElement) {
    const ctx = performanceElement.getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['00:00', '08:00', '16:00', '23:59'],
            datasets: [{
                label: 'Crescimento Banca (USDT)',
                data: [199.30, 199.40, 199.42, 199.44],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.05)',
                tension: 0.3,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: '#10b981'
            }]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        }
    });
}
