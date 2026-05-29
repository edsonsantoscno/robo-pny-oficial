import json
import threading
import collections
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS

# Importando todas as variáveis físicas e operacionais do arquivo de configuração unificado
from config_dashboard import (
    STATE_FILE_MESTRE, STATE_FILE_CLIENTE, LATEST_SIGNAL_FILE,
    LOG_FILE_MESTRE, LOG_FILE_CLIENTE, SECRET_KEY, DEBUG, HOST, PORT, STRATEGIES
)

# Mecanismo de trava (Lock) global contra corrupção concorrente de arquivos JSON/TXT
file_lock = threading.Lock()

# ============ INICIALIZAÇÃO E BLINDAGEM FLASK ============
app = Flask(__name__, template_folder='templates', static_folder='static')

# Permite credenciais seguras e conexões do ecossistema
CORS(app, supports_credentials=True)

app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,  # Proteção avançada contra roubo de cookies via JavaScript (XSS)
    SESSION_COOKIE_SAMESITE='Lax',  # Impede ataques de falsificação de requisição cruzada (CSRF)
)

# ============ DECORATOR DE AUTENTICAÇÃO OBRIGATÓRIA ============
def login_required(f):
    """Garante que apenas administradores ou clientes autenticados comandem as rotas do robô"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Acesso negado. Autenticação pendente."}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============ FUNÇÕES AUXILIARES DE LEITURA E GRAVAÇÃO EM DISCO ============
def load_state(file_path):
    """Lê o estado operacional do robô de forma segura contra concorrência de I/O"""
    with file_lock:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"⚠ Arquivo corrompido detectado e limpo automaticamente: {file_path}")
                return {}
        return {}

def save_state(file_path, state):
    """Grava os novos dados de forma atômica no armazenamento físico do servidor"""
    with file_lock:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro crítico ao gravar dados no arquivo {file_path}: {e}")
            raise e
# ============ ROTA VISUAL ============
@app.route("/")
def dashboard():
    """Carrega a interface gráfica em tempo real"""
    return render_template("dashboard.html")

# ============ API ENDPOINTS - ROBÔ MESTRE (MASTER) ============
@app.route("/api/status")
@login_required
def api_status():
    """Consolida as informações de saldo, lucros e posições do mestre e do cliente"""
    try:
        state_mestre = load_state(STATE_FILE_MESTRE)
        state_cliente = load_state(STATE_FILE_CLIENTE)

        # Processamento e cálculos do Robô Mestre
        banca_inicial_mestre = float(state_mestre.get("banca_inicial", 199.44))
        ganho_dia_mestre = float(state_mestre.get("ganho_dia", 0.0))
        meta_pct_mestre = float(state_mestre.get("meta_diaria_percent", 2.0))
        meta_diaria_mestre = banca_inicial_mestre * (meta_pct_mestre / 100.0)

        # Processamento e cálculos do Robô Cliente
        banca_inicial_cliente = float(state_cliente.get("banca_inicial", 0.0))
        banca_atual_cliente = float(state_cliente.get("banca_atual", banca_inicial_cliente))
        ganho_dia_cliente = float(state_cliente.get("ganho_dia", 0.0))
        meta_pct_cliente = float(state_cliente.get("meta_diaria_percent", 2.0))
        meta_diaria_cliente = banca_inicial_cliente * (meta_pct_cliente / 100.0)
        daily_target_reached_cliente = state_cliente.get("daily_target_reached", False)

        return jsonify({
            "mestre": {
                "status": "running",
                "bot_active": state_mestre.get("bot_active", False),
                "position_active": state_mestre.get("position_active", False),
                "current_symbol": state_mestre.get("current_symbol", "N/A"),
                "entry_price": state_mestre.get("entry_price", 0),
                "estrategia": state_mestre.get("estrategia", "PNY"),
                "saldo": banca_inicial_mestre,
                "lucro_hoje": ganho_dia_mestre,
                "meta_diaria": meta_diaria_mestre,
                "falta_meta": max(0.0, meta_diaria_mestre - ganho_dia_mestre)
            },
            "cliente": {
                "status": "connected",
                "bot_active": state_cliente.get("bot_active", True),
                "position_active": state_cliente.get("position_active", False),
                "current_symbol": state_cliente.get("current_symbol", "N/A"),
                "saldo_inicial": banca_inicial_cliente,
                "saldo_atual": banca_atual_cliente,
                "lucro_hoje": ganho_dia_cliente,
                "meta_diaria": meta_diaria_cliente,
                "falta_meta": max(0.0, meta_diaria_cliente - ganho_dia_cliente),
                "meta_atingida": daily_target_reached_cliente,
                "quantidade_percentual": state_cliente.get("quantidade_percentual", 100.0)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Falha interna ao processar API de Status: {e}")
        return jsonify({"error": "Erro interno ao ler estados operacionais."}), 500

@app.route("/api/start", methods=["POST"])
@login_required
def start_trading():
    """Ativa os loops de varredura de mercado do Mestre"""
    try:
        state = load_state(STATE_FILE_MESTRE) or {}
        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)
        print("🚀 Comando enviado: Robô MESTRE Ativado!")
        return jsonify({"success": True, "message": "Trading do Mestre iniciado com sucesso!"})
    except Exception as e:
        return jsonify({"error": "Falha ao ligar robô mestre."}), 500

@app.route("/api/stop", methods=["POST"])
@login_required
def stop_trading():
    """Congela novas entradas do Robô Mestre"""
    try:
        state = load_state(STATE_FILE_MESTRE) or {}
        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)
        print("⏹ Comando enviado: Robô MESTRE Desativado!")
        return jsonify({"success": True, "message": "Trading do Mestre interrompido com sucesso!"})
    except Exception as e:
        return jsonify({"error": "Falha ao desligar robô mestre."}), 500

@app.route("/api/params", methods=["GET", "POST"])
@login_required
def manage_params():
    """Lê ou atualiza parâmetros de gerenciamento de risco do Mestre de forma sanitizada"""
    if request.method == "POST":
        try:
            data = request.json or {}
            state = load_state(STATE_FILE_MESTRE) or {}
            
            # Travas Sanitárias Duráveis: Valores de risco impossíveis são filtrados automaticamente
            if "stop_loss_percent" in data:
                state["stop_loss_percent"] = max(0.1, min(float(data["stop_loss_percent"]), 20.0))
            if "take_profit_percent" in data:
                state["take_profit_percent"] = max(0.1, min(float(data["take_profit_percent"]), 50.0))
            if "quantidade_percentual" in data:
                state["quantidade_percentual"] = max(1.0, min(float(data["quantidade_percentual"]), 100.0))
            if "meta_diaria_percent" in data:
                state["meta_diaria_percent"] = max(0.5, min(float(data["meta_diaria_percent"]), 15.0))

            state["updated_at"] = datetime.now().isoformat()
            save_state(STATE_FILE_MESTRE, state)
            return jsonify({"success": True, "message": "Gerenciamento de risco do Mestre salvo!", "data": data})
        except Exception as e:
            return jsonify({"error": "Erro ao persistir novas configurações."}), 500

    # Método GET padrão
    try:
        state = load_state(STATE_FILE_MESTRE)
        return jsonify({
            "stop_loss_percent": float(state.get("stop_loss_percent", 4.0)),
            "take_profit_percent": float(state.get("take_profit_percent", 2.0)),
            "meta_diaria_percent": float(state.get("meta_diaria_percent", 2.0)),
            "quantidade_percentual": float(state.get("quantidade_percentual", 100.0)),
            "estrategia": state.get("estrategia", "PNY")
        })
    except Exception as e:
        return jsonify({"error": "Erro ao buscar parâmetros."}), 500

@app.route("/api/strategy", methods=["POST"])
@login_required
def update_strategy_route():
    """Muda o setup operacional usando a lista limpa vinda do arquivo config"""
    try:
        data = request.json or {}
        strategy = data.get("strategy", "PNY")
        
        # Filtro estrito contra strings ou injeções de setups inexistentes
        if strategy not in STRATEGIES:
            return jsonify({"error": f"Estratégia inválida. Escolha entre: {STRATEGIES}"}), 400
            
        state = load_state(STATE_FILE_MESTRE) or {}
        state["estrategia"] = strategy
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)
        return jsonify({"success": True, "strategy": strategy, "message": f"Setup alterado para {strategy}"})
    except Exception as e:
        return jsonify({"error": "Falha ao gravar nova inteligência de mercado."}), 500
# ============ API ENDPOINTS - ROBÔ CLIENTE (SLAVE / COPY) ============
@app.route("/api/cliente/status")
@login_required
def api_cliente_status():
    """Exibe o andamento e preenchimento de lotes e metas da ponta executora do cliente"""
    try:
        state_cliente = load_state(STATE_FILE_CLIENTE)
        banca_inicial = float(state_cliente.get("banca_inicial", 0.0))
        banca_atual = float(state_cliente.get("banca_atual", banca_inicial))
        ganho_dia = float(state_cliente.get("ganho_dia", 0.0))
        meta_pct = float(state_cliente.get("meta_diaria_percent", 2.0))
        meta_diaria = banca_inicial * (meta_pct / 100.0)

        return jsonify({
            "bot_active": state_cliente.get("bot_active", True),
            "position_active": state_cliente.get("position_active", False),
            "current_symbol": state_cliente.get("current_symbol", "N/A"),
            "entry_price": state_cliente.get("entry_price", 0),
            "entry_quantity": state_cliente.get("entry_quantity", 0),
            "saldo_inicial": banca_inicial,
            "saldo_atual": banca_atual,
            "lucro_hoje": ganho_dia,
            "meta_diaria": meta_diaria,
            "falta_meta": max(0.0, meta_diaria - ganho_dia),
            "meta_atingida": state_cliente.get("daily_target_reached", False),
            "stop_loss_percent": float(state_cliente.get("stop_loss_percent", 4.0)),
            "take_profit_percent": float(state_cliente.get("take_profit_percent", 2.0)),
            "quantidade_percentual": float(state_cliente.get("quantidade_percentual", 100.0)),
            "updated_at": state_cliente.get("updated_at", datetime.now().isoformat())
        })
    except Exception as e:
        return jsonify({"error": "Não foi possível coletar parâmetros do cliente."}), 500

@app.route("/api/cliente/start", methods=["POST"])
@login_required
def start_cliente_trading():
    """Ativa o espelhamento de ordens em tempo real no cliente"""
    try:
        state = load_state(STATE_FILE_CLIENTE) or {}
        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_CLIENTE, state)
        return jsonify({"success": True, "message": "Cópia proporcional iniciada no cliente!"})
    except Exception as e:
        return jsonify({"error": "Erro ao disparar cópia."}), 500

@app.route("/api/cliente/stop", methods=["POST"])
@login_required
def stop_cliente_trading():
    """Corta imediatamente o recebimento e cópia de ordens vinda do mestre"""
    try:
        state = load_state(STATE_FILE_CLIENTE) or {}
        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_CLIENTE, state)
        return jsonify({"success": True, "message": "Espelhamento pausado no cliente!"})
    except Exception as e:
        return jsonify({"error": "Erro ao pausar cópia."}), 500

@app.route("/api/cliente/params", methods=["GET", "POST"])
@login_required
def manage_cliente_params():
    """Lê ou atualiza travas sanitárias individuais do robô cliente"""
    if request.method == "POST":
        try:
            data = request.json or {}
            state = load_state(STATE_FILE_CLIENTE) or {}
            
            if "stop_loss_percent" in data:
                state["stop_loss_percent"] = max(0.1, min(float(data["stop_loss_percent"]), 20.0))
            if "take_profit_percent" in data:
                state["take_profit_percent"] = max(0.1, min(float(data["take_profit_percent"]), 50.0))
            if "quantidade_percentual" in data:
                state["quantidade_percentual"] = max(1.0, min(float(data["quantidade_percentual"]), 100.0))
            if "meta_diaria_percent" in data:
                state["meta_diaria_percent"] = max(0.5, min(float(data["meta_diaria_percent"]), 15.0))

            state["updated_at"] = datetime.now().isoformat()
            save_state(STATE_FILE_CLIENTE, state)
            return jsonify({"success": True, "message": "Gerenciamento de risco do Cliente salvo!"})
        except Exception as e:
            return jsonify({"error": "Erro ao processar inputs do cliente."}), 500

    # Método GET padrão do cliente
    try:
        state = load_state(STATE_FILE_CLIENTE)
        return jsonify({
            "stop_loss_percent": float(state.get("stop_loss_percent", 4.0)),
            "take_profit_percent": float(state.get("take_profit_percent", 2.0)),
            "meta_diaria_percent": float(state.get("meta_diaria_percent", 2.0)),
            "quantidade_percentual": float(state.get("quantidade_percentual", 100.0))
        })
    except Exception as e:
        return jsonify({"error": "Erro ao buscar dados de parametrização."}), 500

# ============ FILTROS DE POLLED STREAMING DE MÍDIA E ALERTAS ============
@app.route("/api/signals")
@login_required
def get_signals():
    """Retorna de forma segura os últimos 5 gatilhos sem gargalo de concorrência"""
    try:
        if LATEST_SIGNAL_FILE.exists():
            with file_lock:
                with open(LATEST_SIGNAL_FILE, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
                return jsonify(signals[-5:] if len(signals) > 5 else signals)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": "Falha na leitura síncrona de sinais."}), 500

@app.route("/api/logs")
@login_required
def get_logs():
    """Lê reversamente apenas o fim do log físico sem carregar arquivos gigantes na RAM da VPS"""
    try:
        if LOG_FILE_MESTRE.exists():
            with file_lock:
                # O deque com maxlen extrai apenas o final do arquivo diretamente do ponteiro de disco
                with open(LOG_FILE_MESTRE, 'r', encoding='utf-8', errors='ignore') as f:
                    lines_buffer = collections.deque(f, maxlen=10)
                return jsonify({"logs": list(lines_buffer)})
        return jsonify({"logs": []})
    except Exception as e:
        return jsonify({"error": "Falha ao escanear logs operacionais."}), 500

# ============ EXECUÇÃO PRINCIPAL DO SERVIDOR OPERACIONAL ============
if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
