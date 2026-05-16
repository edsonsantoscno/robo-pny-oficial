import json
from datetime import datetime
from supabase import create_client

# CONFIGURAÇÃO DIRETA PARA DESTRAVAR O TESTE LOCAL NO WINDOWS
SUPABASE_URL = "https://base.mandacarurn.com.br"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3MTUwNTA4MDAsCiAgImV4cCI6IDE4NzI4MTcyMDAKfQ.QyAbsAIda4o4-BINI9l9i2wvJ0r9gjP4vlvZlRiggFk"

class SignalGenerator:
    def __init__(self):
        try:
            # Conecta diretamente usando as variáveis acima
            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"❌ Erro ao conectar no Supabase: {e}")

    def generate_signal(self, operation_type, quantity, price, symbol, status="new", stop_loss=None, take_profit=None):
        """Gera e envia o sinal de trade para o Supabase."""
        try:
            sl_value = float(stop_loss) if stop_loss is not None else float(price * 0.98)
            tp_value = float(take_profit) if take_profit is not None else float(price * 1.02)

            data = {
                "operation_type": operation_type,
                "symbol": symbol,
                "price": float(price),
                "quantity": float(quantity),
                "stop_loss": sl_value,
                "take_profit": tp_value,
                "status": status
            }

            self.supabase.table("copy_signals").insert(data).execute()
            print(f"📡 Sinal de {operation_type} [{status}] para {symbol} enviado ao Supabase!")

        except Exception as e:
            print(f"❌ Erro ao gerar/enviar sinal para o Supabase: {e}")
