import os
from datetime import datetime
from pathlib import Path
import logging

class TradingLoggerCliente:
    def __init__(self, name="TradingLoggerCliente"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Garante que o diretório de logs exista
        log_dir = Path("/app/logs") # Caminho fixo dentro do container
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configura o FileHandler para o arquivo de log do cliente
        log_file_path = log_dir / "trading_logs_cliente.txt"
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.INFO)

        # Configura o StreamHandler para o console
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)

        # Formato do log
        formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        # Adiciona os handlers ao logger, evitando duplicatas
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(stream_handler)

    def log_info(self, message):
        self.logger.info(message)

    def log_warning(self, message):
        self.logger.warning(message)

    def log_error(self, message):
        self.logger.error(message)

    def log_stop(self, message, loss_percent):
        # Exemplo de log customizado para stop loss
        self.logger.critical(f"🚨🚨🚨 STOP LOSS: {message} | Perda: {loss_percent:.2f}% 🚨🚨🚨")

    def log_profit(self, message, profit_percent):
        # Exemplo de log customizado para take profit
        self.logger.critical(f"💰💰💰 TAKE PROFIT: {message} | Lucro: {profit_percent:.2f}% 💰💰💰")

    def log_meta_atingida(self, ganho_usdt, ganho_percent):
        self.logger.critical(f"🎯🎯🎯 META DIÁRIA ATINGIDA: Ganho: +{ganho_usdt:.2f} USDT (+{ganho_percent:.2f}%) 🎯🎯🎯")
