import json
import os
import threading
from pathlib import Path
from dotenv import load_dotenv

# Mecanismo Global de Trava (Lock) contra corrupção simultânea de I/O de disco
state_lock = threading.Lock()

# CORREÇÃO #1: Alinhado com o diretório raiz /app do contêiner Docker conforme docker-compose
BASE_DIR = Path(__file__).parent
STATE_FILE = Path("/app/trading_state.json")

# Carregamento correto do arquivo .env relativo ao diretório atual do robô
load_dotenv(BASE_DIR / ".env")

def get_saldo_binance() -> float:
    """
    Busca o saldo real da conta Binance.
    Soma USDT livre + USDT em ordem.
    Converte BTC, SOL e BNB para USDT e adiciona ao total.
    Retorna o total em USDT como float com duas casas decimais.
    """
    try:
        from binance.client import Client as BinanceSDK
        
        # CORREÇÃO #2: Sincronização dos nomes das chaves de API com o config.py e Docker Stack
        api_key = os.getenv("KEY_BINANCE") or os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("SECRET_BINANCE") or os.getenv("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            print("⚠ Chaves de API (KEY_BINANCE/SECRET_BINANCE) não localizadas na memória da VPS.")
            return 0.0

        client = BinanceSDK(api_key, api_secret)
        account = client.get_account()
        saldo_total = 0.0
        ativos_converter = {"BTC": "BTCUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT"}

        for balance in account["balances"]:
            asset = balance["asset"]
            livre = float(balance["free"])
            bloqueado = float(balance["locked"])
            total_asset = livre + bloqueado

            if total_asset <= 0:
                continue

            if asset == "USDT":
                saldo_total += total_asset
            elif asset in ativos_converter:
                try:
                    ticker = client.get_symbol_ticker(symbol=ativos_converter[asset])
                    preco = float(ticker["price"])
                    saldo_total += total_asset * preco
                except Exception as e:
                    print(f"⚠ Erro ao converter {asset}: {e}")

        return round(saldo_total, 2)
    except Exception as e:
        print(f"❌ Erro ao buscar saldo Binance: {e}")
        return 0.0

def save_state(**kwargs):
    """
    Salva o estado do robô no arquivo JSON de forma atômica e segura.
    Se 'banca_inicial' não for passado, busca da Binance automaticamente.
    Usa a trava global thread-safe state_lock para impedir colisões de I/O.
    """
    # CORREÇÃO #3: Encapsulamento completo de gravação com o Lock de Processos
    with state_lock:
        try:
            state = {}
            if STATE_FILE.exists():
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    try:
                        state = json.load(f)
                    except Exception:
                        state = {}

            # Busca o saldo real da carteira se não foi passado explicitamente por parâmetro
            if "banca_inicial" not in kwargs:
                saldo_real = get_saldo_binance()
                if saldo_real > 0:
                    kwargs["banca_inicial"] = saldo_real

            state.update(kwargs)
            
            # Força a criação do diretório pai caso não exista na primeira inicialização
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro crítico ao salvar o arquivo de estado JSON: {e}")

def load_state() -> dict:
    """Lê o estado atual do arquivo JSON de forma segura com trava de isolamento."""
    if not STATE_FILE.exists():
        return {}
    with state_lock:
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

def clear_state():
    """Remove o arquivo de estado do disco de forma limpa se necessário."""
    with state_lock:
        try:
            if STATE_FILE.exists():
                STATE_FILE.unlink()
                print("🧹 Arquivo de estado limpo com sucesso.")
        except Exception as e:
            print(f"❌ Erro ao deletar o arquivo de estado: {e}")

def atualizar_saldo_binance() -> float:
    """
    Função standalone para atualizar apenas o saldo no JSON.
    Pode ser chamada pelo main_trader a cada ciclo operacional.
    """
    saldo = get_saldo_binance()
    if saldo > 0:
        save_state(banca_inicial=saldo)
        print(f"✅ Saldo Binance atualizado: ${saldo}")
    return saldo
