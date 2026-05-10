# strategy.py
import pandas as pd
from config import (
    RSI_PERIOD, RSI_BUY_THRESHOLD, RSI_SELL_THRESHOLD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL
)

class MovingAverageStrategy:
    def __init__(self, binance_client):
        self.client      = binance_client
        self.fast_period = 9
        self.slow_period = 21

    def get_data(self, symbol, interval, limit=100):
        try:
            klines = self.client.get_klines(symbol, interval, limit=limit)
            if not klines:
                return None

            df = pd.DataFrame(klines, columns=[
                "open_time", "open", "high", "low", "close",
                "volume", "close_time", "quote_volume", "trades",
                "taker_buy_base", "taker_buy_quote", "ignore"
            ])

            df["close"]  = pd.to_numeric(df["close"])
            df["volume"] = pd.to_numeric(df["volume"])
            return df

        except Exception as e:
            print(f"❌ Erro ao buscar dados: {e}")
            return None

    def calculate_ema(self, closes, period):
        return closes.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, closes, period=RSI_PERIOD):
        delta    = closes.diff()
        gain     = delta.where(delta > 0, 0.0)
        loss     = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs       = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, closes):
        ema_fast    = closes.ewm(span=MACD_FAST,    adjust=False).mean()
        ema_slow    = closes.ewm(span=MACD_SLOW,    adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
        histogram   = macd_line - signal_line
        return macd_line, signal_line, histogram

    def calculate_volume_alto(self, df):
        volume_media = df["volume"].rolling(window=20).mean()
        return df["volume"].iloc[-1] > volume_media.iloc[-1]

    def calculate_signal(self, df):
        try:
            closes = df["close"]

            # EMA 9 e 21
            ema_fast = self.calculate_ema(closes, self.fast_period)
            ema_slow = self.calculate_ema(closes, self.slow_period)

            # RSI período 9
            rsi = self.calculate_rsi(closes, RSI_PERIOD)

            # MACD 12/26/9
            macd_line, signal_line, _ = self.calculate_macd(closes)

            # Valores atuais
            ema_fast_current = ema_fast.iloc[-1]
            ema_slow_current = ema_slow.iloc[-1]

            rsi_current = rsi.iloc[-1]

            macd_current   = macd_line.iloc[-1]
            # macd_prev      = macd_line.iloc[-2]
            signal_current = signal_line.iloc[-1]
            # signal_prev    = signal_line.iloc[-2]

            volume_alto = self.calculate_volume_alto(df)

            print(f"📊 EMA9: {ema_fast_current:.2f} | EMA21: {ema_slow_current:.2f} | "
                  f"RSI({RSI_PERIOD}): {rsi_current:.2f} | "
                  f"MACD: {macd_current:.4f} | Sinal MACD: {signal_current:.4f} | "
                  f"Volume alto: {volume_alto}")

            # Tendência das EMAs (sem exigir cruzamento)
            tendencia_alta  = ema_fast_current > ema_slow_current
            tendencia_baixa = ema_fast_current < ema_slow_current

            # Confirmação MACD
            macd_bullish = macd_current > signal_current
            macd_bearish = macd_current < signal_current

            # BUY: EMA9 > EMA21 + RSI < threshold + MACD bullish
            if tendencia_alta:
                if rsi_current < RSI_BUY_THRESHOLD and macd_bullish:
                    if volume_alto:
                        print(f"✅ Sinal BUY confirmado | RSI: {rsi_current:.2f} < {RSI_BUY_THRESHOLD} | "
                              f"MACD bullish | Volume alto")
                    else:
                        print(f"✅ Sinal BUY confirmado | RSI: {rsi_current:.2f} < {RSI_BUY_THRESHOLD} | "
                              f"MACD bullish | Volume normal")
                    return "BUY"
                else:
                    motivo = []
                    if rsi_current >= RSI_BUY_THRESHOLD:
                        motivo.append(f"RSI {rsi_current:.2f} >= {RSI_BUY_THRESHOLD}")
                    if not macd_bullish:
                        motivo.append("MACD não bullish")
                    print(f"⏸️  HOLD | {' | '.join(motivo)}")
                    return "HOLD"

            # SELL: EMA9 < EMA21 + RSI > threshold + MACD bearish
            if tendencia_baixa:
                if rsi_current > RSI_SELL_THRESHOLD and macd_bearish:
                    print(f"✅ Sinal SELL confirmado | RSI: {rsi_current:.2f} > {RSI_SELL_THRESHOLD} | "
                          f"MACD bearish")
                    return "SELL"
                else:
                    motivo = []
                    if rsi_current <= RSI_SELL_THRESHOLD:
                        motivo.append(f"RSI {rsi_current:.2f} <= {RSI_SELL_THRESHOLD}")
                    if not macd_bearish:
                        motivo.append("MACD não bearish")
                    print(f"⏸️  HOLD | {' | '.join(motivo)}")
                    return "HOLD"

            return "HOLD"

        except Exception as e:
            print(f"❌ Erro ao calcular sinal: {e}")
            return "HOLD"