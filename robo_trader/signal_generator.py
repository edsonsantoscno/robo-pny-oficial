import json
from datetime import datetime
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

class SignalGenerator:
    def __init__(self):
        # Inicializa a conexão com o Supabase
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"❌ Erro ao conectar no Supabase: {e}")

    def generate_signal(self, operation_type, quantity, price, symbol, status="new", stop_loss=None, take_profit=None):
        """
        Gera e envia o sinal de trade para o Supabase.
        Ajustado para suportar status (new/closed) e valores de saída.
        """
        try:
            # Lógica para garantir que valores numéricos não sejam nulos
            # Se não vier do bot, define um padrão baseado no preço atual
            sl_value = float(stop_loss) if stop_loss is not None else float(price * 0.98)
            tp_value = float(take_profit) if take_profit is not None else float(price * 1.02)

            data = {
                "operation_type": operation_type,
                "symbol": symbol,
                "price": float(price),
                "quantity": float(quantity),
                "stop_loss": sl_value,
                "take_profit": tp_value,
                "status": status,
                #"updated_at": datetime.utcnow().isoformat()
            }

            # Envia para a tabela no Supabase
            # Nota: .insert() cria uma nova linha. 
            # Se sua tabela exigir atualização de linha existente, use .upsert()
            self.supabase.table("copy_signals").insert(data).execute()
            
            print(f"📡 Sinal de {operation_type} [{status}] para {symbol} enviado ao Supabase!")

        except Exception as e:
            print(f"❌ Erro ao gerar/enviar sinal para o Supabase: {e}")
