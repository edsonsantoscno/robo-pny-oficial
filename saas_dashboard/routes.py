import os
import json
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis do arquivo .env
load_dotenv()

# ============ INTEGRAÇÃO SUPABASE E ARQUIVOS ============
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

BASE_DIR = Path(__file__).parent.parent
STATE_FILE_MESTRE = BASE_DIR / "robo_trader" / "trading_state.json"
STATE_FILE_CLIENTE = BASE_DIR / "robo_cliente" / "trading_state_cliente.json"

# ============ SEGURANÇA E CONCORRÊNCIA ============
file_lock = threading.Lock() # Corrige falha de corrupção de arquivos
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "dev_key")
CORS(app)

# ============ FUNÇÕES AUXILIARES SEGURAS ============
def load_state(file_path):
    with file_lock:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}
        return {}

def save_state(file_path, state):
    with file_lock:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(state, f, indent=4)

# ============ AUTENTICAÇÃO (SUPABASE) ============
@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    if request.method == "POST":
        try:
            auth = supabase.auth.sign_in_with_password({"email": request.form.get("email"), "password": request.form.get("password")})
            session['user_id'] = auth.user.id
            return redirect(url_for('dashboard'))
        except: flash("Login inválido", "danger")
    return render_template("login.html")

@app.route("/")
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template("dashboard.html")
# ============ API ENDPOINTS ============

@app.route("/api/status")
def api_status():
    """Retorna status do robô mestre e cliente em tempo real"""
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    try:
        state_mestre = load_state(STATE_FILE_MESTRE)
        state_cliente = load_state(STATE_FILE_CLIENTE)

        banca_inicial_mestre = float(state_mestre.get("banca_inicial", 199.44))
        ganho_dia_mestre = float(state_mestre.get("ganho_dia", 0.0))
        meta_pct_mestre = float(state_mestre.get("meta_diaria_percent", 2.0))
        meta_diaria_mestre = banca_inicial_mestre * (meta_pct_mestre / 100.0)

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
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/start", methods=["POST"])
def start_trading():
    """Inicia o trading do robô MESTRE gravando no estado"""
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    try:
        state = load_state(STATE_FILE_MESTRE)
        state["bot_active"] = True
        save_state(STATE_FILE_MESTRE, state)
        return jsonify({"success": True, "message": "Mestre iniciado!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop", methods=["POST"])
def stop_trading():
    """Para o trading do robô MESTRE gravando no estado"""
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    try:
        state = load_state(STATE_FILE_MESTRE)
        state["bot_active"] = False
        save_state(STATE_FILE_MESTRE, state)
        return jsonify({"success": True, "message": "Mestre parado!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/params", methods=["GET", "POST"])
def manage_params():
    """Gerencia leitura e escrita dos parâmetros do robô MESTRE"""
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    if request.method == "POST":
        try:
            data = request.json or {}
            state = load_state(STATE_FILE_MESTRE)
            if "stop_loss_percent" in data: state["stop_loss_percent"] = float(data["stop_loss_percent"])
            if "take_profit_percent" in data: state["take_profit_percent"] = float(data["take_profit_percent"])
            if "quantidade_percentual" in data: state["quantidade_percentual"] = float(data["quantidade_percentual"])
            if "meta_diaria_percent" in data: state["meta_diaria_percent"] = float(data["meta_diaria_percent"])
            save_state(STATE_FILE_MESTRE, state)
            return jsonify({"success": True, "message": "Parâmetros salvos!"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    # Método GET
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
        return jsonify({"error": str(e)}), 500

@app.route("/logout")
def logout():
    """Finaliza as sessões no Flask e no Supabase"""
    if supabase:
        try: supabase.auth.sign_out()
        except: pass
    session.clear()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for('login'))

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")
    app.run(host=host, port=port, debug=debug)
