import json
from pathlib import Path

# Força o arquivo a ser criado e lido EXATAMENTE na raiz compartilhada do container,
# eliminando o risco do Dashboard e o Robô lerem caminhos diferentes.
BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "trading_state.json"

def save_state(**kwargs):
    """
    Salva o estado do robô aceitando parâmetros dinâmicos.
    Garante compatibilidade total com o risk_manager e o app.py do dashboard.
    """
    try:
        # Se o arquivo já existir, carrega os dados atuais para não apagar chaves como 'bot_active'
        state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                try:
                    state = json.load(f)
                except Exception:
                    state = {}

        # Atualiza o dicionário com as novas informações enviadas pelo robô
        state.update(kwargs)

        # Grava de forma segura na raiz do projeto
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
            
    except Exception as e:
        print(f"❌ Erro crítico ao salvar o arquivo de estado JSON: {e}")

def load_state():
    """Lê o estado atual de forma segura contra corrupção de arquivos."""
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # Se o arquivo estiver corrompido ou vazio, retorna um estado padrão limpo
        return {}

def clear_state():
    """Remove o arquivo de estado se necessário."""
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except Exception as e:
        print(f"❌ Erro ao deletar o arquivo de estado: {e}")
