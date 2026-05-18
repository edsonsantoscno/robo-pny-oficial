console.log('✅ Dashboard carregado com sucesso!');

// Atualiza o status completo a cada 5 segundos de forma contínua
setInterval(updateStatus, 5000);
updateStatus();

// Carrega os parâmetros salvos logo na primeira inicialização da página
loadCurrentParamsMestre(); // Carrega parâmetros do mestre
loadCurrentParamsCliente(); // Carrega parâmetros do cliente

// ========== ATUALIZAR STATUS EM TEMPO REAL ==========
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error(`HTTP erro! Status: ${response.status}`);
        const data = await response.json();

        // --- Status do Mestre ---
        const mestreSaldo = parseFloat(data.mestre.saldo) || 0.0;
        const mestreLucroHoje = parseFloat(data.mestre.lucro_hoje) || 0.0;
        const mestreMetaDiaria = parseFloat(data.mestre.meta_diaria) || 0.0;

        document.getElementById('saldo-total').textContent = `$${mestreSaldo.toFixed(2)}`;
        document.getElementById('lucro-hoje').textContent = `${mestreLucroHoje >= 0 ? '+' : ''}$${mestreLucroHoje.toFixed(2)}`;
        const mestrePctLucro = mestreSaldo > 0 ? ((mestreLucroHoje / mestreSaldo) * 100).toFixed(2) : "0.00";
        document.getElementById('lucro-pct').textContent = `+${mestrePctLucro}%`;
        document.getElementById('meta-diaria').textContent = `$${mestreMetaDiaria.toFixed(2)}`;
        const mestreFalta = mestreMetaDiaria - mestreLucroHoje;
        document.getElementById('falta-meta').textContent = mestreFalta > 0 ? `Falta: $${mestreFalta.toFixed(2)}` : "🎯 Meta Atingida!";

        const mestreStatusElement = document.getElementById('status-text');
        const mestreIndicatorElement = document.querySelector('.status-indicator');
        if (data.mestre.bot_active) {
            mestreStatusElement.textContent = "ATIVO";
            mestreStatusElement.className = "text-success fw-bold";
            if (mestreIndicatorElement) {
                mestreIndicatorElement.style.backgroundColor = "#10b981";
                mestreIndicatorElement.style.boxShadow = "0 0 12px #10b981";
            }
        } else {
            mestreStatusElement.textContent = "PARADO";
            mestreStatusElement.className = "text-danger fw-bold";
            if (mestreIndicatorElement) {
                mestreIndicatorElement.style.backgroundColor = "#ef4444";
                mestreIndicatorElement.style.boxShadow = "0 0 12px #ef4444";
            }
        }

        // --- Status do Cliente ---
        const clienteSaldo = parseFloat(data.cliente.saldo) || 0.0;
        const clienteLucroHoje = parseFloat(data.cliente.lucro_hoje) || 0.0;
        const clienteMetaDiaria = parseFloat(data.cliente.meta_diaria) || 0.0;

        // Atualizar elementos do dashboard_cliente.html (se estiver usando)
        // Exemplo: document.getElementById('cliente-saldo-total').textContent = `$${clienteSaldo.toFixed(2)}`;
        // ... e assim por diante para os outros elementos do cliente

        // Atualiza o status do botão de controle do cliente
        const btnStartCliente = document.getElementById('btn-start-cliente');
        const btnStopCliente = document.getElementById('btn-stop-cliente');
        if (btnStartCliente && btnStopCliente) {
            if (data.cliente.bot_active) {
                btnStartCliente.disabled = true;
                btnStopCliente.disabled = false;
            } else {
                btnStartCliente.disabled = false;
                btnStopCliente.disabled = true;
            }
        }


        // Executa a atualização das listas internas de suporte
        updateSignals();
        updateLogsMestre(); // Logs do Mestre
        updateLogsCliente(); // Logs do Cliente
    } catch (e) {
        console.error('❌ Erro crítico ao atualizar status no painel:', e);
    }
}

// ========== CARREGAR PARAMETROS SALVOS NO INPUT (GET) - MESTRE ==========
async function loadCurrentParamsMestre() {
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
        console.error("Erro ao carregar parâmetros iniciais do Mestre:", e);
    }
}

// ========== CARREGAR PARAMETROS SALVOS NO INPUT (GET) - CLIENTE ==========
async function loadCurrentParamsCliente() {
    try {
        const response = await fetch('/api/cliente/params');
        if (response.ok) {
            const data = await response.json();
            // Preenche os campos do HTML de forma automática com as regras salvas para o cliente
            // Exemplo: if (document.getElementById('cliente-stop-loss')) document.getElementById('cliente-stop-loss').value = data.stop_loss_percent || 4.0;
            // ... e assim por diante para os outros parâmetros do cliente
        }
    } catch (e) {
        console.error("Erro ao carregar parâmetros iniciais do Cliente:", e);
    }
}

// ========== ENVIAR ATUALIZAÇÃO DA ESTRATÉGIA (POST) - MESTRE ==========
async function updateStrategyMestre() {
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
            showNotification(`✅ Inteligência do Robô MESTRE alterada para: ${strategy}`, 'success');
        }
    } catch (e) {
        showNotification(`❌ Falha na conexão ao alterar estratégia do Mestre`, 'error');
        console.error(e);
    }
}

// ========== ENVIAR ATUALIZAÇÃO DE CONFIGURAÇÃO DE RISCO GERAL - MESTRE ==========
async function saveTradingParamsMestre() {
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
            showNotification('✅ Novas travas de Risco do MESTRE salvas e aplicadas!', 'success');
        }
    } catch (e) {
        showNotification('❌ Erro ao salvar configurações de risco do Mestre', 'error');
        console.error(e);
    }
}

// ========== BOTÃO: INICIAR TRADING (POST) - MESTRE ==========
async function startTradingMestre() {
    try {
        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('🚀 Comando de início do MESTRE enviado! Inicializando varredura...', 'success');
            updateStatus();
        }
    } catch (e) {
        showNotification('❌ Erro de rede ao iniciar trading do Mestre', 'error');
        console.error(e);
    }
}

// ========== BOTÃO: PARAR TRADING (POST) - MESTRE ==========
async function stopTradingMestre() {
    try {
        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('⏹️ Comando de pausa do MESTRE enviado! Robô em modo de espera.', 'warning');
            updateStatus();
        }
    } catch (e) {
        showNotification('❌ Erro de rede ao interromper trading do Mestre', 'error');
        console.error(e);
    }
}

// ========== BOTÃO: INICIAR TRADING (POST) - CLIENTE ==========
async function startTradingCliente() {
    try {
        const response = await fetch('/api/cliente/start', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('🚀 Comando de início do CLIENTE enviado! Inicializando cópia...', 'success');
            updateStatus();
        }
    } catch (e) {
        showNotification('❌ Erro de rede ao iniciar trading do Cliente', 'error');
        console.error(e);
    }
}

// ========== BOTÃO: PARAR TRADING (POST) - CLIENTE ==========
async function stopTradingCliente() {
    try {
        const response = await fetch('/api/cliente/stop', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('⏹️ Comando de pausa do CLIENTE enviado! Robô em modo de espera.', 'warning');
            updateStatus();
        }
    } catch (e) {
        showNotification('❌ Erro de rede ao interromper trading do Cliente', 'error');
        console.error(e);
    }
}

// ========== CARREGAR LISTA DE SINAIS DO MESTRE ==========
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

// ========== CARREGAR BOX PRETA DE LOGS DO CONSOLE - MESTRE ==========
async function updateLogsMestre() {
    try {
        const response = await fetch('/api/logs/mestre');
        const data = await response.json();
        const list = document.getElementById('logs-list-mestre') || document.getElementById('terminal-box-mestre'); // Novo ID
        if (!list) return;

        if (!data.logs || !Array.isArray(data.logs) || data.logs.length === 0) {
            list.innerHTML = '<div class="text-muted">> Aguardando primeira transmissão de logs do Mestre...</div>';
            return;
        }

        list.innerHTML = data.logs.map(log => `<div>> ${log.trim()}</div>`).join('');

        // Força a caixa de texto a rolar automaticamente para o final (Scroll down)
        list.scrollTop = list.scrollHeight;
    } catch (e) {
        console.error('Erro ao renderizar terminal de logs do Mestre:', e);
    }
}

// ========== CARREGAR BOX PRETA DE LOGS DO CONSOLE - CLIENTE ==========
async function updateLogsCliente() {
    try {
        const response = await fetch('/api/logs/cliente');
        const data = await response.json();
        const list = document.getElementById('logs-list-cliente') || document.getElementById('terminal-box-cliente'); // Novo ID
        if (!list) return;

        if (!data.logs || !Array.isArray(data.logs) || data.logs.length === 0) {
            list.innerHTML = '<div class="text-muted">> Aguardando primeira transmissão de logs do Cliente...</div>';
            return;
        }

        list.innerHTML = data.logs.map(log => `<div>> ${log.trim()}</div>`).join('');

        // Força a caixa de texto a rolar automaticamente para o final (Scroll down)
        list.scrollTop = list.scrollHeight;
    } catch (e) {
        console.error('Erro ao renderizar terminal de logs do Cliente:', e);
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

// Adicionar event listeners para os botões do cliente (se existirem no HTML)
document.addEventListener('DOMContentLoaded', () => {
    const btnStartCliente = document.getElementById('btn-start-cliente');
    const btnStopCliente = document.getElementById('btn-stop-cliente');

    if (btnStartCliente) {
        btnStartCliente.addEventListener('click', startTradingCliente);
    }
    if (btnStopCliente) {
        btnStopCliente.addEventListener('click', stopTradingCliente);
    }

    // Event listeners para os botões do mestre (já existentes)
    const btnStartMestre = document.getElementById('btn-start-mestre'); // Assumindo que você adicionará um ID
    const btnStopMestre = document.getElementById('btn-stop-mestre'); // Assumindo que você adicionará um ID
    const btnSaveParamsMestre = document.getElementById('btn-save-params-mestre'); // Assumindo que você adicionará um ID
    const btnUpdateStrategyMestre = document.getElementById('btn-update-strategy-mestre'); // Assumindo que você adicionará um ID

    if (btnStartMestre) {
        btnStartMestre.addEventListener('click', startTradingMestre);
    }
    if (btnStopMestre) {
        btnStopMestre.addEventListener('click', stopTradingMestre);
    }
    if (btnSaveParamsMestre) {
        btnSaveParamsMestre.addEventListener('click', saveTradingParamsMestre);
    }
    if (btnUpdateStrategyMestre) {
        btnUpdateStrategyMestre.addEventListener('click', updateStrategyMestre);
    }
});
