import pandas as pd
import pandas_ta as ta
from config import (
    MODO_ESTRATEGIA, RSI_PERIOD, RSI_BUY_THRESHOLD, RSI_SELL_THRESHOLD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL, EMA_ONLY_PERIOD,
    EMA_ONLY_FAST, EMA_ONLY_SLOW, EMA_SCALPER_FAST, EMA_SCALPER_SLOW,
    PNY_BB_PERIOD, PNY_BB_STD, PNY_STOCH_K, PNY_STOCH_THRESHOLD_LOW, PNY_STOCH_THRESHOLD_HIGH
)

class AgressiveStrategy:
    def __init__(self, binance_client):
        self.client = binance_client

    def get_data(self, symbol, interval, limit=250):
        try:
            klines = self.client.get_klines(symbol, interval, limit=limit)
            if not klines: return None

            df = pd.DataFrame(klines, columns=[
                "open_time", "open", "high", "low", "close",
                "volume", "close_time", "quote_volume", "trades",
                "taker_buy_base", "taker_buy_quote", "ignore"
            ])

            # Conversão essencial para cálculos matemáticos
            df["close"] = pd.to_numeric(df["close"])
            df["high"] = pd.to_numeric(df["high"])
            df["low"] = pd.to_numeric(df["low"])
            df["volume"] = pd.to_numeric(df["volume"])
            return df
        except Exception as e:
            print(f"❌ Erro ao buscar dados: {e}")
            return None

    def calculate_signal(self, df):
        try:
            if df is None or len(df) < 50: return "HOLD"

            # --- 1. SINAL ORIGINAL (RSI + MACD) ---
            sig_original = "HOLD"
            rsi = ta.rsi(df['close'], length=RSI_PERIOD)
            macd = ta.macd(df['close'], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
            
            if rsi is not None and macd is not None and not rsi.empty:
                hist_col = f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
                curr_rsi = rsi.iloc[-1]
                curr_hist = macd[hist_col].iloc[-1]
                if curr_rsi <= RSI_BUY_THRESHOLD and curr_hist > 0:
                    sig_original = "BUY"
                elif curr_rsi >= RSI_SELL_THRESHOLD or (curr_hist < 0 and curr_rsi > 50):
                    sig_original = "SELL"

            # --- 2. SINAL EMA_ONLY (Cruzamento Moderado) ---
            sig_ema_only = "HOLD"
            ema_f = ta.ema(df['close'], length=EMA_ONLY_FAST)
            ema_s = ta.ema(df['close'], length=EMA_ONLY_SLOW)
            ema_l = ta.ema(df['close'], length=EMA_ONLY_PERIOD)
            if ema_f is not None and ema_s is not None and not ema_f.empty:
                if ema_f.iloc[-1] > ema_s.iloc[-1] and ema_f.iloc[-2] <= ema_s.iloc[-2] and df['close'].iloc[-1] > ema_l.iloc[-1]:
                    sig_ema_only = "BUY"
                elif (ema_f.iloc[-1] < ema_s.iloc[-1] and ema_f.iloc[-2] >= ema_s.iloc[-2]) or df['close'].iloc[-1] < ema_l.iloc[-1]:
                    sig_ema_only = "SELL"

            # --- 3. SINAL EMA_SCALPER (Agressivo) ---
            sig_ema_scalper = "HOLD"
            ema_fs = ta.ema(df['close'], length=EMA_SCALPER_FAST)
            ema_ss = ta.ema(df['close'], length=EMA_SCALPER_SLOW)
            if ema_fs is not None and ema_ss is not None and not ema_fs.empty:
                if ema_fs.iloc[-1] > ema_ss.iloc[-1] and ema_fs.iloc[-2] <= ema_ss.iloc[-2]:
                    sig_ema_scalper = "BUY"
                elif ema_fs.iloc[-1] < ema_ss.iloc[-1] and ema_fs.iloc[-2] >= ema_ss.iloc[-2]:
                    sig_ema_scalper = "SELL"

            # --- 4. SINAL PRÍNCIPE DE NY (Topo e Fundo) ---
            sig_pny = "HOLD"
            bb = ta.bbands(df['close'], length=PNY_BB_PERIOD, std=PNY_BB_STD)
            stoch = ta.stoch(df['high'], df['low'], df['close'], k=PNY_STOCH_K, d=3)
            
            stoch_val, l_band_val = 0.0, 0.0

            if bb is not None and not bb.empty and not stoch.empty:
                l_band = bb.iloc[:, 0].iloc[-1] # Banda Inferior
                u_band = bb.iloc[:, 2].iloc[-1] # Banda Superior
                stoch_k = stoch.iloc[:, 0].iloc[-1] # K do Estocástico
                
                stoch_val, l_band_val = stoch_k, l_band

                low_now = df['low'].iloc[-1]
                high_now = df['high'].iloc[-1]
                close_now = df['close'].iloc[-1]

                # Lógica PNY: Mínima fora, Fechamento dentro, Estocástico sobrevendido
                if low_now < l_band and close_now > l_band and stoch_k < PNY_STOCH_THRESHOLD_LOW:
                    sig_pny = "BUY"
                # Topo: Máxima fora, Fechamento dentro, Estocástico sobrecomprado
                elif high_now > u_band and close_now < u_band and stoch_k > PNY_STOCH_THRESHOLD_HIGH:
                    sig_pny = "SELL"

            # --- SELETOR DE SAÍDA BASEADO NO CONFIG ---
            if MODO_ESTRATEGIA == "ORIGINAL":
                return sig_original
            elif MODO_ESTRATEGIA == "EMA_ONLY":
                return sig_ema_only
            elif MODO_ESTRATEGIA == "EMA_SCALPER":
                return sig_ema_scalper
            elif MODO_ESTRATEGIA == "PNY":
                print(f"🤴 [PNY] Stoch: {stoch_val:.2f} | Banda_Inf: {l_band_val:.4f} | Preço: {df['close'].iloc[-1]:.4f}")
                return sig_pny
            elif MODO_ESTRATEGIA == "ALL":
                if "BUY" in [sig_original, sig_ema_only, sig_ema_scalper, sig_pny]:
                    return "BUY"
                if "SELL" in [sig_original, sig_ema_only, sig_ema_scalper, sig_pny]:
                    return "SELL"

            return "HOLD"
        except Exception as e:
            print(f"❌ Erro ao calcular sinal: {e}")
            return "HOLD"
