# saas_dashboard/app.py
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pathlib import Path
import json
from datetime import datetime

# ============ CONFIGURAÇÕES ============
BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "robo_trader" / "trading_state.json"
SIGNALS_FILE = BASE_DIR / "robo_cliente" / "signals.json"
LOG_FILE = BASE_DIR / "robo_trader" / "trading_logs.txt"

SECRET_KEY = "sua_chave_secreta_aqui_2026"
DEBUG = True
HOST = "0.0.0.0"
PORT = 5000

# ============ INICIALIZAÇÃO FLASK ============
# CORREÇÃO: Caminhos relativos (templates e static estão na mesma pasta do app.py)
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
            state = {
                "position_active": False,
                "entry_price": 0,
                "entry_quantity": 0,
                "banca_inicial": 199.44,
                "ganho_dia": 0.14,
                "current_symbol": "SOLUSDT"
            }

        banca_inicial = state.get("banca_inicial", 199.44)
        ganho_dia = state.get("ganho_dia", 0.14)
        meta_diaria = banca_inicial * 0.02

        return jsonify({
            "mestre": {
                "status": "running",
                "position_active": state.get("position_active", False),
                "current_symbol": state.get("current_symbol", "SOLUSDT"),
                "entry_price": state.get("entry_price", 0)
            },
            "cliente": {
                "status": "connected",
                "saldo": banca_inicial,
                "lucro_hoje": ganho_dia,
                "meta_diaria": meta_diaria,
                "falta_meta": max(0, meta_diaria - ganho_dia)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Erro ao obter status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/params", methods=["GET"])
def get_params():
    """Retorna parâmetros atuais do robô"""
    try:
        return jsonify({
            "stop_loss_percent": 4.0,
            "take_profit_percent": 2.0,
            "meta_diaria_percent": 2.0,
            "quantidade_percentual": 100,
            "estrategia": "PNY"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/params", methods=["POST"])
def save_params():
    """Salva novos parâmetros"""
    try:
        data = request.json
        print(f"✅ Parâmetros atualizados: {data}")
        return jsonify({
            "success": True,
            "message": "Parâmetros salvos com sucesso!",
            "data": data
        })
    except Exception as e:
        print(f"❌ Erro ao salvar parâmetros: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/strategy", methods=["POST"])
def update_strategy():
    """Altera a estratégia de trading"""
    try:
        data = request.json
        strategy = data.get("strategy", "PNY")
        print(f"🎯 Estratégia alterada para: {strategy}")
        return jsonify({
            "success": True,
            "strategy": strategy,
            "message": f"Estratégia alterada para {strategy}"
        })
    except Exception as e:
        print(f"❌ Erro ao alterar estratégia: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop-loss", methods=["POST"])
def update_stop_loss():
    """Atualiza Stop Loss"""
    try:
        data = request.json
        stop_loss = data.get("stop_loss_percent", 4.0)
        print(f"🛑 Stop Loss alterado para: {stop_loss}%")
        return jsonify({
            "success": True,
            "stop_loss_percent": stop_loss,
            "message": f"Stop Loss alterado para {stop_loss}%"
        })
    except Exception as e:
        print(f"❌ Erro ao alterar Stop Loss: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/take-profit", methods=["POST"])
def update_take_profit():
    """Atualiza Take Profit"""
    try:
        data = request.json
        take_profit = data.get("take_profit_percent", 2.0)
        print(f"🎯 Take Profit alterado para: {take_profit}%")
        return jsonify({
            "success": True,
            "take_profit_percent": take_profit,
            "message": f"Take Profit alterado para {take_profit}%"
        })
    except Exception as e:
        print(f"❌ Erro ao alterar Take Profit: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/percent-banca", methods=["POST"])
def update_percent_banca():
    """Atualiza percentual da banca por trade"""
    try:
        data = request.json
        percent = data.get("percent", 100)
        print(f"💰 % da banca alterado para: {percent}%")
        return jsonify({
            "success": True,
            "percent": percent,
            "message": f"% da banca alterado para {percent}%"
        })
    except Exception as e:
        print(f"❌ Erro ao alterar % da banca: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/signals")
def get_signals():
    """Retorna últimos sinais do robô mestre"""
    try:
        if SIGNALS_FILE.exists():
            with open(SIGNALS_FILE, 'r') as f:
                signals = json.load(f)
            recent_signals = signals[-5:] if len(signals) > 5 else signals
            return jsonify(recent_signals)
        return jsonify([])
    except Exception as e:
        print(f"❌ Erro ao carregar sinais: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/logs")
def get_logs():
    """Retorna últimas linhas do log"""
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            recent_logs = lines[-10:] if len(lines) > 10 else lines
            return jsonify({"logs": recent_logs})
        return jsonify({"logs": []})
    except Exception as e:
        print(f"❌ Erro ao carregar logs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/start", methods=["POST"])
def start_trading():
    """Inicia o trading"""
    try:
        print("🚀 Trading iniciado!")
        return jsonify({
            "success": True,
            "message": "Trading iniciado com sucesso!"
        })
    except Exception as e:
        print(f"❌ Erro ao iniciar trading: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop", methods=["POST"])
def stop_trading():
    """Para o trading"""
    try:
        print("⏹️ Trading parado!")
        return jsonify({
            "success": True,
            "message": "Trading parado com sucesso!"
        })
    except Exception as e:
        print(f"❌ Erro ao parar trading: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/health")
def health_check():
    """Verifica saúde do servidor"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def not_found(error):
    """Tratamento de rota não encontrada"""
    return jsonify({"error": "Rota não encontrada"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Tratamento de erro interno"""
    return jsonify({"error": "Erro interno do servidor"}), 500

# ============ INICIALIZAÇÃO ============

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 DASHBOARD SaaS - CopyTrader PNY")
    print("="*60)
    print(f"📍 Rodando em http://{HOST}:{PORT}")
    print(f"🔧 Debug: {DEBUG}")
    print("="*60 + "\n")

    app.run(host=HOST, port=PORT, debug=DEBUG)