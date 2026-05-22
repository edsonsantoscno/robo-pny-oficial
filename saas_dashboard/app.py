import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pathlib import Path
import json
from datetime import datetime

# ============ CONFIGURAÇÕES DE CAMINHOS UNIFICADOS ============
BASE_DIR = Path(__file__).parent.parent
STATE_FILE_MESTRE = BASE_DIR / "robo_trader" / "trading_state.json" # Renomeado para clareza
STATE_FILE_CLIENTE = BASE_DIR / "robo_cliente" / "trading_state_cliente.json" # Novo arquivo de estado do cliente
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

# ============ FUNÇÕES AUXILIARES PARA LER/GRAVAR ESTADO ============
def load_state(file_path):
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def save_state(file_path, state):
    with open(file_path, 'w') as f:
        json.dump(state, f, indent=4)

# ============ API ENDPOINTS ============

@app.route("/")
def dashboard():
    """Carrega o dashboard principal"""
    return render_template("dashboard.html")

@app.route("/api/status")
def api_status():
    """Retorna status do robô mestre e cliente em tempo real"""
    try:
        state_mestre = load_state(STATE_FILE_MESTRE)
        state_cliente = load_state(STATE_FILE_CLIENTE) # Carrega o estado do cliente

        # Fallbacks de segurança para o Mestre
        banca_inicial_mestre = float(state_mestre.get("banca_inicial", 199.44))
        ganho_dia_mestre = float(state_mestre.get("ganho_dia", 0.0)) # Ajustado para 0.0 como default
        meta_pct_mestre = float(state_mestre.get("meta_diaria_percent", 2.0))
        meta_diaria_mestre = banca_inicial_mestre * (meta_pct_mestre / 100.0)

        # Fallbacks de segurança para o Cliente
        banca_inicial_cliente = float(state_cliente.get("banca_inicial", 0.0)) # Pega do estado do cliente
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
                "saldo": banca_inicial_mestre, # Usando banca_inicial do mestre para compatibilidade com o JS atual
                "lucro_hoje": ganho_dia_mestre,
                "meta_diaria": meta_diaria_mestre,
                "falta_meta": max(0.0, meta_diaria_mestre - ganho_dia_mestre)
            },
            "cliente": {
                "status": "connected",
                "bot_active": state_cliente.get("bot_active", True), # Assume True se não existir
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
    try:
        state = load_state(STATE_FILE_MESTRE)
        return jsonify({
            "stop_loss_percent": float(state.get("stop_loss_percent", 4.0)),
            "take_profit_percent": float(state.get("take_profit_percent", 2.0)),
            "meta_diaria_percent": float(state.get("meta_diaria_percent", 2.0)),
            "quantidade_percentual": float(state.get("quantidade_percentual", 100.0)), # Este é do mestre, não do cliente
            "estrategia": state.get("estrategia", "PNY")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/params", methods=["POST"])
def save_params():
    """Persiste novos parâmetros operacionais reais de Stop/Take enviados pelo front para o MESTRE"""
    try:
        data = request.json
        state = load_state(STATE_FILE_MESTRE)

        # Faz o update seguro mantendo o histórico e injetando as novas travas do input
        if "stop_loss_percent" in data: state["stop_loss_percent"] = float(data["stop_loss_percent"])
        if "take_profit_percent" in data: state["take_profit_percent"] = float(data["take_profit_percent"])
        if "quantidade_percentual" in data: state["quantidade_percentual"] = float(data["quantidade_percentual"])
        if "meta_diaria_percent" in data: state["meta_diaria_percent"] = float(data["meta_diaria_percent"])

        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)

        print(f"✅ Parâmetros persistidos no arquivo de estado do robô MESTRE: {data}")
        return jsonify({"success": True, "message": "Parâmetros do Mestre salvos com sucesso!", "data": data})
    except Exception as e:
        print(f"❌ Erro ao salvar parâmetros do Mestre em disco: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/strategy", methods=["POST"])
def update_strategy_route():
    """Persiste a alteração da estratégia operacional (PNY, RSI, EMA) feita no painel para o MESTRE"""
    try:
        data = request.json
        strategy = data.get("strategy", "PNY")

        state = load_state(STATE_FILE_MESTRE)
        state["estrategia"] = strategy
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_MESTRE, state)

        print(f"🎯 Inteligência do Robô MESTRE alterada para o Setup: {strategy}")
        return jsonify({"success": True, "strategy": strategy, "message": f"Estratégia do Mestre alterada para {strategy}"})
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
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            return jsonify({"logs": lines[-10:] if len(lines) > 10 else lines})
        return jsonify({"logs": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ NOVOS ENDPOINTS PARA O CLIENTE ============

@app.route("/api/cliente/status")
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
        return jsonify({"error": str(e)}), 500

@app.route("/api/cliente/start", methods=["POST"])
def start_cliente_trading():
    """Ativa a cópia no robô CLIENTE"""
    try:
        state = load_state(STATE_FILE_CLIENTE)
        state["bot_active"] = True
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_CLIENTE, state)

        print("🚀 Status do Robô CLIENTE alterado para: ATIVO!")
        return jsonify({"success": True, "message": "Cópia do Cliente iniciada com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao iniciar cópia do Cliente: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/cliente/stop", methods=["POST"])
def stop_cliente_trading():
    """Desativa a cópia no robô CLIENTE"""
    try:
        state = load_state(STATE_FILE_CLIENTE)
        state["bot_active"] = False
        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_CLIENTE, state)

        print("⏹️ Status do Robô CLIENTE alterado para: PARADO!")
        return jsonify({"success": True, "message": "Cópia do Cliente parada com sucesso!"})
    except Exception as e:
        print(f"❌ Erro ao parar cópia do Cliente: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/cliente/params", methods=["GET"])
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
        return jsonify({"error": str(e)}), 500

@app.route("/api/cliente/params", methods=["POST"])
def save_cliente_params():
    """Persiste novos parâmetros operacionais reais de Stop/Take/Quantidade enviados pelo front para o CLIENTE"""
    try:
        data = request.json
        state = load_state(STATE_FILE_CLIENTE)

        if "stop_loss_percent" in data: state["stop_loss_percent"] = float(data["stop_loss_percent"])
        if "take_profit_percent" in data: state["take_profit_percent"] = float(data["take_profit_percent"])
        if "quantidade_percentual" in data: state["quantidade_percentual"] = float(data["quantidade_percentual"])
        if "meta_diaria_percent" in data: state["meta_diaria_percent"] = float(data["meta_diaria_percent"])

        state["updated_at"] = datetime.now().isoformat()
        save_state(STATE_FILE_CLIENTE, state)

        print(f"✅ Parâmetros persistidos no arquivo de estado do robô CLIENTE: {data}")
        return jsonify({"success": True, "message": "Parâmetros do Cliente salvos com sucesso!", "data": data})
    except Exception as e:
        print(f"❌ Erro ao salvar parâmetros do Cliente em disco: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    @app.route('/login', methods=['GET', 'POST'])
def login():
    # Se o usuário já estiver logado, redireciona direto para o painel
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # 1. Tenta autenticar o usuário diretamente no Supabase Auth
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # 2. Se as credenciais forem válidas, salva os dados na sessão do Flask
            session['user_id'] = auth_response.user.id
            session['user_email'] = auth_response.user.email
            session['access_token'] = auth_response.session.access_token
            
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            # Captura erros de senha errada ou usuário inexistente
            flash('E-mail ou senha incorretos. Tente novamente.', 'danger')
            
    # Se o método for GET, apenas exibe a página HTML de login
    return render_template('login.html')


@app.route('/logout')
def logout():
    try:
        # Encerra a sessão ativa no servidor do Supabase
        supabase.auth.sign_out()
    except Exception:
        pass
        
    # Limpa todos os dados salvos no navegador do cliente
    session.clear()
    flash('Sessão encerrada com sucesso.', 'info')
    return redirect(url_for('login'))

