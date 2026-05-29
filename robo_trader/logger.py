import os
import threading
from datetime import datetime
from pathlib import Path

# CORREÇÃO #2: Mecanismo Global de Trava (Lock) para evitar colisões de I/O com o Dashboard
log_lock = threading.Lock()

class TradingLogger:
    def __init__(self, log_file=None):
        """
        Garante o caminho absoluto e unificado na raiz do container do Docker.
        Sincronizado perfeitamente com os volumes mapeados no docker-compose.yml.
        """
        # CORREÇÃO #1: Ajustado para apontar para a raiz /app do contêiner Docker
        if log_file:
            self.log_file = Path(log_file)
        else:
            log_default = os.getenv("LOG_FILE", "/app/trading_logs_trader.txt")
            self.log_file = Path(log_default)

    def _write_to_disk(self, message: str):
        """Método auxiliar thread-safe para persistir strings e limpar o buffer."""
        print(message)
        with log_lock:
            try:
                # Garante a criação do diretório pai caso não exista na VPS
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(message + "\n")
                    f.flush()  # Evita o bloqueio de arquivo (File Locking) no Portainer
            except Exception as e:
                print(f"❌ Erro crítico ao escrever em disco no arquivo de logs: {e}")

    def log_entry(self, operation_type, symbol, quantity, price, notional, reason=""):
        """Formata e registra as ordens de compra e venda abertas pelo robô mestre."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Conversões seguras contra falhas de tipagem vindas da API da Binance
        try:
            qty_val = float(quantity)
            price_val = float(price)
            notional_val = float(notional)
        except (ValueError, TypeError):
            qty_val, price_val, notional_val = 0.0, 0.0, 0.0

        message = f"[{timestamp}] {operation_type.upper()} | {symbol} | Qtd: {qty_val:.8f} | Preço: {price_val:.4f} USDT | Notional: {notional_val:.2f} USDT"
        
        if reason:
            message += f" | {reason}"
            
        self._write_to_disk(message)

    def log_stop(self, reason, loss_percent):
        """Registra no terminal os eventos de acionamento de Stop Loss."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            loss_val = float(loss_percent)
        except (ValueError, TypeError):
            loss_val = 0.0

        message = f"[{timestamp}] PARADO | {reason} | Perda: {loss_val:.2f}%"
        self._write_to_disk(message)

    def log_meta_atingida(self, ganho_usdt, ganho_percent):
        """Registra as saídas por atingimento de meta diária configurada."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            ganho_val = float(ganho_usdt)
            pct_val = float(ganho_percent)
        except (ValueError, TypeError):
            ganho_val, pct_val = 0.0, 0.0

        message = f"[{timestamp}] META DIÁRIA ATINGIDA | Ganho: +{ganho_val:.2f} USDT (+{pct_val:.2f}%)"
        self._write_to_disk(message)
