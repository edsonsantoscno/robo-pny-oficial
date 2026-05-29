console.log('✅ Motor JavaScript (app.js) Iniciado com Sucesso!');

// Definição dos loops automáticos temporizados
setInterval(sincronizarStatusGeral, 5000);
sincronizarStatusGeral();

// Execução primária ao carregar a página
document.addEventListener('DOMContentLoaded', () => {
    carregarParametrosIniciaisMestre();
    vincularEventosBotoes();
});

// ========== ATUALIZAR STATUS DO PAINEL EM TEMPO REAL ==========
async function sincronizarStatusGeral() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error(`HTTP Erro! Código: ${response.status}`);
        const data = await response.json();

        // 1. ATUALIZAÇÃO DOS CARDS DO ROBÔ MESTRE (MASTER)
        if (data.mestre) {
            const mSaldo = parseFloat(data.mestre.saldo) || 0.0;
            const mLucro = parseFloat(data.mestre.lucro_hoje) || 0.0;
            const mMeta = parseFloat(data.mestre.meta_diaria) || 0.0;
            const mFalta = parseFloat(data.mestre.falta_meta) || 0.0;

            if (document.getElementById('saldo-mestre')) {
                document.getElementById('saldo-mestre').textContent = `$${mSaldo.toFixed(2)}`;
            }
            if (document.getElementById('lucro-mestre')) {
                document.getElementById('lucro-mestre').textContent = `${mLucro >= 0 ? '+' : ''}$${mLucro.toFixed(2)}`;
            }
            if (document.getElementById('meta-mestre')) {
                document.getElementById('meta-mestre').textContent = `$${mMeta.toFixed(2)}`;
            }
            
            const txtFaltaMestre = document.getElementById('falta-meta-mestre');
            if (txtFaltaMestre) {
                txtFaltaMestre.textContent = mFalta > 0 ? `Falta: $${mFalta.toFixed(2)}` : "🎯 Meta Batida!";
            }

            // Sincronização visual das badges de atividade do Master
            const indMestre = document.getElementById('status-indicator-mestre');
            const txtMestre = document.getElementById('status-text-mestre');
            const parMestre = document.getElementById('posicao-mestre');

            if (parMestre) parMestre.textContent = `Par Ativo: ${data.mestre.current_symbol || 'N/A'}`;

            if (indMestre && txtMestre) {
                if (data.mestre.bot_active) {
                    indMestre.className = "status-indicator status-running me-2";
                    txtMestre.textContent = "OPERANDO 24/7";
                    txtMestre.className = "text-success small fw-bold text-uppercase";
                } else {
                    indMestre.className = "status-indicator status-stopped me-2";
                    txtMestre.textContent = "PAUSADO";
                    txtMestre.className = "text-danger small fw-bold text-uppercase";
                }
            }
        }
        
        // Chamada encadeada para popular os dados do cliente e os consoles
        processarStatusCliente(data);
        atualizarListasSuporte();

    } catch (error) {
        console.error('❌ Erro de sincronização na rota de status:', error);
    }
}
// ========== PROCESSAR E EXIBIR STATUS DO CLIENTE ==========
function processarStatusCliente(data) {
    if (!data || !data.cliente) return;

    const cSaldoInicial = parseFloat(data.cliente.saldo_inicial) || 0.0;
    const cSaldoAtual = parseFloat(data.cliente.saldo_atual) || 0.0;
    const cLucro = parseFloat(data.cliente.lucro_hoje) || 0.0;
    const cPercent = parseFloat(data.cliente.quantidade_percentual) || 100.0;

    if (document.getElementById('saldo-cliente')) {
        document.getElementById('saldo-cliente').textContent = `$${cSaldoAtual.toFixed(2)}`;
    }
    if (document.getElementById('saldo-inicial-cliente')) {
        document.getElementById('saldo-inicial-cliente').textContent = `Inicial: $${cSaldoInicial.toFixed(2)}`;
    }
    if (document.getElementById('lucro-cliente')) {
        document.getElementById('lucro-cliente').textContent = `${cLucro >= 0 ? '+' : ''}$${cLucro.toFixed(2)}`;
    }
    if (document.getElementById('qtd-percentual-cliente')) {
        document.getElementById('qtd-percentual-cliente').textContent = `${cPercent.toFixed(1)}%`;
    }
    if (document.getElementById('posicao-cliente')) {
        document.getElementById('posicao-cliente').textContent = `Copiando: ${data.cliente.current_symbol || 'N/A'}`;
    }
    if (document.getElementById('meta-atingida-cliente')) {
        document.getElementById('meta-atingida-cliente').textContent = data.cliente.meta_atingida ? "🎯 Meta Diária Batida!" : "Buscando meta diária...";
    }

    // Gerenciamento visual das badges de status do Cliente
    const indCliente = document.getElementById('status-indicator-cliente');
    const txtCliente = document.getElementById('status-text-cliente');
    if (indCliente && txtCliente) {
        if (data.cliente.bot_active) {
            indCliente.className = "status-indicator status-running me-2";
            txtCliente.textContent = "SINCRONIZADO";
            txtCliente.className = "text-success small fw-bold text-uppercase";
        } else {
            indCliente.className = "status-indicator status-stopped me-2";
            txtCliente.textContent = "CÓPIA DESATIVADA";
            txtCliente.className = "text-danger small fw-bold text-uppercase";
        }
    }
}

// ========== CARREGAR PARAMETROS SALVOS NO BANCO (GET) ==========
async function carregarParametrosIniciaisMestre() {
    try {
        const response = await fetch('/api/params');
        if (!response.ok) return;
        const data = await response.json();

        if (document.getElementById('strategy')) document.getElementById('strategy').value = data.estrategia || "PNY";
        if (document.getElementById('stop-loss')) document.getElementById('stop-loss').value = data.stop_loss_percent || 4.0;
        if (document.getElementById('take-profit')) document.getElementById('take-profit').value = data.take_profit_percent || 2.0;
        if (document.getElementById('meta-mestre-input')) document.getElementById('meta-mestre-input').value = data.meta_diaria_percent || 2.0;
        
        // Se estiver no dashboard do cliente, popula o lote
        if (document.getElementById('quantidade-percentual')) document.getElementById('quantidade-percentual').value = data.quantidade_percentual || 100;
    } catch (e) {
        console.error("Erro ao pré-carregar parâmetros:", e);
    }
}

// ========== ATUALIZAÇÃO DE PARÂMETROS OPERACIONAIS (POST) ==========
async function updateMestreParams() {
    const body = {
        strategy: document.getElementById('strategy').value,
        stop_loss_percent: document.getElementById('stop-loss').value,
        take_profit_percent: document.getElementById('take-profit').value,
        meta_diaria_percent: document.getElementById('meta-mestre-input').value
    };
    try {
        const res = await fetch('/api/params', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) showNotification("⚙️ Configurações do Master salvas com sucesso!", "success");
    } catch (err) {
        showNotification("❌ Erro de conexão ao salvar parâmetros", "error");
    }
}

async function updateClienteParams() {
    const body = {
        quantidade_percentual: document.getElementById('quantidade-percentual').value,
        stop_loss_percent: document.getElementById('stop-loss-cliente').value,
        take_profit_percent: document.getElementById('take-profit-cliente').value
    };
    try {
        const res = await fetch('/api/cliente/params', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) showNotification("⚙️ Gerenciamento do Cliente aplicado!", "success");
    } catch (err) {
        showNotification("❌ Erro de conexão ao salvar riscos do cliente", "error");
    }
}
// ========== COMANDOS DE LIGA / DESLIGA (MESTRE E CLIENTE) ==========
async function startMestre() {
    try {
        await fetch('/api/start', { method: 'POST' });
        showNotification("🚀 Robô MASTER Ativado com sucesso!", "success");
        sincronizarStatusGeral();
    } catch (e) { showNotification("❌ Falha ao ligar Master", "error"); }
}

async function stopMestre() {
    try {
        await fetch('/api/stop', { method: 'POST' });
        showNotification("⏹ Robô MASTER colocado em espera.", "warning");
        sincronizarStatusGeral();
    } catch (e) { showNotification("❌ Falha ao pausar Master", "error"); }
}

async function startCliente() {
    try {
        await fetch('/api/cliente/start', { method: 'POST' });
        showNotification("🚀 Replicação do CLIENTE Ativada!", "success");
        sincronizarStatusGeral();
    } catch (e) { showNotification("❌ Falha ao ligar Cliente", "error"); }
}

async function stopCliente() {
    try {
        await fetch('/api/cliente/stop', { method: 'POST' });
        showNotification("⏹ Sincronização do CLIENTE Interrompida.", "warning");
        sincronizarStatusGeral();
    } catch (e) { showNotification("❌ Falha ao pausar Cliente", "error"); }
}

// ========== ATUALIZAR LISTAS DE SUPORTE (SINAIS E LOGS DOS TERMINAIS) ==========
async function atualizarListasSuporte() {
    // 1. Renderização de Sinais do Mestre
    try {
        const resSignals = await fetch('/api/signals');
        const signals = await resSignals.json();
        const boxSignals = document.getElementById('signals-list-cliente');
        
        if (boxSignals && Array.isArray(signals)) {
            if (signals.length === 0) {
                boxSignals.innerHTML = '<div class="text-muted">> Nenhum sinal emitido no ciclo atual...</div>';
            } else {
                boxSignals.innerHTML = signals.map(sig => `
                    <div>[${sig.timestamp || 'INFO'}] Ordem detectada: ${sig.type || 'TRADE'} | Ativo: ${sig.symbol} @ $${parseFloat(sig.price || 0).toFixed(4)}</div>
                `).join('');
            }
        }
    } catch (err) { console.log("Erro ao processar lista de sinais."); }

    // 2. Renderização de Logs do Terminal (Mestre + Cliente)
    try {
        const resLogs = await fetch('/api/logs');
        const dataLogs = await resLogs.json();
        const boxLogs = document.getElementById('logs-list-cliente');

        if (boxLogs && dataLogs && Array.isArray(dataLogs.logs)) {
            if (dataLogs.logs.length === 0) {
                boxLogs.innerHTML = '<div class="text-muted">> Escutando terminal de eventos interno...</div>';
            } else {
                boxLogs.innerHTML = dataLogs.logs.map(log => `<div>${log.trim()}</div>`).join('');
                boxLogs.scrollTop = boxLogs.scrollHeight; // Auto-scroll para o final
            }
        }
    } catch (err) { console.log("Erro ao atualizar terminal de logs."); }
}

// ========== NOTIFICAÇÕES FLUIDAS (TOASTS) ==========
function showNotification(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `notification ${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle'} me-2"></i>${message}`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ========== VINCULAR BOTÕES AOS EVENTOS DOM ==========
function vinculareventosBotoes() {
    const bStartM = document.getElementById('btn-start-mestre');
    const bStopM = document.getElementById('btn-stop-mestre');
    const bStartC = document.getElementById('btn-start-cliente');
    const bStopC = document.getElementById('btn-stop-cliente');

    if (bStartM) bStartM.onclick = startMestre;
    if (bStopM) bStopM.onclick = stopMestre;
    if (bStartC) bStartC.onclick = startCliente;
    if (bStopC) bStopC.onclick = stopCliente;
}

// ========== GRÁFICOS DO CHART.JS (CONSTRUÇÃO PADRÃO) ==========
const chartPerf = document.getElementById('performanceChart');
if (chartPerf) {
    new Chart(chartPerf.getContext('2d'), {
        type: 'line',
        data: {
            labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
            datasets: [{ label: 'P&L Acumulado ($)', data: [0, 0.5, 1.2, 0.8, 1.9, 2.4], borderColor: '#198754', tension: 0.3, fill: true, backgroundColor: 'rgba(25, 135, 84, 0.05)' }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

const chartWin = document.getElementById('winRateChart');
if (chartWin) {
    new Chart(chartWin.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Vitórias', 'Derrotas'],
            datasets: [{ data: [18, 6], backgroundColor: ['#198754', '#dc3545'] }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}
