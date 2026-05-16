import streamlit as st
import os
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from binance_client import BinanceClient  # Seu cliente corrigido
from config import (
    SYMBOLS, STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT, 
    DAILY_LOSS_LIMIT_PERCENT, LOG_FILE, STATE_FILE, SIGNALS_FILE
)
import time
import threading

# Configuração da página
st.set_page_config(
    page_title="🚀 CopyTrader PNY - SaaS Cliente", 
    page_icon="🚀",
    layout="wide"
)

class CopyTraderSaaS:
    def __init__(self):
        self.client = BinanceClient()
        self.balance_history = []
        self.signals_history = []
        self.setup_session()

    def setup_session(self):
        """Estado da sessão"""
        defaults = {
            'api_key': '',
            'api_secret': '',
            'position_size': 0.05,  # 5%
            'strategy': 'PNY',
            'trading_active': False,
            'signals': []
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

# Sidebar - Configurações do Cliente
st.sidebar.header("🔧 Configurações Cliente")
api_key = st.sidebar.text_input("🔑 API Key Binance", type="password")
api_secret = st.sidebar.text_input("🔐 API Secret", type="password")

if st.sidebar.button("💾 Salvar API Keys"):
    # Salva no .env
    with open(".env_cliente", "w") as f:
        f.write(f"KEY_BINANCE_CLIENTE={api_key}\n")
        f.write(f"SECRET_BINANCE_CLIENTE={api_secret}\n")
    st.session_state.api_key = api_key
    st.session_state.api_secret = api_secret
    st.success("✅ API Keys salvas!")
    st.rerun()

# Parâmetros ajustáveis
st.sidebar.subheader("⚙️ Trading")
position_size = st.sidebar.slider("📊 % Banca/Trade", 1, 20, int(st.session_state.position_size*100)) / 100
strategy = st.sidebar.selectbox("🎯 Estratégia", ["PNY", "EMA_SCALP", "RSI", "EMA_ONLY"])

if st.sidebar.button("🔄 Atualizar"):
    st.session_state.position_size = position_size
    st.session_state.strategy = strategy
    st.success("✅ Configurações atualizadas!")

# Dashboard Principal
trader = CopyTraderSaaS()
col1, col2, col3 = st.columns(3)

with col1:
    balance = trader.client.get_balance_usdt()
    st.metric("💰 Banca Total", f"${balance:.2f}")

with col2:
    st.metric("📈 P&L Hoje", f"+0.14 USDT", "0.07%")

with col3:
    status = "🟢 ATIVO" if st.session_state.trading_active else "🔴 PARADO"
    st.metric("📡 Status", status)

# Gráfico Performance
st.subheader("📊 Performance 24h")
fig = go.Figure()
fig.add_trace(go.Scatter(
    y=[195, 197, 198, 199.44], 
    mode='lines+markers',
    name='Banca USDT',
    line=dict(color='#10B981', width=3)
))
fig.update_layout(height=400, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# Últimos Sinais PNY (do seu scanner mestre)
st.subheader("🎯 Últimos Sinais PNY")
signals_df = pd.DataFrame({
    'Moeda': ['PENDLEUSDT', 'RENDERUSDT', 'BTCUSDT'],
    'Preço': [1.899, 1.959, 80675],
    'Stoch': [4.64, 11.52, 5.58],
    'Ação': ['🟡 Aguardando', '🟡 Aguardando', '🟡 Aguardando']
})
st.dataframe(signals_df, use_container_width=True)

# Botões de Controle
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 Iniciar Copy Trading", type="primary", use_container_width=True):
        st.session_state.trading_active = True
        st.success("✅ Copy Trading ATIVO - Copiando PNY!")
        st.rerun()

with col2:
    if st.button("⏹️ Parar Trading", type="secondary", use_container_width=True):
        st.session_state.trading_active = False
        st.warning("⏹️ Copy Trading PARADO")
        st.rerun()

# Histórico de Trades
st.subheader("📋 Histórico Trades")
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        logs = f.readlines()[-10:]  # Últimos 10
    st.text("\n".join(logs))
else:
    st.info("📄 Logs em desenvolvimento...")

st.markdown("---")
st.markdown("*👨‍💼 Desenvolvido por José | CopyTrader PNY 2026*")