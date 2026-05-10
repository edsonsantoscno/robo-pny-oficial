from signal_generator import SignalGenerator
import time

def testar_conexao_supabase():
    print("🚀 Iniciando teste de envio para o Supabase...")
    
    try:
        # Inicializa o gerador de sinais
        sg = SignalGenerator()
        
        # Dados de teste (Simulando uma compra de SOL)
        simbol = "SOLUSDT"
        preco_teste = 93.50
        quantidade_teste = 1.5
        
        print(f"📡 Enviando sinal de TESTE para {simbol}...")
        
        # Chama a função exatamente como o robô faz
        sg.generate_signal(
            operation_type="BUY",
            quantity=quantidade_teste,
            price=preco_teste,
            symbol=simbol,
            status="testing", # Status especial para você identificar no painel
            stop_loss=90.00,
            take_profit=98.00
        )
        
        print("\n✅ COMANDO EXECUTADO! Verifique seu painel no Supabase.")
        print("Procure por uma linha com status 'testing'.")

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")

if __name__ == "__main__":
    testar_conexao_supabase()
