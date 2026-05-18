import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pathlib import Path
import json
from datetime import datetimeimport os
from pathlib import Path

# No main_trader.py e app.py
STATE_FILE = Path(os.getenv("STATE_FILE_PATH", Path(__file__).parent / "trading_state.json"))


# ============ CONFIGURAÇÕES DE CAMINHOS UNIFICADOS ============
BASE_DIR = Path(__file__).parent.parent
# Caminhos ajustados para os novos volumes mapeados
STATE_FILE_MESTRE = BASE_DIR / "data" / "robo_trader" / "trading_state.json" # <-- CORREÇÃO AQUI
STATE_FILE_CLIENTE = BASE_DIR / "data" / "robo_cliente" / "trading_state_cliente.json" # <-- NOVO
LATEST_SIGNAL_FILE = BASE_DIR / "data" / "robo_trader" / "latest_signal.json" # <-- NOVO
LOG_FILE_MESTRE = BASE_DIR / "data" / "logs" / "trading_logs.txt" # <-- NOVO
LOG_FILE_CLIENTE = BASE_DIR / "data" / "logs" / "trading_logs_cliente.txt" # <-- NOVO

SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "sua_chave_secreta_aqui_2026") # <-- CORREÇÃO AQUI: Ler de env
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ('true', '1', 't') # <-- CORREÇÃO AQUI: Ler de env
HOST = "0.0.0.0"
PORT = 5000

# ============ INICIALIZAÇÃO FLASK ============
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.config['SECRET_KEY'] = SECRET_KEY

# ============ API ENDPOINTS ============

@app.route("/")
def dashboard():
    """Carrega o dashboard principal"""
    return render_template("dashboard.html")

@app.route("/api/status")
def api_status():
    """Retorna status do robô mestre e cliente em tempo real"""
    try:
        # --- Status do Mestre ---
        mestre_state = {}
        if STATE_FILE_MESTRE.exists():
            with open(STATE_FILE_MESTRE, 'r') as f:
                mestre_state = json.load(f)

        # Fallbacks de segurança caso o arquivo de estado do mestre esteja inicializando vazio
        mestre_banca_inicial = float(mestre_state.get("banca_inicial", 199.44))
        mestre_ganho_dia = float(mestre_state.get("ganho_dia", 0.0))
        mestre_meta_pct = float(mestre_state.get("meta_diaria_percent", 2.0))
        mestre_meta_diaria = mestre_banca_inicial * (mestre_meta_pct / 100.0)

        # --- Status do Cliente ---
        cliente_state = {}
        if STATE_FILE_CLIENTE.exists():
            with open(STATE_FILE_CLIENTE, 'r') as f:
                cliente_state = json.load(f)

        # Fallbacks de segurança caso o arquivo de estado do cliente esteja inicializando vazio
        cliente_banca_inicial = float(cliente_state.get("banca_inicial", 199.44))
        cliente_banca_atual = float(cliente_state.get("banca_atual", cliente_banca_inicial))
        cliente_ganho_dia = float(cliente_state.get("ganho_dia", 0.0))
        cliente_meta_pct = float(cliente_state.get("meta_diaria_percent", 2.0))
        cliente_meta_diaria = cliente_banca_inicial * (cliente_meta_pct / 100.0)
        cliente_position_active = cliente_state.get("position_active", False)
        cliente_current_symbol = cliente_state.get("current_symbol", "N/A")
        cliente_entry_price = cliente_state.get("entry_price", 0.0)
        cliente_entry_quantity = cliente_state.get("entry_quantity", 0.0)
        cliente_bot_active = cliente_state.get("bot_active", False) # Novo: controle de ativação do cliente

        return jsonify({
            "mestre": {
                "status": "running",
                "bot_active": mestre_state.get("bot_active", False),
                "position_active": mestre_state.get("position_active", False),
                "current_symbol": mestre_state.get("current_symbol", "SOLUSDT"),
                "entry_price": mestre_state.get("entry_price", 0),
                "estrategia": mestre_state.get("estrategia", "PNY"),
                "saldo": mestre_banca_inicial, # Usando banca_inicial do mestre para o dashboard
                "lucro_hoje": mestre_ganho_dia,
                "meta_diaria": mestre_meta_diaria,
                "falta_meta": max(0.0, mestre_meta_diaria - mestre_ganho_dia)
            },
            "cliente": {
                "status": "connected",
                "bot_active": cliente_bot_active, # Novo: status de ativação do cliente
                "position_active": cliente_position_active,
                "current_symbol": cliente_current_symbol,
                "entry_price": cliente_entry_price,
                "entry_quantity": cliente_entry_quantity,
                "saldo": cliente_banca_atual, # Saldo atual do cliente
                "lucro_hoje": cliente_ganho_dia,
                "meta_diaria": cliente_meta_diaria,
                "falta_meta": max(0.0, cliente_meta_diaria - cliente_ganho_dia)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Erro ao obter status na API: {e}")
        return jsonify({"error": str(e)}), 500

# --- Endpoints para controle do Robô Mestre ---
@app.route("/api/start", methods=["POST"])
def start_trading_mestre():
    """Inicia o trading do Mestre de forma real gravando no estado"""
    try:
        state = {}
        if STATE_FILE_MESTRE.exists():
            with open(STATE_FILE_MESTRE, 'r') as f:
                state = json.load(f)

        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE_MESTRE, 'w') as f:
            json.dump(state, f, indent=4)

        print("🚀 Status do Robô MESTRE alterado para: ATIVO!")
        return jsonify({"success": True, "message": "Trading do Mestre iniciado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao iniciar trading do Mestre: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop", methods=["POST"])
def stop_trading_mestre():
    """Para o trading do Mestre de forma real gravando no estado"""
    try:
        state = {}
        if STATE_FILE_MESTRE.exists():
            with open(STATE_FILE_MESTRE, 'r') as f:
                state = json.load(f)

        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE_MESTRE, 'w') as f:
            json.dump(state, f, indent=4)

        print("⏹️ Status do Robô MESTRE alterado para: PARADO!")
        return jsonify({"success": True, "message": "Trading do Mestre parado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao parar trading do Mestre: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/params", methods=["GET"])
def get_params_mestre():
    """Busca parâmetros reais gravados dinamicamente no JSON do Mestre"""
    try:
        state = {}
        if STATE_FILE_MESTRE.exists():
            with open(STATE_FILE_MESTRE, 'r') as f:
                state = json.load(f)

        return jsonify({
            "stop_loss_percent": float(state.get("stop_loss_percent", 4.0)),
            "take_profit_percent": float(state.get("take_profit_percent", 2.0)),
            "meta_diaria_percent": float(state.get("meta_diaria_percent", 2.0)),
            "quantidade_percentual": float(state.get("quantidade_percentual", 100.0)),
            "estrategia": state.get("estrategia", "PNY")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/params", methods=["POST"])
def save_params_mestre():
    """Persiste novos parâmetros operacionais reais de Stop/Take enviados pelo front para o Mestre"""
    try:
        data = request.json
        state = {}
        if STATE_FILE_MESTRE.exists():
            with open(STATE_FILE_MESTRE, 'r') as f:
                state = json.load(f)

        # Faz o update seguro mantendo o histórico e injetando as novas travas do input
        if "stop_loss_percent" in data: state["stop_loss_percent"] = float(data["stop_loss_percent"])
        if "take_profit_percent" in data: state["take_profit_percent"] = float(data["take_profit_percent"])
        if "quantidade_percentual" in data: state["quantidade_percentual"] = float(data["quantidade_percentual"])
        if "meta_diaria_percent" in data: state["meta_diaria_percent"] = float(data["meta_diaria_percent"])

        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE_MESTRE, 'w') as f:
            json.dump(state, f, indent=4)

        print(f"✅ Parâmetros persistidos no arquivo de estado do robô MESTRE: {data}")
        return jsonify({"success": True, "message": "Parâmetros do Mestre salvos com sucesso!", "data": data})
    except Exception as e:
        print(f"❌ Erro ao salvar parâmetros em disco do Mestre: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/strategy", methods=["POST"])
def update_strategy_route_mestre():
    """Persiste a alteração da estratégia operacional (PNY, RSI, EMA) feita no painel para o MESTRE"""
    try:
        data = request.json
        strategy = data.get("strategy", "PNY")

        state = {}
        if STATE_FILE_MESTRE.exists():
            with open(STATE_FILE_MESTRE, 'r') as f:
                state = json.load(f)

        state["estrategia"] = strategy
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE_MESTRE, 'w') as f:
            json.dump(state, f, indent=4)

        print(f"🎯 Inteligência do Robô MESTRE alterada para o Setup: {strategy}")
        return jsonify({"success": True, "strategy": strategy, "message": f"Estratégia do Mestre alterada para {strategy}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Endpoints para controle do Robô Cliente ---
@app.route("/api/cliente/start", methods=["POST"])
def start_cliente_trading():
    """Inicia o trading do Cliente de forma real gravando no estado"""
    try:
        state = {}
        if STATE_FILE_CLIENTE.exists():
            with open(STATE_FILE_CLIENTE, 'r') as f:
                state = json.load(f)

        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE_CLIENTE, 'w') as f:
            json.dump(state, f, indent=4)

        print("🚀 Status do Robô CLIENTE alterado para: ATIVO!")
        return jsonify({"success": True, "message": "Trading do Cliente iniciado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao iniciar trading do Cliente: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/cliente/stop", methods=["POST"])
def stop_cliente_trading():
    """Para o trading do Cliente de forma real gravando no estado"""
    try:
        state = {}
        if STATE_FILE_CLIENTE.exists():
            with open(STATE_FILE_CLIENTE, 'r') as f:
                state = json.load(f)

        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE_CLIENTE, 'w') as f:
            json.dump(state, f, indent=4)

        print("⏹️ Status do Robô CLIENTE alterado para: PARADO!")
        return jsonify({"success": True, "message": "Trading do Cliente parado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao parar trading do Cliente: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/cliente/params", methods=["GET"])
def get_params_cliente():
    """Busca parâmetros reais gravados dinamicamente no JSON do Cliente"""
    try:
        state = {}
        if STATE_FILE_CLIENTE.exists():
            with open(STATE_FILE_CLIENTE, 'r') as f:
                state = json.load(f)

        return jsonify({
            "stop_loss_percent": float(state.get("stop_loss_percent", 4.0)),
            "take_profit_percent": float(state.get("take_profit_percent", 2.0)),
            "meta_diaria_percent": float(state.get("meta_diaria_percent", 2.0)),
            "quantidade_percentual": float(state.get("quantidade_percentual", 100.0)),
            "bot_active": state.get("bot_active", False)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/cliente/params", methods=["POST"])
def save_params_cliente():
    """Persiste novos parâmetros operacionais reais de Stop/Take enviados pelo front para o Cliente"""
    try:
        data = request.json
        state = {}
        if STATE_FILE_CLIENTE.exists():
            with open(STATE_FILE_CLIENTE, 'r') as f:
                state = json.load(f)

        # Faz o update seguro mantendo o histórico e injetando as novas travas do input
        if "stop_loss_percent" in data: state["stop_loss_percent"] = float(data["stop_loss_percent"])
        if "take_profit_percent" in data: state["take_profit_percent"] = float(data["take_profit_percent"])
        if "quantidade_percentual" in data: state["quantidade_percentual"] = float(data["quantidade_percentual"])
        if "meta_diaria_percent" in data: state["meta_diaria_percent"] = float(data["meta_diaria_percent"])

        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE_CLIENTE, 'w') as f:
            json.dump(state, f, indent=4)

        print(f"✅ Parâmetros persistidos no arquivo de estado do robô CLIENTE: {data}")
        return jsonify({"success": True, "message": "Parâmetros do Cliente salvos com sucesso!", "data": data})
    except Exception as e:
        print(f"❌ Erro ao salvar parâmetros em disco do Cliente: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/signals")
def get_signals():
    """Retorna os últimos sinais do MESTRE"""
    try:
        if LATEST_SIGNAL_FILE.exists():
            with open(LATEST_SIGNAL_FILE, 'r') as f:
                signal = json.load(f)
            # Retorna o último sinal como uma lista de um item para compatibilidade com o front
            return jsonify([signal])
        return jsonify([])
    except Exception as e:
        print(f"❌ Erro ao obter sinais: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/logs/mestre")
def get_logs_mestre():
    """Retorna os últimos logs do Mestre"""
    try:
        if LOG_FILE_MESTRE.exists():
            with open(LOG_FILE_MESTRE, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            return jsonify({"logs": lines[-10:] if len(lines) > 10 else lines})
        return jsonify({"logs": []})
    except Exception as e:
        print(f"❌ Erro ao obter logs do mestre: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/logs/cliente")
def get_logs_cliente():
    """Retorna os últimos logs do Cliente"""
    try:
        if LOG_FILE_CLIENTE.exists():
            with open(LOG_FILE_CLIENTE, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            return jsonify({"logs": lines[-10:] if len(lines) > 10 else lines})
        return jsonify({"logs": []})
    except Exception as e:
        print(f"❌ Erro ao obter logs do cliente: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
