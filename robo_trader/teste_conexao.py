from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

def testar():
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
