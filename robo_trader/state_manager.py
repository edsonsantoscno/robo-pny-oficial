import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/opt/robo-pny-oficial/.env")

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "trading_state.json"


def get_saldo_binance() -> float:
    """
    Busca o saldo real da conta Binance.
    Soma USDT livre + USDT em ordem.
    Converte BTC e SOL para USDT e adiciona ao total.
    Retorna o total em USDT como float.
    """
    try:
        from binance.client import Client as BinanceSDK

        api_key    = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            print("⚠️  BINANCE_API_KEY ou BINANCE_API_SECRET não encontrados no .env")
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
                    print(f"⚠️  Erro ao converter {asset}: {e}")

        return round(saldo_total, 2)

    except Exception as e:
        print(f"❌ Erro ao buscar saldo Binance: {e}")
        return 0.0


def save_state(**kwargs):
    """
    Salva o estado do robô.
    Se 'banca_inicial' não for passado, busca da Binance automaticamente.
    """
    try:
        state = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                try:
                    state = json.load(f)
                except Exception:
                    state = {}

        # Busca saldo real se não foi passado explicitamente
        if "banca_inicial" not in kwargs:
            saldo_real = get_saldo_binance()
            if saldo_real > 0:
                kwargs["banca_inicial"] = saldo_real

        state.update(kwargs)

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
        return {}


def clear_state():
    """Remove o arquivo de estado se necessário."""
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except Exception as e:
        print(f"❌ Erro ao deletar o arquivo de estado: {e}")


def atualizar_saldo_binance():
    """
    Função standalone para atualizar apenas o saldo no JSON.
    Pode ser chamada pelo main_trader a cada ciclo.
    """
    saldo = get_saldo_binance()
    if saldo > 0:
        save_state(banca_inicial=saldo)
        print(f"✅ Saldo Binance atualizado: ${saldo}")
    return saldo
