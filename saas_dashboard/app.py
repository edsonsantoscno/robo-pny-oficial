import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pathlib import Path
import json
from datetime import datetime

# ============ CONFIGURAÇÕES DE CAMINHOS UNIFICADOS ============
BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "robo_trader" / "trading_state.json"
SIGNALS_FILE = BASE_DIR / "robo_cliente" / "signals.json"
LOG_FILE = BASE_DIR / "robo_trader" / "trading_logs.txt"

SECRET_KEY = "sua_chave_secreta_aqui_2026"
DEBUG = True
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
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
        else:
            state = {}

        # Fallbacks de segurança caso o arquivo de estado esteja inicializando vazio
        banca_inicial = float(state.get("banca_inicial", 199.44))
        ganho_dia = float(state.get("ganho_dia", 0.14))
        
        # Recupera as configurações dinâmicas modificadas pelo painel ou config padrão
        meta_pct = float(state.get("meta_diaria_percent", 2.0))
        meta_diaria = banca_inicial * (meta_pct / 100.0)

        return jsonify({
            "mestre": {
                "status": "running",
                "bot_active": state.get("bot_active", False),
                "position_active": state.get("position_active", False),
                "current_symbol": state.get("current_symbol", "SOLUSDT"),
                "entry_price": state.get("entry_price", 0),
                "estrategia": state.get("estrategia", "PNY")
            },
            "cliente": {
                "status": "connected",
                "saldo": banca_inicial,
                "lucro_hoje": ganho_dia,
                "meta_diaria": meta_diaria,
                "falta_meta": max(0.0, meta_diaria - ganho_dia)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Erro ao obter status na API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/start", methods=["POST"])
def start_trading():
    """Inicia o trading de forma real gravando no estado"""
    try:
        state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
        
        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)

        print("🚀 Status do Robô alterado para: ATIVO!")
        return jsonify({"success": True, "message": "Trading iniciado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao iniciar trading: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop", methods=["POST"])
def stop_trading():
    """Para o trading de forma real gravando no estado"""
    try:
        state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
        
        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)

        print("⏹️ Status do Robô alterado para: PARADO!")
        return jsonify({"success": True, "message": "Trading parado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao parar trading: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/params", methods=["GET"])
def get_params():
    """Busca parâmetros reais gravados dinamicamente no JSON"""
    try:
        state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
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
def save_params():
    """Persiste novos parâmetros operacionais reais de Stop/Take enviados pelo front"""
    try:
        data = request.json
        state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
        
        # Faz o update seguro mantendo o histórico e injetando as novas travas do input
        if "stop_loss_percent" in data: state["stop_loss_percent"] = float(data["stop_loss_percent"])
        if "take_profit_percent" in data: state["take_profit_percent"] = float(data["take_profit_percent"])
        if "quantidade_percentual" in data: state["quantidade_percentual"] = float(data["quantidade_percentual"])
        if "meta_diaria_percent" in data: state["meta_diaria_percent"] = float(data["meta_diaria_percent"])
        
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)

        print(f"✅ Parâmetros persistidos no arquivo de estado do robô: {data}")
        return jsonify({"success": True, "message": "Parâmetros salvos com sucesso!", "data": data})
    except Exception as e:
        print(f"❌ Erro ao salvar parâmetros em disco: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/strategy", methods=["POST"])
def update_strategy_route():
    """Persiste a alteração da estratégia operacional (PNY, RSI, EMA) feita no painel"""
    try:
        data = request.json
        strategy = data.get("strategy", "PNY")
        
        state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                
        state["estrategia"] = strategy
        state["updated_at"] = datetime.now().isoformat()

        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)

        print(f"🎯 Inteligência do Robô alterada para o Setup: {strategy}")
        return jsonify({"success": True, "strategy": strategy, "message": f"Estratégia alterada para {strategy}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/signals")
def get_signals():
    try:
        if SIGNALS_FILE.exists():
            with open(SIGNALS_FILE, 'r') as f:
                signals = json.load(f)
            return jsonify(signals[-5:] if len(signals) > 5 else signals)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/logs")
def get_logs():
    try:
        if LOG_FILE.exists():
            # errors='ignore' blinda a leitura contra falhas de quebras de codificação da VPS
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            return jsonify({"logs": lines[-10:] if len(lines) > 10 else lines})
        return jsonify({"logs": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
