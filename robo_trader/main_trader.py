import time
import json
import os
from datetime import datetime, timedelta
from config import *
from client import BinanceClient
from strategy import AgressiveStrategy
from order_manager import OrderManager
from risk_manager import RiskManager
from logger import TradingLogger
from signal_generator import SignalGenerator
from pathlib import Path
from state_manager import atualizar_saldo_binance, save_state
from pathlib import Path

# No main_trader.py e app.py
STATE_FILE = Path(os.getenv("STATE_FILE_PATH", Path(__file__).parent / "trading_state.json"))


# No início do loop principal (a cada ciclo de ~5 segundos)
atualizar_saldo_binance()

# Certifica a leitura do arquivo de estado unificado na raiz do container
STATE_FILE = Path("/app/state") / "trading_state.json"

class TradingBotTrader:
    def __init__(self):
        self.binance_client = BinanceClient()
        self.strategy = AgressiveStrategy(self.binance_client)
        self.order_manager = OrderManager(self.binance_client)
        self.risk_manager = RiskManager(BANCA_INICIAL, take_profit_meta_percent=TAKE_PROFIT_META_PERCENT)
        self.logger = TradingLogger()
        self.signal_generator = SignalGenerator()
        self.running = True

    def verificar_se_bot_pode_operar(self):
        """Verifica se o botão Iniciar do Dashboard está ativado"""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                return state.get("bot_active", False)
        except Exception as e:
            print(f"❌ Erro ao ler controle de execução JSON: {e}")
        return False

    def run_once(self):
        try:
            # 1. Checagem Obrigatória de Segurança SaaS (Botão Ligar/Desligar)
            if not self.verificar_se_bot_pode_operar():
                print("💤 Robô em modo de espera... Ative no Dashboard para iniciar operações.")
                return True

            # 2. Atualização Financeira e Cálculo de Banca
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
            print(f"💰 BANCA TOTAL: {banca_total:.2f} USDT | LIVRE: {usdt_livre:.2f} USDT")
            print(f"📈 LUCRO HOJE: {ganho_usdt:.2f} USDT ({ganho_pct:.2f}%)")
            print(f"🎯 META DIÁRIA: {meta_usdt:.2f} USDT | FALTA: {max(0, meta_usdt - ganho_usdt):.2f} USDT")
            print("-"*60)

            # 3. Verificação Inteligente de Meta Diária (Sem travar o container)
            if not self.risk_manager.pode_operar_hoje():
                print(f"🎯 META DIÁRIA ATINGIDA! Aguardando o reset do dia seguinte...")
                time.sleep(900) # Aguarda 15 minutos de forma saudável antes de checar de novo
                return True

            # 4. GESTÃO DE POSIÇÃO ATIVA E SUPORTE A PARÂMETROS DINÂMICOS DO SAAS
            if self.risk_manager.position_active:
                symbol = self.risk_manager.current_symbol
                price = float(self.binance_client.get_current_price(symbol))
                data = self.strategy.get_data(symbol, INTERVAL)
                signal = self.strategy.calculate_signal(data)
                
                # --- INTEGRADO: ATUALIZA AS TRAVAS DE RISCO DIRETAMENTE VIA DASHBOARD SAAS ---
                try:
                    if STATE_FILE.exists():
                        with open(STATE_FILE, 'r') as f:
                            current_state = json.load(f)
                        # Sobrescreve as constantes se houver alteração em tempo real na interface web
                        sl_percent = float(current_state.get("stop_loss_percent", STOP_LOSS_PERCENT))
                        tp_percent = float(current_state.get("take_profit_percent", TAKE_PROFIT_PERCENT))
                    else:
                        sl_percent, tp_percent = STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT
                except Exception:
                    sl_percent, tp_percent = STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT

                pct_atual = ((price - self.risk_manager.entry_price) / self.risk_manager.entry_price) * 100
                
                # Lógica matemática dinâmica de validação baseada nos novos inputs do painel
                stop = pct_atual <= -sl_percent
                lucro_usdt = (price - self.risk_manager.entry_price) * self.risk_manager.entry_quantity
                take = (lucro_usdt >= (self.risk_manager.get_meta_diaria() * self.risk_manager.take_profit_meta_percent) or pct_atual >= tp_percent)
                
                print(f"👀 Monitorando {symbol}: Preço ${price:.4f} | Lucro Atual: {pct_atual:.2f}% (SL Alvo: -{sl_percent}% / TP Alvo: {tp_percent}%) | Sinal: {signal}")

                # Proteção PNY: Só permite saída por sinal oposto se houver lucro cobrindo as taxas
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
                
                # Coleta os percentuais corretos lidos do painel para enviar ao sinal do cliente
                try:
                    with open(STATE_FILE, 'r') as f:
                        current_state = json.load(f)
                    sl_percent = float(current_state.get("stop_loss_percent", STOP_LOSS_PERCENT))
                    tp_percent = float(current_state.get("take_profit_percent", TAKE_PROFIT_PERCENT))
                except Exception:
                    sl_percent, tp_percent = STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT

                # Projeta alvos matemáticos atualizados para o cliente final
                stop_p = price * (1 - sl_percent/100.0)
                take_p = price * (1 + tp_percent/100.0)

                # 1. ENVIAR SINAL PARA O BANCO DE DADOS (SUPABASE)
                self.signal_generator.generate_signal(
                    "BUY", calc["quantity"], price, symbol, 
                    status="new", 
                    stop_loss=stop_p, 
                    take_profit=take_p
                )
                
                # 2. INTEGRADO: SALVAR SINAL RÁPIDO PARA O SERVIDOR WEBSOCKET
                try:
                    with open(Path(__file__).parent / "latest_signal.json", "w") as f:
                        json.dump({
                            "operation_type": "BUY", 
                            "symbol": symbol, 
                            "price": float(price), 
                            "quantity": float(calc["quantity"]),
                            "timestamp": time.time()
                        }, f, indent=4)
                except Exception as ws_err:
                    print(f"⚠️ Erro ao gravar arquivo rápido do WebSocket: {ws_err}")
                
                self.logger.log_entry("BUY", symbol, calc["quantity"], price, calc["notional"], f"Modo: {MODO_ESTRATEGIA}")
                print(f"📡 Sinal de COMPRA transmitido ao Supabase e ao WebSocket.")

    def _execute_sell(self, symbol, price, reason):
        qty = self.risk_manager.entry_quantity
        if self.order_manager.validate_order(symbol, "SELL", qty):
            order = self.binance_client.create_order(symbol, "SELL", qty)
            if order:
                # 1. ENVIAR SINAL DE FECHAMENTO PARA O BANCO DE DADOS (SUPABASE)
                self.signal_generator.generate_signal("SELL", qty, price, symbol, status="closed")
                
                # 2. INTEGRADO: SALVAR SINAL RÁPIDO DE FECHAMENTO PARA O SERVIDOR WEBSOCKET
                try:
                    with open(Path(__file__).parent / "latest_signal.json", "w") as f:
                        json.dump({
                            "operation_type": "SELL", 
                            "symbol": symbol, 
                            "price": float(price), 
                            "quantity": float(qty),
                            "reason": reason,
                            "timestamp": time.time()
                        }, f, indent=4)
                except Exception as ws_err:
                    print(f"⚠️ Erro ao gravar arquivo rápido do WebSocket: {ws_err}")

                self.logger.log_entry("SELL", symbol, qty, price, qty*price, reason)
                self.risk_manager.clear_position()
                print(f"📡 Sinal de VENDA transmitido ao Supabase e ao WebSocket.")

    def run_continuous(self):
        print("\n" + "="*60)
        print(f"🚀 ROBÔ SCANNER MESTRE - MODO: {MODO_ESTRATEGIA} ATIVADO")
        print(f"Ativos: {', '.join(SYMBOLS)}")
        print(f"Alvo TP padrão: {TAKE_PROFIT_PERCENT}% | Stop SL padrão: {STOP_LOSS_PERCENT}%")
        print("="*60 + "\n")
        
        while self.running:
            self.run_once()
            time.sleep(15) # Ciclo de leitura padrão do robô

if __name__ == "__main__":
    try:
        bot = TradingBotTrader()
        bot.run_continuous()
    except KeyboardInterrupt:
        print("\n⏹️ Robô desligado via terminal.")
