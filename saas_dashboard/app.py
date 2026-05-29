import os
import json
import threading
import collections
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS

# ============ CONFIGURAÇÕES DE CAMINHOS UNIFICADOS ============
BASE_DIR = Path(__file__).parent.parent
STATE_FILE_MESTRE = BASE_DIR / "robo_trader" / "trading_state.json"
STATE_FILE_CLIENTE = BASE_DIR / "robo_cliente" / "trading_state_cliente.json"
SIGNALS_FILE = BASE_DIR / "robo_cliente" / "signals.json"
LOG_FILE = BASE_DIR / "robo_trader" / "trading_logs.txt"

# ============ SEGURANÇA E PRODUÇÃO (VPS HOSTINGER) ============
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "prod_strong_key_pny_2026_secure_hash")
DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
HOST = "0.0.0.0"
PORT = int(os.environ.get("FLASK_PORT", 5000))

# Mecanismo de trava (Lock) contra concorrência de arquivos
file_lock = threading.Lock()

# ============ INICIALIZAÇÃO E BLINDAGEM FLASK ============
app = Flask(__name__, template_folder='templates', static_folder='static')

# Restringe o CORS apenas para o domínio seguro em produção (se definido)
CORS(app, supports_credentials=True)

app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,  # Impede roubo de sessão via JavaScript malicioso (XSS)
    SESSION_COOKIE_SAMESITE='Lax',  # Proteção contra ataques CSRF
)

# ============ DECORATOR DE AUTENTICAÇÃO OBRIGATÓRIA ============
def login_required(f):
    """Garante que apenas requisições autenticadas acessem os endpoints do robô"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Acesso negado. Autenticação pendente."}), 401
        return f(*args, **kwargs)
    return decorated_function
# ============ FUNÇÕES AUXILIARES COM TRAVA DE SEGURANÇA ============
def load_state(file_path):
    """Lê o estado do arquivo JSON de forma segura contra concorrência"""
    with file_lock:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"⚠ Arquivo corrompido detectado e ignorado: {file_path}")
                return {}
        return {}
def save_state(file_path, state):
    """Grava o estado no arquivo JSON de forma atômica e segura"""
    with file_lock:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro crítico ao gravar em {file_path}: {e}")
            raise e
# ============ ROTA VISUAL ============
@app.route("/")
def dashboard():
    """Carrega o dashboard principal"""
    return render_template("dashboard.html")

# ============ API ENDPOINTS - ROBÔ MESTRE ============
@app.route("/api/status")
@login_required
def api_status():
    """Retorna status do robô mestre e cliente em tempo real"""
    try:
        state_mestre = load_state(STATE_FILE_MESTRE)
        state_cliente = load_state(STATE_FILE_CLIENTE)

        # Fallbacks de segurança para o Mestre
        banca_inicial_mestre = float(state_mestre.get("banca_inicial", 199.44))
        ganho_dia_mestre = float(state_mestre.get("ganho_dia", 0.0))
        meta_pct_mestre = float(state_mestre.get("meta_diaria_percent", 2.0))
        meta_diaria_mestre = banca_inicial_mestre * (meta_pct_mestre / 100.0)

        # Fallbacks de segurança para o Cliente
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
        print(f"❌ Erro ao obter status na API: {e}")
        return jsonify({"error": "Erro interno do servidor ao ler status."}), 500

@app.route("/api/start", methods=["POST"])
@login_required
def start_trading():
    """Inicia o trading do robô MESTRE gravando no estado"""
    try:
        state = load_state(STATE_FILE_MESTRE) or {}
        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)
        print("🚀 Status do Robô MESTRE alterado para: ATIVO!")
        return jsonify({"success": True, "message": "Trading do Mestre iniciado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao iniciar trading do Mestre: {e}")
        return jsonify({"error": "Falha ao iniciar trading do mestre."}), 500

@app.route("/api/stop", methods=["POST"])
@login_required
def stop_trading():
    """Para o trading do robô MESTRE gravando no estado"""
    try:
        state = load_state(STATE_FILE_MESTRE) or {}
        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)
        print("⏹ Status do Robô MESTRE alterado para: PARADO!")
        return jsonify({"success": True, "message": "Trading do Mestre parado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao parar trading do Mestre: {e}")
        return jsonify({"error": "Falha ao parar trading do mestre."}), 500

@app.route("/api/params", methods=["GET"])
@login_required
def get_params():
    """Busca parâmetros reais gravados dinamicamente no JSON do MESTRE"""
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
        return jsonify({"error": "Falha ao obter parâmetros."}), 500

@app.route("/api/params", methods=["POST"])
@login_required
def save_params():
    """Persiste e valida parâmetros operacionais de Stop/Take enviados pelo front para o MESTRE"""
    try:
        data = request.json or {}
        state = load_state(STATE_FILE_MESTRE) or {} 
    # Validação Sanitária das Entradas (Garantia de que valores absurdos não travarão a conta)
        if "stop_loss_percent" in data:
            val = float(data["stop_loss_percent"])
            state["stop_loss_percent"] = max(0.1, min(val, 20.0))  # Trava entre 0.1% e 20%           
        if "take_profit_percent" in data:
            val = float(data["take_profit_percent"])
            state["take_profit_percent"] = max(0.1, min(val, 50.0))  # Trava entre 0.1% e 50%    
        if "quantidade_percentual" in data:
            val = float(data["quantidade_percentual"])
            state["quantidade_percentual"] = max(1.0, min(val, 100.0))  # Trava entre 1% e 100%
        if "meta_diaria_percent" in data:
            val = float(data["meta_diaria_percent"])
            state["meta_diaria_percent"] = max(0.5, min(val, 15.0))  # Trava entre 0.5% e 15%

        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)
        print(f"✅ Parâmetros validados e salvos no robô MESTRE: {state}")
        return jsonify({"success": True, "message": "Parâmetros do Mestre salvos com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao salvar parâmetros do Mestre em disco: {e}")
        return jsonify({"error": "Falha ao salvar parâmetros."}), 500
@app.route("/api/strategy", methods=["POST"])
@login_required
def update_strategy_route():
    """Persiste a alteração da estratégia operacional (PNY, RSI, EMA) feita no painel para o MESTRE"""
    try:
        data = request.json or {}
        strategy = data.get("strategy", "PNY")
        
        # Filtro estrito de estratégias válidas
        if strategy not in ["PNY", "RSI", "EMA_ONLY", "EMA_SCALP"]:
            return jsonify({"error": "Estratégia inválida."}), 400
            
        state = load_state(STATE_FILE_MESTRE) or {}
        state["estrategia"] = strategy
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)
        print(f"🎯 Inteligência do Robô MESTRE alterada para o Setup: {strategy}")
        return jsonify({"success": True, "strategy": strategy, "message": f"Estratégia alterada para {strategy}"})
    except Exception as e:
        return jsonify({"error": "Falha ao alterar estratégia."}), 500
# ============ API ENDPOINTS - ROBÔ CLIENTE ============
@app.route("/api/cliente/status")
@login_required
def api_cliente_status():
    """Retorna o status detalhado do robô CLIENTE em tempo real"""
    try:
        state_cliente = load_state(STATE_FILE_CLIENTE)
        banca_inicial = float(state_cliente.get("banca_inicial", 0.0))
        banca_atual = float(state_cliente.get("banca_atual", banca_inicial))
        ganho_dia = float(state_cliente.get("ganho_dia", 0.0))
        meta_pct = float(state_cliente.get("meta_diaria_percent", 2.0))
        meta_diaria = banca_inicial * (meta_pct / 100.0)
        daily_target_reached = state_cliente.get("daily_target_reached", False)

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
            "meta_atingida": daily_target_reached,
            "stop_loss_percent": float(state_cliente.get("stop_loss_percent", 4.0)),
            "take_profit_percent": float(state_cliente.get("take_profit_percent", 2.0)),
            "quantidade_percentual": float(state_cliente.get("quantidade_percentual", 100.0)),
            "last_reset_date": state_cliente.get("last_reset_date", str(datetime.now().date())),
            "updated_at": state_cliente.get("updated_at", datetime.now().isoformat())
        })
    except Exception as e:
        print(f"❌ Erro ao obter status do CLIENTE na API: {e}")
        return jsonify({"error": "Erro ao carregar status do cliente."}), 500

@app.route("/api/cliente/start", methods=["POST"])
@login_required
def start_cliente_trading():
    """Ativa a cópia no robô CLIENTE"""
    try:
        state = load_state(STATE_FILE_CLIENTE) or {}
        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_CLIENTE, state)
        print("🚀 Status do Robô CLIENTE alterado para: ATIVO!")
        return jsonify({"success": True, "message": "Cópia do Cliente iniciada com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao iniciar cópia do Cliente: {e}")
        return jsonify({"error": "Falha ao iniciar robô cliente."}), 500

@app.route("/api/cliente/stop", methods=["POST"])
@login_required
def stop_cliente_trading():
    """Desativa a cópia no robô CLIENTE"""
    try:
        state = load_state(STATE_FILE_CLIENTE) or {}
        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_CLIENTE, state)
        print("⏹ Status do Robô CLIENTE alterado para: PARADO!")
        return jsonify({"success": True, "message": "Cópia do Cliente parada com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao parar cópia do Cliente: {e}")
        return jsonify({"error": "Falha ao parar robô cliente."}), 500

@app.route("/api/cliente/params", methods=["GET"])
@login_required
def get_cliente_params():
    """Busca parâmetros reais gravados dinamicamente no JSON do CLIENTE"""
    try:
        state = load_state(STATE_FILE_CLIENTE)
        return jsonify({
            "stop_loss_percent": float(state.get("stop_loss_percent", 4.0)),
            "take_profit_percent": float(state.get("take_profit_percent", 2.0)),
            "meta_diaria_percent": float(state.get("meta_diaria_percent", 2.0)),
            "quantidade_percentual": float(state.get("quantidade_percentual", 100.0))
        })
    except Exception as e:
        return jsonify({"error": "Erro ao obter parâmetros do cliente."}), 500

@app.route("/api/cliente/params", methods=["POST"])
@login_required
def save_cliente_params():
    """Persiste e valida novos parâmetros de gerenciamento de risco salvos para o CLIENTE"""
    try:
        data = request.json or {}
        state = load_state(STATE_FILE_CLIENTE) or {}
        # Validação Sanitária das Entradas do Cliente
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
        print(f"✅ Parâmetros validados e salvos no robô CLIENTE: {state}")
        return jsonify({"success": True, "message": "Parâmetros do Cliente salvos com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao salvar parâmetros do Cliente em disco: { e}")
        return jsonify({"error": "Falha ao salvar parâmetros do cliente."}), 500
# ============ STREAMING DE LOGS E SINAIS DE ALTA PERFORMANCE ============
@app.route("/api/signals")
@login_required
def get_signals():
    """Busca os últimos 5 sinais emitidos sem estresse de I/O"""
    try:
        if SIGNALS_FILE.exists():
            with file_lock:
                with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
                return jsonify(signals[-5:] if len(signals) > 5 else signals)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": "Erro ao ler sinais."}), 500

@app.route("/api/logs")
@login_required
def get_logs():
    """Lê eficientemente apenas o final do arquivo de log sem comprometer a RAM da VPS"""
    try:
        if LOG_FILE.exists():
            with file_lock:
                # Utiliza buffer reverso para ler apenas as últimas 10 linhas físicas do disco
                with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                    lines_buffer = collections.deque(f, maxlen=10)
                return jsonify({"logs": list(lines_buffer)})
        return jsonify({"logs": []})
    except Exception as e:
        return jsonify({"error": "Erro ao ler logs."}), 500

# ============ CONEXÃO DE ENTRADA PRINCIPAL ============
if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
