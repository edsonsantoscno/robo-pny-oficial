from datetime import datetime

class RiskManagerCliente:
    def __init__(self, banca_inicial, meta_diaria_percent=2.0, take_profit_meta_percent=10.0):
        self.banca_inicial = banca_inicial
        self.banca_atual = banca_inicial
        self.entry_price = None
        self.entry_quantity = None
        self.current_symbol = None # Adicionado para identificar o ativo
        self.position_active = False
        self.daily_target_reached = False
        self.last_reset_date = datetime.now().date()
        
        # Parâmetros de risco dinâmicos (virão do sinal do mestre)
        self.stop_loss_limit = -1.0 
        self.take_profit_limit = 1.5
        
        self.meta_diaria_percent = meta_diaria_percent
        self.take_profit_meta_percent = take_profit_meta_percent

    def set_entry(self, symbol, price, quantity, sl=-1.0, tp=1.5):
        """Define a entrada baseada nos limites enviados pelo Mestre"""
        self.current_symbol = symbol
        self.entry_price = price
        self.entry_quantity = quantity
        self.stop_loss_limit = sl
        self.take_profit_limit = tp
        self.position_active = True

    def clear_position(self): # Nome padronizado com o Mestre
        self.current_symbol = None
        self.entry_price = None
        self.entry_quantity = None
        self.position_active = False

    def atualizar_banca(self, nova_banca):
        self.banca_atual = nova_banca

    def check_stop_loss(self, current_price):
        if not self.position_active or self.entry_price is None:
            return False, 0.0
        pct = ((current_price - self.entry_price) / self.entry_price) * 100
        # Usa o limite de stop que veio no sinal do mestre
        if pct <= self.stop_loss_limit:
            return True, pct
        return False, pct

    def check_take_profit(self, current_price):
        if not self.position_active or self.entry_price is None:
            return False, 0.0
        
        pct = ((current_price - self.entry_price) / self.entry_price) * 100
        lucro_usdt = (current_price - self.entry_price) * self.entry_quantity
        alvo_usdt = self.get_meta_diaria() * (self.take_profit_meta_percent / 100)

        # O cliente sai se bater o lucro em USDT ou a porcentagem enviada pelo mestre
        if pct >= self.take_profit_limit or lucro_usdt >= alvo_usdt:
            return True, lucro_usdt
        return False, lucro_usdt

    def get_meta_diaria(self):
        return self.banca_inicial * (self.meta_diaria_percent / 100)

    def get_ganho_atual(self):
        return self.banca_atual - self.banca_inicial

    def get_percentual_ganho(self):
        if self.banca_inicial == 0: return 0.0
        return ((self.banca_atual - self.banca_inicial) / self.banca_inicial) * 100

    def pode_operar_hoje(self):
        # Lógica de reset diário simplificada
        if self.last_reset_date != datetime.now().date():
            self.daily_target_reached = False
            self.banca_inicial = self.banca_atual
            self.last_reset_date = datetime.now().date()
        
        return not self.daily_target_reached and self.get_ganho_atual() < self.get_meta_diaria()
