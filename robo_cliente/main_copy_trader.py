import time
import os
from datetime import datetime, timedelta
from supabase import create_client
from binance.client import Client
from config_cliente import *
from risk_manager_cliente import RiskManagerCliente
from order_manager_cliente import OrderManagerCliente
from datetime import UTC 

class CopyTrader:
    def __init__(self):
        print("🔗 Conectando aos serviços...")
        try:
            # Conexão com o seu Supabase
            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Conexão com a Binance do Cliente
            self.binance_client = Client(API_KEY_CLIENTE, SECRET_KEY_CLIENTE)
            
            # Inicialização dos Gerenciadores
            self.risk_manager = RiskManagerCliente(BANCA_INICIAL, META_DIARIA_PERCENT, TAKE_PROFIT_META_PERCENT)
            self.order_manager = OrderManagerCliente(self.binance_client)
            
            self.ativo = COPY_TRADER_ATIVO
            self.running = False
            
            # Teste rápido de conexão
            saldo = self.binance_client.get_asset_balance(asset='USDT')
            print(f"✅ Conectado à Binance! Saldo atual: {saldo['free']} USDT")
            
        except Exception as e:
            print(f"❌ Erro crítico na inicialização: {e}")
            raise e

    def run_once(self):
        if not self.ativo:
            return

        try:
            # 1. Atualiza banca do cliente
            balance_res = self.binance_client.get_asset_balance(asset='USDT')
            usdt_balance = float(balance_res['free'])
            self.risk_manager.atualizar_banca(usdt_balance)

            # 2. Verifica Meta Diária
            if not self.risk_manager.pode_operar_hoje():
                print(f"🎯 Meta atingida para {CLIENTE_NOME}. Aguardando reset...")
                return

            # 3. Monitora posição ativa (Saída)
            if self.risk_manager.position_active:
                symbol = self.risk_manager.current_symbol
                ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
                price = float(ticker['price'])
                
                # BUSCA STATUS ATUALIZADO DO MESTRE NO SUPABASE
                # Se o Mestre mudou de 'new' para 'closed', o cliente fecha
                res_status = self.supabase.table("copy_signals")\
                    .select("status")\
                    .eq("symbol", symbol)\
                    .order("created_at", desc=True).limit(1).execute()
                
                status_mestre = res_status.data[0]['status'] if res_status.data else "new"
                
                stop, _ = self.risk_manager.check_stop_loss(price)
                take, _ = self.risk_manager.check_take_profit(price)
                
                # O cliente fecha se o mestre enviar sinal de SELL OR se o status for 'closed'
                if stop or take or status_mestre == "closed":
                    reason = "STATUS CLOSED" if status_mestre == "closed" else "STOP/TAKE"
                    self._execute_sell(symbol, price, reason)
                return

            # 4. BUSCA NOVOS SINAIS NO SUPABASE (Entrada)
            # TRAVA DE SEGURANÇA: Só aceita sinais criados nos últimos 3 minutos
            tempo_limite = (datetime.now(UTC) - timedelta(minutes=3)).isoformat()

            res = self.supabase.table("copy_signals")\
                .select("*")\
                .eq("status", "new")\
                .eq("operation_type", "BUY")\
                .gt("created_at", tempo_limite)\
                .order("created_at", desc=True).limit(1).execute()
            
            if res.data:
                sinal = res.data[0]
                self._execute_buy(sinal)
            else:
                # Log silencioso
                print(f"🔍 [{time.strftime('%H:%M:%S')}] Monitorando sinais recentes...")

        except Exception as e:
            print(f"❌ Erro no ciclo do cliente: {e}")

    def _execute_buy(self, sinal):
        try:
            symbol = sinal['symbol']
            price_mestre = sinal['price']
            
            calc = self.order_manager.calculate_quantity(symbol, quantity_percent=QUANTIDADE_PERCENTUAL)
            
            if calc:
                print(f"🚀 Copiando COMPRA de {symbol}...")
                order = self.binance_client.create_order(
                    symbol=symbol, 
                    side='BUY', 
                    type='MARKET', 
                    quantity=calc['quantity']
                )
                
                if order:
                    # Usa Stop e Take que o mestre sugeriu ou os padrões do cliente
                    sl = sinal.get('stop_loss', 2.0)
                    tp = sinal.get('take_profit', 2.0)
                    self.risk_manager.set_entry(symbol, price_mestre, calc['quantity'], sl, tp)
                    
                    # Opcional: Marcar como processado apenas para controle local se for multi-cliente
                    print(f"✅ Ordem de COMPRA {symbol} executada!")
        except Exception as e:
            print(f"❌ Falha ao executar compra: {e}")

    def _execute_sell(self, symbol, price, reason):
        try:
            qty = self.risk_manager.entry_quantity
            print(f"💰 Copiando VENDA de {symbol} ({reason})...")
            order = self.binance_client.create_order(symbol=symbol, side='SELL', type='MARKET', quantity=qty)
            if order:
                self.risk_manager.clear_position()
                print(f"✅ Ordem de VENDA executada!")
        except Exception as e:
            print(f"❌ Falha ao executar venda: {e}")

    def run_continuous(self):
        self.running = True
        print("⚡ Monitoramento em tempo real ativado.")
        while self.running:
            self.run_once()
            time.sleep(5)

if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print(f"🤖 CLIENTE COPY TRADER - VERSÃO PRODUÇÃO")
        print(f"👤 Cliente: {CLIENTE_NOME}")
        print("="*60 + "\n")
        
        bot_cliente = CopyTrader()
        bot_cliente.run_continuous()
        
    except KeyboardInterrupt:
        print("\n⏹️  Copy Trader desligado.")
    except Exception as fatal_error:
        print(f"💥 Erro fatal: {fatal_error}")
