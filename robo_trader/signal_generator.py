import os
import json
from datetime import datetime, timezone
from supabase import create_client

class SignalGenerator:
    def __init__(self):
        # Inicializa a conexão lendo diretamente das Variáveis de Ambiente da Stack do Portainer
        try:
            supabase_url = os.getenv("SUPABASE_URL", "https://mandacarurn.com.br")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_key:
                print("⚠️ AVISO: SUPABASE_KEY não encontrada nas variáveis de ambiente.")
                
            self.supabase = create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"❌ Erro crítico ao conectar no Supabase via Nuvem: {e}")

    def generate_signal(self, operation_type, quantity, price, symbol, status="new", stop_loss=None, take_profit=None):
        """
        Gera e envia o sinal de trade para o Supabase.
        Ajustado para suportar status (new/closed), valores de saída e carimbo de hora.
        """
        try:
            # Lógica para garantir que valores numéricos não sejam nulos
            sl_value = float(stop_loss) if stop_loss is not None else float(price * 0.98)
            tp_value = float(take_profit) if take_profit is not None else float(price * 1.02)

            # Carimbo de data e hora com fuso horário explícito (Padrão ISO aceito pelo Supabase)
            horario_atual = datetime.now(timezone.utc).isoformat()

            data = {
                "operation_type": operation_type,
                "symbol": symbol,
                "price": float(price),
                "quantity": float(quantity),
                "stop_loss": sl_value,
                "take_profit": tp_value,
                "status": status,
                "created_at": horario_atual  # Adicionado campo de tempo para o Copy Trader se guiar
            }

            # Envia para a tabela no Supabase de forma direta
            self.supabase.table("copy_signals").insert(data).execute()
            print(f"📡 Sinal de {operation_type} [{status}] para {symbol} enviado com sucesso ao Supabase!")

        except Exception as e:
            print(f"❌ Erro ao gerar/enviar sinal para o Supabase: {e}")
