import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Força o Python a encontrar o arquivo .env na raiz do projeto
raiz_do_projeto = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=raiz_do_projeto / '.env')

# Puxa as credenciais diretamente do ambiente carregado
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://base.mandacarurn.com.br")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3MTUwNTA4MDAsCiAgImV4cCI6IDE4NzI4MTcyMDAKfQ.QyAbsAIda4o4-BINI9l9i2wvJ0r9gjP4vlvZlRiggFk")

def testar():
    if not SUPABASE_KEY or "OCULTADA" in SUPABASE_KEY:
        print("❌ FALHA: A SUPABASE_KEY não foi encontrada no arquivo .env ou está incorreta.")
        return

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Tenta inserir um sinal de teste
        data = {
            "operation_type": "TESTE",
            "symbol": "BTCUSDT",
            "price": 1.0,
            "quantity": 1.0,
            "status": "new"
        }
        res = supabase.table("copy_signals").insert(data).execute()
        print("✅ SUCESSO! O Supabase aceitou a conexão e gravou o sinal.")
    except Exception as e:
        print(f"❌ FALHA: {e}")

if __name__ == "__main__":
    testar()
