import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from pathlib import Path
import json
from datetime import datetime

# ============ INTEGRAÇÃO SUPABASE ============
# Certifique-se de instalar as dependências: pip install supabase python-dotenv
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # Fallback ou aviso caso as variáveis ainda não estejam configuradas no ambiente/.env
    print("⚠️ Aviso: SUPABASE_URL e SUPABASE_KEY não configuradas no arquivo .env")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============ CONFIGURAÇÕES DE CAMINHOS UNIFICADOS ============
BASE_DIR = Path(__file__).parent.parent
STATE_FILE_MESTRE = BASE_DIR / "robo_trader" / "trading_state.json" 
STATE_FILE_CLIENTE = BASE_DIR / "robo_cliente" / "trading_state_cliente.json" 
SIGNALS_FILE = BASE_DIR / "robo_cliente" / "signals.json"
LOG_FILE = BASE_DIR / "robo_trader" / "trading_logs.txt"

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "sua_chave_secreta_aqui_2026")
DEBUG = True
HOST = "0.0.0.0"
PORT = 5000

# ============ INICIALIZAÇÃO FLASK ============
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.config['SECRET_KEY'] = SECRET_KEY

# ============ FUNÇÕES AUXILIARES PARA LER/GRAVAR ESTADO ============
def load_state(file_path):
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def save_state(file_path, state):
    with open(file_path, 'w') as f:
        json.dump(state, f, indent=4)

# ============ AUTENTICAÇÃO (SESSÃO E LOGIN) ============

@app.route("/login", methods=["GET", "POST"])
def login():
    """Gerencia a autenticação dos clientes via Supabase Auth"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not supabase:
            flash("Erro no servidor: Conexão com banco de dados não configurada.", "danger")
            return render_template("login.html")

        try:
            # Autentica usando o microsserviço do Supabase GoTrue
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # Inicializa a sessão segura do Flask
            session['user_id'] = auth_response.user.id
            session['user_email'] = auth_response.user.email
            session['access_token'] = auth_response.session.access_token
            
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash("E-mail ou senha incorretos. Tente novamente.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Finaliza as sessões no Flask e no Supabase"""
    if supabase:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
    session.clear()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for('login'))

# ============ INTERFACE GRÁFICA ============

@app.route("/")
def dashboard():
    """Carrega o dashboard principal se o usuário estiver autenticado"""
    if 'user_id' not in session:
        flash("Por favor, faça o login para acessar o painel.", "warning")
        return redirect(url_for('login'))
        
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
        return jsonify({"error": str(e)}), 500

@app.route("/api/start", methods=["POST"])
def start_trading():
    """Inicia o trading do robô MESTRE gravando no estado"""
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
        
    try:
        state = load_state(STATE_FILE_MESTRE)
        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)

        print("🚀 Status do Robô MESTRE alterado para: ATIVO!")
        return jsonify({"success": True, "message": "Trading do Mestre iniciado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao iniciar trading do Mestre: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop", methods=["POST"])
def stop_trading():
    """Para o trading do robô MESTRE gravando no estado"""
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
        
    try:
        state = load_state(STATE_FILE_MESTRE)
        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)

        print("⏹️ Status do Robô MESTRE alterado para: PARADO!")
        return jsonify({"success": True, "message": "Trading do Mestre parado com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao parar trading do Mestre: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/params", methods=["GET"])
def get_params():
    """Busca parâmetros reais gravados dinamicamente no JSON do MESTRE"""
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
        
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

@app.route("/api/params", methods=["POST"])
def save_params():
    """Persiste novos parâmetros operacionais reais de Stop/Take enviados pelo front para o MESTRE"""
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
        
    try:
        data = request.json
        state = load_state(STATE_FILE_MESTRE)

        if "stop_loss_percent" in data: state["stop_loss_percent"] = float(data["stop_loss_percent"])
        if "take_profit_percent" in data: state["take_profit_percent"] = float(data["take_profit_percent"])
        if "quantidade_percentual" in data: state["quantidade_percentual"] = float(data["quantidade_percentual"])
        if "meta_diaria_percent" in data: state["meta_diaria_percent"] = float(data["meta_diaria_percent"])

        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)

        print(f"✅ Parâmetros persistidos no arquivo de estado do robô MESTRE: {data}")
