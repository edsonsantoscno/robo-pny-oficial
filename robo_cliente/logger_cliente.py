import os
import threading
from datetime import datetime
from pathlib import Path
import logging

# CORREÇÃO #2: Mecanismo de Trava Global (Lock) para impedir colisões de I/O com o Dashboard
log_lock = threading.Lock()

class TradingLoggerCliente:
    def __init__(self, name="TradingLoggerCliente"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # CORREÇÃO #1: Caminho absoluto e unificado na raiz /app conforme mapeado no docker-compose.yml
        self.log_file = Path("/app/trading_logs_cliente.txt")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configura o FileHandler para gravar diretamente na raiz do volume compartilhado
        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # Configura o StreamHandler para espelhar as informações no console do terminal Docker
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)

        # Formatação profissional limpa de strings de tempo e escopo
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        # Adiciona os handlers ao logger de forma segura evitando duplicações na RAM
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(stream_handler)

    def _write_safe(self, log_func, message):
        """Encapsula a execução de logs com trava e flush síncrono para garantir exibição imediata."""
        with log_lock:
            try:
                log_func(message)
                # Força a gravação imediata no disco para o app.py ler sem delay de buffer
                for handler in self.logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        handler.flush()
            except Exception as e:
                print(f"❌ Erro crítico no subsistema de telemetria do cliente: {e}")

    def log_info(self, message):
        self._write_safe(self.logger.info, message)

    def log_warning(self, message):
        self._write_safe(self.logger.warning, message)

    def log_error(self, message):
        self._write_safe(self.logger.error, message)

    def log_stop(self, message, loss_percent):
        """Garante a formatação absoluta e gravação imediata do Stop Loss acionado."""
        try:
            val = float(loss_percent)
        except (ValueError, TypeError):
            val = 0.0
        msg = f"🚨🚨🚨 STOP LOSS: {message} | Perda: {val:.2f}% 🚨🚨🚨"
        self._write_safe(self.logger.critical, msg)

    def log_profit(self, message, profit_percent):
        """Garante a formatação absoluta e gravação imediata do Take Profit acionado."""
        try:
            val = float(profit_percent)
        except (ValueError, TypeError):
            val = 0.0
        msg = f"💰💰💰 TAKE PROFIT: {message} | Lucro: {val:.2f}% 💰💰💰"
        self._write_safe(self.logger.critical, msg)

    def log_meta_atingida(self, ganho_usdt, ganho_percent):
        """Registra as saídas por atingimento de meta diária na subconta."""
        try:
            g_val = float(ganho_usdt)
            p_val = float(ganho_percent)
        except (ValueError, TypeError):
            g_val, p_val = 0.0, 0.0
        msg = f"🎯🎯🎯 META DIÁRIA ATINGIDA: Ganho: +{g_val:.2f} USDT (+{p_val:.2f}%) 🎯🎯🎯"
        self._write_safe(self.logger.critical, msg)
