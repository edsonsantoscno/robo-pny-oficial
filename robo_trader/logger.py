from datetime import datetime
from config import LOG_FILE

class TradingLogger:
    def __init__(self, log_file=LOG_FILE):
        self.log_file = log_file

    def log_entry(self, operation_type, symbol, quantity, price, notional, reason=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = f"[{timestamp}] {operation_type.upper()} | {symbol} | Qtd: {quantity:.8f} | Preço: {price:.2f} USDT | Notional: {notional:.2f} USDT"

        if reason:
            message += f" | {reason}"

        print(message)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception as e:
            print(f"❌ Erro ao escrever log: {e}")

    def log_stop(self, reason, loss_percent):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{timestamp}] PARADO | {reason} | Perda: {loss_percent:.2f}%"

        print(message)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception as e:
            print(f"❌ Erro ao escrever log: {e}")

    def log_meta_atingida(self, ganho_usdt, ganho_percent):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{timestamp}] META DIÁRIA ATINGIDA | Ganho: +{ganho_usdt:.2f} USDT (+{ganho_percent:.2f}%)"

        print(message)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception as e:
            print(f"❌ Erro ao escrever log: {e}")