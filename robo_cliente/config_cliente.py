root@Mandakarun:~/robo-pny-oficial# import os
from pathlib import Path

# ============ CONFIGURAÇÕES DE DIRETÓRIOS E ARQUIVOS NO DOCKER ============
BASE_DIR = Path("/app")

# Arquivos de comunicação compartilhados via volumes do Docker Compose
LOG_FILE = BASE_DIR / "trading_logs_cliente.txt"
SIGNALS_FILE = BASE_DIR / "signals.json"

# ============ SEGURANÇA: VARIÁVEIS DE AMBIENTE DA VPS/PORTAINER ============
API_KEY_CLIENTE = os.getenv("KEY_BINANCE") or os.getenv("API_KEY")
SECRET_KEY_CLIENTE = os.getenv("SECRET_BINANCE") or os.getenv("API_SECRET")

# Apontando estritamente para o subdomínio correto do seu Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://supabase.mandacarurn.com.br")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ============ CONFIGURAÇÕES DE IDENTIDADE DO SAAS ============
CLIENTE_NOME = os.getenv("CLIENTE_NOME", "Cliente Oficial 1")
QUOTE_ASSET = "USDT"

# ============ PARÂMETROS OPERACIONAIS DE CÓPIA PROPORCIONAL ============
QUANTIDADE_PERCENTUAL = 1.0

# ============ METAS E TRAVAS DE RISCO COMERCIAL ============
META_DIARIA_PERCENT = 2.0        
TAKE_PROFIT_META_PERCENT = 10.0  
COPY_TRADER_ATIVO = True
BANCA_INICIAL = 199.44

# ============ CONFIGURAÇÕES DE WEBSOCKET FIXADAS COM ERRO ZERO ============
WEBSOCKET_PORT = int(os.getenv("WS_PORT", 6001))-server")orreto na porta 6001
import-im6.q16: unable to open X server `' @ error/import.c/ImportImageCommand/346.
Command 'from' not found, but can be installed with:
apt install mailutils
-bash: syntax error near unexpected token `('
LOG_FILE: command not found
SIGNALS_FILE: command not found
-bash: syntax error near unexpected token `('
-bash: syntax error near unexpected token `('
-bash: syntax error near unexpected token `('
-bash: syntax error near unexpected token `('
-bash: syntax error near unexpected token `('
QUOTE_ASSET: command not found
QUANTIDADE_PERCENTUAL: command not found
META_DIARIA_PERCENT: command not found
TAKE_PROFIT_META_PERCENT: command not found
COPY_TRADER_ATIVO: command not found
BANCA_INICIAL: command not found
-bash: syntax error near unexpected token `('
-bash: syntax error near unexpected token `('
root@Mandakarun:~/robo-pny-oficial# 
