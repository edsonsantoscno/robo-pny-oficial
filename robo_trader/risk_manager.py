import round
from state_manager import save_state, load_state
from config import STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT, META_DIARIA_PERCENT

class RiskManager:
    def __init__(self, banca_inicial, take_profit_meta_percent=0.5):
        self.banca_inicial = float(banca_inicial)
        self.banca_atual = float(banca_inicial)
        self.take_profit_meta_percent = float(take_profit_meta_percent)
        self.daily_target_reached = False

        # Variáveis de posição (Sincronizadas com o Dashboard)
        self.position_active = False
        self.current_symbol = None
        self.entry_price = None
        self.entry_quantity = None

        state = load_state()
        if state:
            self.position_active = state.get("position_active", False)
            self.current_symbol = state.get("current_symbol")
            self.entry_price = float(state["entry_price"]) if state.get("entry_price") else None
            # CORREÇÃO #1: Garante a captura segura da quantidade de entrada persistida no arquivo unificado
            self.entry_quantity = float(state["entry_quantity"]) if state.get("entry_quantity") else None
            self.banca_inicial = float(state.get("banca_inicial", banca_inicial))
            self.banca_atual = float(state.get("banca_atual", banca_inicial))

    def set_entry(self, symbol, price, quantity):
        """Registra a entrada salvando qual moeda foi comprada"""
        self.position_active = True
        self.current_symbol = symbol
        self.entry_price = float(price)
        self.entry_quantity = float(quantity)
        self._persist()

    def clear_position(self):
        """Limpa a posição e o símbolo atual após a venda de forma atômica"""
        self.position_active = False
        self.current_symbol = None
        self.entry_price = None
        self.entry_quantity = None
        self._persist()

    def atualizar_banca(self, valor):
        """Atualiza a carteira forçando a gravação imediata do ganho flutuante"""
        self.banca_atual = float(valor)
        self._persist()
    def get_ganho_atual(self):
        # CORREÇÃO #3: Arredondamento contínuo para evitar dízimas flutuantes do Python nas contas
        return round(self.banca_atual - self.banca_inicial, 2)

    def get_percentual_ganho(self):
        if self.banca_inicial == 0: return 0.0
        return round((self.get_ganho_atual() / self.banca_inicial) * 100, 2)

    def get_meta_diaria(self):
        return round(self.banca_inicial * (META_DIARIA_PERCENT / 100), 2)

    def pode_operar_hoje(self):
        # CORREÇÃO #2: Impede que micro-centavos bloqueiem ou liberem ordens indevidamente
        return self.get_ganho_atual() < self.get_meta_diaria()

    def get_take_profit_usdt(self):
        return round(self.get_meta_diaria() * self.take_profit_meta_percent, 2)

    def check_stop_loss(self, price):
        if not self.position_active or not self.entry_price: 
            return False, 0.0
        pct = ((price - self.entry_price) / self.entry_price) * 100
        return pct <= -STOP_LOSS_PERCENT, round(pct, 2)

    def check_take_profit(self, price):
        if not self.position_active or not self.entry_price or not self.entry_quantity:
            return False, 0.0
        lucro_usdt = (price - self.entry_price) * self.entry_quantity
        pct = ((price - self.entry_price) / self.entry_price) * 100
        
        # Validação cruzada: Alvo batido por valor nominal em dólares ou por taxa percentual fixada
        alvo_atingido = (lucro_usdt >= self.get_take_profit_usdt() or pct >= TAKE_PROFIT_PERCENT)
        return alvo_atingido, round(lucro_usdt, 2)

    def _persist(self):
        """Salva com segurança os estados contábeis e de risco para sincronizar com o dashboard"""
        try:
            save_state(
                position_active=self.position_active,
                entry_price=self.entry_price,
                entry_quantity=self.entry_quantity,
                banca_inicial=self.banca_inicial,
                ganho_dia=self.get_ganho_atual(), # Chave mapeada lida pelo app.py do painel web
                current_symbol=self.current_symbol,
                banca_atual=self.banca_atual
            )
        except TypeError:
            # Mecanismo de fallback caso sua biblioteca state_manager exija arrays puramente posicionais
            save_state(
                self.position_active,
                self.entry_price,
                self.entry_quantity,
                self.banca_inicial,
                self.get_ganho_atual(),
                self.current_symbol
            )
