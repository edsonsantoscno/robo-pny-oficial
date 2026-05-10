from state_manager import save_state, load_state
from config import STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT, META_DIARIA_PERCENT

class RiskManager:
    def __init__(self, banca_inicial, take_profit_meta_percent=0.5):
        self.banca_inicial = banca_inicial
        self.banca_atual = banca_inicial
        self.take_profit_meta_percent = take_profit_meta_percent
        self.daily_target_reached = False
        
        # Variáveis de posição (Agora com current_symbol)
        self.position_active = False
        self.current_symbol = None
        self.entry_price = None
        self.entry_quantity = None

        state = load_state()
        if state:
            self.position_active = state.get("position_active", False)
            self.current_symbol = state.get("current_symbol") # NOVIDADE
            self.entry_price = state.get("entry_price")
            self.entry_quantity = state.get("entry_quantity")
            self.banca_inicial = state.get("banca_inicial", banca_inicial)

    def set_entry(self, symbol, price, quantity):
        """Registra a entrada salvando qual moeda foi comprada"""
        self.position_active = True
        self.current_symbol = symbol
        self.entry_price = price
        self.entry_quantity = quantity
        self._persist()

    def clear_position(self):
        """Limpa a posição e o símbolo atual"""
        self.position_active = False
        self.current_symbol = None
        self.entry_price = None
        self.entry_quantity = None
        self._persist()

    def atualizar_banca(self, valor): 
        self.banca_atual = valor

    def get_ganho_atual(self): 
        return self.banca_atual - self.banca_inicial

    def get_percentual_ganho(self): 
        return (self.get_ganho_atual() / self.banca_inicial) * 100

    def get_meta_diaria(self): 
        # Usa o valor configurado no config.py (ex: 5%)
        return self.banca_inicial * (META_DIARIA_PERCENT / 100)

    def pode_operar_hoje(self): 
        return self.get_ganho_atual() < self.get_meta_diaria()

    def get_take_profit_usdt(self): 
        return self.get_meta_diaria() * self.take_profit_meta_percent

    def check_stop_loss(self, price):
        if not self.position_active: return False, 0.0
        pct = ((price - self.entry_price) / self.entry_price) * 100
        return pct <= -STOP_LOSS_PERCENT, pct

    def check_take_profit(self, price):
        if not self.position_active: return False, 0.0
        lucro_usdt = (price - self.entry_price) * self.entry_quantity
        pct = ((price - self.entry_price) / self.entry_price) * 100
        # Sai se atingir lucro em USDT ou a porcentagem alvo
        return (lucro_usdt >= self.get_take_profit_usdt() or pct >= TAKE_PROFIT_PERCENT), lucro_usdt

    def _persist(self):
        save_state(
            self.position_active, 
            self.entry_price, 
            self.entry_quantity, 
            self.banca_inicial, 
            self.get_ganho_atual(),
            self.current_symbol # Salva o símbolo no JSON
        )
