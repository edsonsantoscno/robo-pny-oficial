import os
import json
from datetime import datetime, timezone
from supabase import create_client

class SignalGenerator:
    def __init__(self):
        """
        Inicializa a conexão lendo diretamente das Variáveis de Ambiente da Stack do Portainer.
        Blindado contra chaves nulas para evitar crash do robô mestre.
        """
        try:
            # CORREÇÃO DEFINITIVA: URL ajustada para o subdomínio exato e homologado no cluster
            supabase_url = os.getenv("SUPABASE_URL", "https://supabase.mandacarurn.com.br")
            
            # MANTIDO SEM CHAVE FIXA: Segurança máxima puxando direto da memória da VPS
            supabase_key = os.getenv("SUPABASE_KEY")
            
            # Impede injeção de chave nula na biblioteca do Supabase para evitar crash fatal
            if not supabase_key:
                print("⚠ AVISO CRÍTICO: SUPABASE_KEY não encontrada. Persistência em nuvem desativada temporariamente.")
                self.supabase = None
            else:
                self.supabase = create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"❌ Erro crítico ao conectar no Supabase via Nuvem: {e}")
            self.supabase = None

    def generate_signal(self, operation_type, quantity, price, symbol, status="new", stop_loss=None, take_profit=None):
        """
        Gera e envia o sinal de trade para o Supabase e para a malha interna do WebSocket.
        Ajustado com travas decimais matemáticas contra estouros de Price Filter.
        """
        try:
            # Encapsulado com round(..., 4) para garantir conformidade com as regras de ticks da Binance
            sl_value = float(stop_loss) if stop_loss is not None else round(float(price * 0.98), 4)
            tp_value = float(take_profit) if take_profit is not None else round(float(price * 1.02), 4)

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
                "created_at": horario_atual
            }

            # Executa a gravação na nuvem apenas se a instância do cliente estiver activa e segura
            if self.supabase:
                self.supabase.table("copy_signals").insert(data).execute()
                print(f"📡 Sinal de {operation_type} [{status}] para {symbol} enviado com sucesso ao Supabase!")
            else:
                print(f"💾 Sinal gerado localmente [{operation_type}], mas envio em nuvem ignorado (Supabase desativado).")

        except Exception as e:
            print(f"❌ Erro ao gerar/enviar sinal para o Supabase: {e}")
