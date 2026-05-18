import os
from datetime import datetime
from pathlib import Path

class TradingLoggerCliente:
    def __init__(self, log_file=None):
        # Garante o caminho absoluto e unificado na raiz do container do Docker do cliente
        if log_file:
            self.log_file = Path(log_file)
        else:
            # Puxa o caminho padrão via Variável de Ambiente ou fixa na raiz do módulo cliente
            # Ajustado para o novo volume mapeado: /app/logs/
            log_default = os.getenv("LOG_FILE", "trading_logs_cliente.txt")
            self.log_file = Path("/app/logs") / log_default # <-- CORREÇÃO AQUI

        # Garante que o diretório de logs exista
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _write_log(self, message):
        """Método interno para escrever no arquivo de log e imprimir no console"""
        print(message)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(message + "\n")
                f.flush() # Evita o bloqueio de arquivo (File Locking) no Portainer Swarm
        except Exception as e:
            print(f"❌ Erro crítico ao escrever log: {e}")

    def info(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write_log(f"[{timestamp}] INFO | {message}")

    def warning(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write_log(f"[{timestamp}] WARNING | {message}")

    def error(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write_log(f"[{timestamp}] ERROR | {message}")

    def log_entry(self, operation_type, symbol, quantity, price, reason=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Conversões estritas e seguras contra falhas de tipagem da API
        try:
            qty_val = float(quantity)
            price_val = float(price)
            notional_val = qty_val * price_val
        except (ValueError, TypeError):
            qty_val, price_val, notional_val = 0.0, 0.0, 0.0

        message = f"[{timestamp}] {operation_type.upper()} | {symbol} | Qtd: {qty_val:.8f} | Preço: {price_val:.4f} USDT | Notional: {notional_val:.2f} USDT"

        if reason:
            message += f" | {reason}"

        self._write_log(message)

    def log_stop(self, reason, loss_percent):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            loss_val = float(loss_percent)
        except (ValueError, TypeError):
            loss_val = 0.0

        message = f"[{timestamp}] PARADO | {reason} | Perda: {loss_val:.2f}%"

        self._write_log(message)

    def log_meta_atingida(self, ganho_usdt, ganho_percent):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            ganho_val = float(ganho_usdt)
            pct_val = float(ganho_percent)
        except (ValueError, TypeError):
            ganho_val, pct_val = 0.0, 0.0

        message = f"[{timestamp}] META DIÁRIA ATINGIDA | Ganho: +{ganho_val:.2f} USDT (+{pct_val:.2f}%)"

        self._write_log(message)
