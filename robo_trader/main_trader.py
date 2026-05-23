import time
import json
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Imports nativos do seu ecossistema original
from config import *
from client import BinanceClient
from strategy import AgressiveStrategy
from order_manager import OrderManager
from risk_manager import RiskManager
from logger import TradingLogger
from signal_generator import SignalGenerator
from state_manager import atualizar_saldo_binance, save_state

# Import do cliente oficial do Supabase para a sincronização SaaS
from supabase import create_client, Client as SupabaseClient

# ============ CONFIGURAÇÃO DE INFRAESTRUTURA E SEGURANÇA ============
state_lock = threading.Lock()

# Certifica a leitura do arquivo de estado unificado na raiz do container
STATE_FILE = Path("/app/state") / "trading_state.json"

# Inicialização do cliente Supabase carregando do ambiente/.env
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: SupabaseClient = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============ FUNÇÕES AUXILIARES CONCORRENTES (THREAD-SAFE) ============

def safe_load_state() -> dict:
    """Lê o arquivo JSON usando travas para evitar quebras por concorrência"""
    with state_lock:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Arquivo de estado corrompido ou ocupado. Ignorando ciclo...")
        return {}

def safe_save_state(state: dict):
    """Grava as atualizações locais em disco de forma isolada"""
    with state_lock:
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"❌ Falha ao gravar estado local em disco: {e}")

def sync_mestre_to_supabase(state: dict, banca_total: float, ganho_usdt: float, meta_usdt: float):
    """Envia o batimento cardíaco e o status real do mestre para a nuvem"""
    if not supabase:
        return
    try:
        supabase.table("configuracoes_mestre").upsert({
            "id": "mestre",
            "bot_active": state.get("bot_active", False),
            "position_active": state.get("position_active", False),
            "current_symbol": state.get("current_symbol", "N/A"),
            "entry_price": float(state.get("entry_price", 0.0)),
            "estrategia": state.get("estrategia", MODO_ESTRATEGIA),
            "saldo": banca_total,
            "lucro_hoje": ganho_usdt,
            "meta_diaria": meta_usdt,
            "falta_meta": max(0.0, meta_usdt - ganho_usdt),
            "updated_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"❌ Erro ao atualizar nuvem do Supabase: {e}")

# ============ CLASSE PRINCIPAL DO ROBÔ REESTRUTURADA ============

class TradingBotTrader:
    def __init__(self):
        self.binance_client = BinanceClient()
        self.strategy = AgressiveStrategy(self.binance_client)
        self.order_manager = OrderManager(self.binance_client)
        
        # Puxa o saldo real da Binance para inicializar a carteira em USDT dinamicamente
        saldo_inicial_real = float(self.binance_client.get_asset_balance("USDT"))
        self.risk_manager = RiskManager(saldo_inicial_real, take_profit_meta_percent=TAKE_PROFIT_META_PERCENT)
        
        self.logger = TradingLogger()
        self.signal_generator = SignalGenerator()
        self.running = True

    def verificar_se_bot_pode_operar(self):
        """Verifica se o botão Iniciar do Dashboard está ativado usando leitura segura"""
        state = safe_load_state()
        return state.get("bot_active", False)

    def run_once(self):
        try:
            # 1. Checagem Obrigatória de Segurança SaaS (Botão Ligar/Desligar)
            if not self.verificar_se_bot_pode_operar():
                print("💤 Robô em modo de espera... Ative no Dashboard para iniciar operações.")
                state = safe_load_state()
                sync_mestre_to_supabase(state, self.risk_manager.banca_inicial, 0.0, 0.0)
                return True

            # 2. Atualização Financeira e Cálculo de Banca Dinâmica USDT
            usdt_livre = float(self.binance_client.get_asset_balance("USDT"))
            banca_total = usdt_livre
            
            if self.risk_manager.position_active and self.risk_manager.entry_quantity:
                price_now = float(self.binance_client.get_current_price(self.risk_manager.current_symbol))
                banca_total += (float(self.risk_manager.entry_quantity) * price_now)
            
            self.risk_manager.atualizar_banca(banca_total)

            ganho_usdt = self.risk_manager.get_ganho_atual()
            ganho_pct = self.risk_manager.get_percentual_ganho()
            meta_usdt = self.risk_manager.get_meta_diaria()
            
            print(f"\n" + "-"*60)
            print(f"💰 BANCA TOTAL DINÂMICA: {banca_total:.2f} USDT | LIVRE: {usdt_livre:.2f} USDT")
            print(f"📈 LUCRO HOJE: {ganho_usdt:.2f} USDT ({ganho_pct:.2f}%)")
            print(f"🎯 META DIÁRIA: {meta_usdt:.2f} USDT | FALTA: {max(0, meta_usdt - ganho_usdt):.2f} USDT")
            print("-"*60)

            current_state = safe_load_state()
            sync_mestre_to_supabase(current_state, banca_total, ganho_usdt, meta_usdt)

            # 3. Verificação Inteligente de Meta Diária
            if not self.risk_manager.pode_operar_hoje():
                print(f"🎯 META DIÁRIA ATINGIDA! Aguardando o reset do dia seguinte...")
                time.sleep(900) 
                return True

            # 4. GESTÃO DE POSIÇÃO ATIVA E SUPORTE A PARÂMETROS DINÂMICOS DO SAAS
            if self.risk_manager.position_active:
                symbol = self.risk_manager.current_symbol
                price = float(self.binance_client.get_current_price(symbol))
                data = self.strategy.get_data(symbol, INTERVAL)
                signal = self.strategy.calculate_signal(data)
                
                current_state = safe_load_state()
                sl_percent = float(current_state.get("stop_loss_percent", STOP_LOSS_PERCENT))
                tp_percent = float(current_state.get("take_profit_percent", TAKE_PROFIT_PERCENT))

                pct_atual = ((price - self.risk_manager.entry_price) / self.risk_manager.entry_price) * 100
                
                stop = pct_atual <= -sl_percent
                lucro_usdt = (price - self.risk_manager.entry_price) * self.risk_manager.entry_quantity
                take = (lucro_usdt >= (self.risk_manager.get_meta_diaria() * self.risk_manager.take_profit_meta_percent) or pct_atual >= tp_percent)
                
                print(f"👀 Monitorando {symbol}: Preço ${price:.4f} | Lucro Atual: {pct_atual:.2f}% (SL Alvo: -{sl_percent}% / TP Alvo: {tp_percent}%) | Sinal: {signal}")

                pode_vender_por_sinal = (signal == "SELL" and pct_atual > 0.20)

                if stop or take or pode_vender_por_sinal:
                    reason = "STOP LOSS" if stop else "TAKE PROFIT" if take else f"SINAL SELL ({pct_atual:.2f}%)"
                    self._execute_sell(symbol, price, reason)
                return True

            # 5. SCANNER DE MERCADO
            print(f"🔍 SCANNER ({MODO_ESTRATEGIA}): Analisando {len(SYMBOLS)} moedas...")
            for symbol in SYMBOLS:
                data = self.strategy.get_data(symbol, INTERVAL)
                if data is None: continue
                
                signal = self.strategy.calculate_signal(data)
                
                if signal == "BUY":
                    price = float(self.binance_client.get_current_price(symbol))
                    print(f"\n✅ COMPRA IDENTIFICADA: {symbol} a ${price}")
                    self._execute_buy(symbol, price)
                    break 

            return True

        except Exception as e:
            print(f"❌ Erro crítico no ciclo do robô: {e}")
            return False

    def _execute_buy(self, symbol, price):
        calc = self.order_manager.calculate_quantity(symbol)
        if calc and self.order_manager.validate_order(symbol, "BUY", calc["quantity"]):
            order = self.binance_client.create_order(symbol, "BUY", calc["quantity"])
            if order:
                self.risk_manager.set_entry(symbol, price, calc["quantity"])
                
                current_state = safe_load_state()
                sl_percent = float(current_state.get("stop_loss_percent", STOP_LOSS_PERCENT))
                tp_percent = float(current_state.get("take_profit_percent", TAKE_PROFIT_PERCENT))

                # Projeta alvos matemáticos para proteção OCO nativa na Binance
                preco_take = round(price * (1 + (tp_percent / 100)), 4)
                preco_stop = round(price * (1 - (sl_percent / 100)), 4)
                preco_stop_limit = round(preco_stop * 0.995, 4)

                print(f"🛡️ [Binance OCO] Enviando travas nativas para a Exchange:")
                print(f"   🎯 Take Profit: {preco_take} | 🛑 Stop Loss: {preco_stop}")

                # ⚡ ENVIO DA ORDEM OCO PROTEGIDA
                try:
                    self.binance_client.client.create_oco_order(
                        symbol=symbol,
                        side="SELL",
                        quantity=calc["quantity"],
                        price=str(preco_take),
                        stopPrice=str(preco_stop),
                        stopLimitPrice=str(preco_stop_limit),
                        stopLimitTimeInForce="GTC"
                    )
                    print("🔒 Alvos OCO criados com sucesso na Binance. Fundos protegidos contra quedas de internet!")
                except Exception as e:
                    print(f"❌ Erro crítico no ciclo do robô: {e}")
                    return False
            def _execute_buy(self, symbol, price):
                calc = self.order_manager.calculate_quantity(symbol)
        if calc and self.order_manager.validate_order(symbol, "BUY", calc["quantity"]):
            order = self.binance_client.create_order(symbol, "BUY", calc["quantity"])
            if order:
                self.risk_manager.set_entry(symbol, price, calc["quantity"])
                
                current_state = safe_load_state()
                sl_percent = float(current_state.get("stop_loss_percent", STOP_LOSS_PERCENT))
                tp_percent = float(current_state.get("take_profit_percent", TAKE_PROFIT_PERCENT))

                # Projeta alvos matemáticos para proteção OCO nativa na Binance
                preco_take = round(price * (1 + (tp_percent / 100)), 4)
                preco_stop = round(price * (1 - (sl_percent / 100)), 4)
                preco_stop_limit = round(preco_stop * 0.995, 4)

                print(f"🛡️ [Binance OCO] Enviando travas nativas para a Exchange:")
                print(f"   🎯 Take Profit: {preco_take} | 🛑 Stop Loss: {preco_stop}")

                # ⚡ ENVIO DA ORDEM OCO PROTEGIDA
                try:
                    self.binance_client.client.create_oco_order(
                        symbol=symbol,
                        side="SELL",
                        quantity=calc["quantity"],
                        price=str(preco_take),
                        stopPrice=str(preco_stop),
                        stopLimitPrice=str(preco_stop_limit),
                        stopLimitTimeInForce="GTC"
                    )
                    print("🔒 Alvos OCO criados com sucesso na Binance. Fundos protegidos contra quedas de internet!")
                except Exception as oco_err:
                    print(f"⚠️ Alerta OCO: Falha ao enviar OCO nativo na exchange (usando gerenciamento por software): {oco_err}")

                # Atualiza as variáveis locais do estado unificado
                current_state["position_active"] = True
                current_state["current_symbol"] = symbol
                current_state["entry_price"] = price
                current_state["updated_at"] = datetime.now().isoformat()
                safe_save_state(current_state)

                # 1. ENVIAR SINAL PARA O BANCO DE DADOS (SUPABASE)
                self.signal_generator.generate_signal(
                    "BUY", calc["quantity"], price, symbol, 
                    status="new", 
                    stop_loss=preco_stop, 
                    take_profit=preco_take
                )
                
                # 2. INTEGRADO: SALVAR SINAL RÁPIDO PARA O SERVIDOR WEBSOCKET
                try:
                    signal_payload = {
                        "action": "BUY",
                        "symbol": symbol,
                        "quantity": calc["quantity"],
                        "price": price,
                        "stop_loss": preco_stop,
                        "take_profit": preco_take,
                        "timestamp": datetime.now().isoformat()
                    }
                    with open(Path(__file__).parent / "latest_signal.json", "w") as f:
                        json.dump(signal_payload, f, indent=4)
                    print("📡 Sinal temporário exportado com sucesso para o transmissor do WebSocket.")
                except Exception as ws_err:
                    print(f"❌ Erro ao exportar sinal para o WebSocket local: {ws_err}")

    def _execute_sell(self, symbol, price, reason):
        """Executa a saída de posição limpando as travas OCO e os estados locais/nuvem"""
        print(f"⏹️ Executando saída de {symbol} por motivo: {reason}")
        
        try:
            open_orders = self.binance_client.client.get_open_orders(symbol=symbol)
            for o in open_orders:
                if 'oco' in o.get('type', '').lower() or o.get('contingencyType') == 'OCO':
                    self.binance_client.client.cancel_order(symbol=symbol, orderId=o['orderId'])
                    print(f"🧹 Ordem OCO antiga {o['orderId']} cancelada com sucesso.")
        except Exception as c_err:
            print(f"⚠️ Nota ao limpar ordens OCO: {c_err}")

        calc_quantity = self.risk_manager.entry_quantity
        order = self.binance_client.create_order(symbol, "SELL", calc_quantity)
        
        if order:
            self.risk_manager.clear_entry()
            
            current_state = safe_load_state()
            current_state["position_active"] = False
            current_state["current_symbol"] = "N/A"
            current_state["entry_price"] = 0.0
            current_state["updated_at"] = datetime.now().isoformat()
            safe_save_state(current_state)
            
            self.signal_generator.generate_signal(
                "SELL", calc_quantity, price, symbol, 
                status="closed", 
                stop_loss=0.0, 
                take_profit=0.0
            )
            print(f"✅ Posição encerrada com sucesso por {reason} a preço ${price}")

# ============ INICIALIZAÇÃO DO SERVIDOR COM SEGURANÇA NO TERMINAL ============
if __name__ == "__main__":
    try:
        bot = TradingBotTrader()
        print("🚀 Motor do Robô Mestre inicializado. Rodando loop de monitoramento contínuo...")
        while bot.running:
            bot.run_once()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n⏹️ Robô de trading desligado via terminal de forma segura.")

