import json
import threading
from datetime import datetime
from pathlib import Path
from logger_cliente import TradingLoggerCliente

# CORREÇÃO #2: Caminho físico unificado na raiz /app e mecanismo de trava contra colisões de I/O
file_lock = threading.Lock()
STATE_FILE = Path("/app/trading_state_cliente.json")

class RiskManagerCliente:
    def __init__(self, banca_inicial, logger: TradingLoggerCliente, meta_diaria_percent=2.0, take_profit_meta_percent=10.0):
        self.logger = logger
        self.banca_inicial = float(banca_inicial)
        self.banca_atual = float(banca_inicial)
        self.entry_price = None
        self.entry_quantity = None
        self.current_symbol = None
        self.position_active = False
        self.daily_target_reached = False
        self.last_reset_date = datetime.now().date()

        # Limites dinâmicos que serão herdados do sinal do Mestre
        self.stop_loss_limit = 4.0  # Convertido para valor positivo padrão para cálculo absoluto
        self.take_profit_limit = 2.0
        self.meta_diaria_percent = float(meta_diaria_percent)
        self.take_profit_meta_percent = float(take_profit_meta_percent)

        # Garante a criação da raiz /app antes de tentar carregar ou persistir os dados
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Recupera o estado em disco caso o container sofra um reboot na VPS
        self._load_state()

    def set_entry(self, symbol, price, quantity, sl=4.0, tp=2.0):
        """Define a entrada forçando os limites a serem tratados de forma absoluta."""
        self.current_symbol = symbol
        self.entry_price = float(price)
        self.entry_quantity = float(quantity)
        
        # Garante que os limites sejam armazenados como números positivos para cálculo absoluto seguro
        self.stop_loss_limit = abs(float(sl)) if sl is not None else 4.0
        self.take_profit_limit = abs(float(tp)) if tp is not None else 2.0
        self.position_active = True
        self._persist()
        self.logger.log_info(f"✅ [RISK MANAGER] Posição aberta para {symbol}. SL: {self.stop_loss_limit}%, TP: {self.take_profit_limit}%")

    def clear_position(self):
        """Limpa o registro de posições e atualiza a persistência local."""
        self.current_symbol = None
        self.entry_price = None
        self.entry_quantity = None
        self.position_active = False
        self._persist()
        self.logger.log_info("✅ [RISK MANAGER] Posição encerrada.")

    def atualizar_banca(self, nova_banca):
        """Atualiza o saldo atual da conta do cliente e força a gravação no JSON do dashboard."""
        self.banca_atual = float(nova_banca)
        self._persist()
        self.logger.log_info(f"💰 [RISK MANAGER] Banca atualizada para: {self.banca_atual:.2f} USDT")

    def check_stop_loss(self, current_price):
        """Verificação de Stop Loss usando cálculo absoluto para evitar falhas de sinal (+/-)."""
        if not self.position_active or self.entry_price is None:
            return False, 0.0

        # Calcula a variação percentual bruta
        pct = ((float(current_price) - self.entry_price) / self.entry_price) * 100
        
        # Se a variação for de queda (negativa) e a queda absoluta for maior ou igual ao limite, stopa!
        if pct < 0 and abs(pct) >= self.stop_loss_limit:
            self.logger.log_warning(f"🛑 [RISK MANAGER] Stop Loss acionado! Perda: {pct:.2f}% (Limite: {self.stop_loss_limit}%)")
            return True, round(pct, 2)
        return False, round(pct, 2)

    def check_take_profit(self, current_price):
        """Verificação dupla de Take Profit: por variação gráfica percentual ou ganho bruto USDT."""
        if not self.position_active or self.entry_price is None or self.entry_quantity is None:
            return False, 0.0

        pct = ((float(current_price) - self.entry_price) / self.entry_price) * 100
        lucro_usdt = (float(current_price) - self.entry_price) * self.entry_quantity
        alvo_usdt = self.get_meta_diaria() * (self.take_profit_meta_percent / 100.0)

        # Dispara saída se atingir a meta percentual do mestre OU bater o financeiro alvo do cliente
        if pct >= self.take_profit_limit or lucro_usdt >= alvo_usdt:
            self.logger.log_info(f"💰 [RISK MANAGER] Take Profit acionado! Lucro: {pct:.2f}% ou {lucro_usdt:.2f} USDT")
            return True, round(lucro_usdt, 2)
        return False, round(lucro_usdt, 2)

    def get_meta_diaria(self):
        # CORREÇÃO #3: Adicionado travas decimais matemáticas contra estouros de dízimas flutuantes
        return round(self.banca_inicial * (self.meta_diaria_percent / 100.0), 2)

    def get_ganho_atual(self):
        return round(self.banca_atual - self.banca_inicial, 2)

    def get_percentual_ganho(self):
        if self.banca_inicial == 0: 
            return 0.0
        return round((self.get_ganho_atual() / self.banca_inicial) * 100.0, 2)

    def pode_operar_hoje(self):
        """Gerencia o reset de metas diárias de forma segura, protegendo posições abertas."""
        hoje = datetime.now().date()
        if self.last_reset_date != hoje:
            # Trava de segurança: só redefine a banca inicial se o cliente não estiver posicionado
            if not self.position_active:
                self.daily_target_reached = False
                self.banca_inicial = self.banca_atual
                self.last_reset_date = hoje
                self._persist()
                self.logger.log_info(f"🔄 [RISK MANAGER] Reset diário de metas. Nova banca inicial: {self.banca_inicial:.2f} USDT")
            else:
                self.logger.log_warning("⚠ [RISK MANAGER] Reset diário adiado: Posição ativa detectada.")

        if self.get_ganho_atual() >= self.get_meta_diaria():
            if not self.daily_target_reached:
                self.daily_target_reached = True
                self.logger.log_meta_atingida(self.get_ganho_atual(), self.get_percentual_ganho())
        return not self.daily_target_reached

    def _persist(self):
        """Grava as métricas em tempo real em arquivo físico de forma thread-safe para o Dashboard."""
        # CORREÇÃO #1: Uso obrigatório do Lock compartilhado para impedir quebra do JSON pelo Flask
        with file_lock:
            try:
                state = {
                    "position_active": self.position_active,
                    "current_symbol": self.current_symbol,
                    "entry_price": self.entry_price,
                    "entry_quantity": self.entry_quantity,
                    "banca_inicial": self.banca_inicial,
                    "banca_atual": self.banca_atual,
                    "ganho_dia": self.get_ganho_atual(),
                    "stop_loss_percent": self.stop_loss_limit,
                    "take_profit_percent": self.take_profit_limit,
                    "daily_target_reached": self.daily_target_reached,
                    "last_reset_date": str(self.last_reset_date),
                    "updated_at": datetime.now().isoformat()
                }
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=4, ensure_ascii=False)
            except Exception as e:
                self.logger.log_error(f"❌ Erro ao salvar estado persistente do cliente: {e}")

    def _load_state(self):
        """Recupera os dados de sessão do disco de forma thread-safe e automática."""
        if not STATE_FILE.exists():
            self.logger.log_info("ℹ [RISK MANAGER] Arquivo de estado não encontrado. Iniciando com estado padrão.")
            return

        with file_lock:
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.position_active = state.get("position_active", False)
                self.current_symbol = state.get("current_symbol")
                self.entry_price = state.get("entry_price")
                self.entry_quantity = state.get("entry_quantity")
                self.banca_inicial = float(state.get("banca_inicial", self.banca_inicial))
                self.banca_atual = float(state.get("banca_atual", self.banca_atual))
                self.daily_target_reached = state.get("daily_target_reached", False)
                if state.get("last_reset_date"):
                    self.last_reset_date = datetime.strptime(state["last_reset_date"], "%Y-%m-%d").date()
                self.logger.log_info("✅ [RISK MANAGER] Estado persistente carregado com sucesso.")
            except Exception as e:
                self.logger.log_error(f"⚠ Falha ao ler arquivo de estado do cliente: {e}")
