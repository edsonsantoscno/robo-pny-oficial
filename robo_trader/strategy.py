    def calculate_signal(self, df):
        """
        Processa os dados das séries temporais através de frameworks matemáticos
        e retorna sinais puros de BUY, SELL ou HOLD.
        """
        try:
            if df is None or len(df) < 100: # Limite de segurança técnica para comportar EMA 100
                return "HOLD"

            # --- 1. SINAL ORIGINAL (RSI + MACD) ---
            sig_original = "HOLD"
            rsi = ta.rsi(df['close'], length=RSI_PERIOD)
            macd = ta.macd(df['close'], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
            
            if rsi is not None and macd is not None and not rsi.empty and not macd.empty:
                hist_col = f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
                if hist_col in macd.columns:
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
            
            if ema_f is not None and ema_s is not None and ema_l is not None and not ema_f.empty:
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

            # --- 4. SINAL PRÍNCIPE DE NY (PNY - Topo e Fundo) ---
            sig_pny = "HOLD"
            bb = ta.bbands(df['close'], length=PNY_BB_PERIOD, std=PNY_BB_STD)
            stoch = ta.stoch(df['high'], df['low'], df['close'], k=PNY_STOCH_K, d=3)
            stoch_val, l_band_val = 0.0, 0.0
            
            if bb is not None and stoch is not None and not bb.empty and not stoch.empty:
                # Mapeamento por nome de coluna técnica gerada pelo pandas-ta
                bb_low_col = f'BBL_{PNY_BB_PERIOD}_{PNY_BB_STD}'
                bb_upp_col = f'BBU_{PNY_BB_PERIOD}_{PNY_BB_STD}'
                
                # CORREÇÃO #2: String do estocástico limpa (removido espaço em branco oculto)
                stoch_k_col = f'STOCHk_{PNY_STOCH_K}_3_3'

                # Mecanismo de fallback por índice posicional caso haja variações na versão do pandas-ta
                l_band = bb[bb_low_col].iloc[-1] if bb_low_col in bb.columns else bb.iloc[:, 0].iloc[-1]
                u_band = bb[bb_upp_col].iloc[-1] if bb_upp_col in bb.columns else bb.iloc[:, 2].iloc[-1]
                stoch_k = stoch[stoch_k_col].iloc[-1] if stoch_k_col in stoch.columns else stoch.iloc[:, 0].iloc[-1]
                
                stoch_val, l_band_val = stoch_k, l_band
                low_now = df['low'].iloc[-1]
                high_now = df['high'].iloc[-1]
                close_now = df['close'].iloc[-1]

                # Lógica PNY: Fechamento dentro/fora combinado com bandas de oscilação e exaustão
                if low_now < l_band and close_now > l_band and stoch_k < PNY_STOCH_THRESHOLD_LOW:
                    sig_pny = "BUY"
                elif high_now > u_band and close_now < u_band and stoch_k > PNY_STOCH_THRESHOLD_HIGH:
                    sig_pny = "SELL"

            # --- SELETOR DE RETORNO INTEGRADO E SINCRONIZADO AO SAAS ---
            if MODO_ESTRATEGIA == "ORIGINAL":
                return sig_original
            elif MODO_ESTRATEGIA == "EMA_ONLY":
                return sig_ema_only
            # CORREÇÃO #1: Ajustado de "EMA_SCALPER" para "EMA_SCALP" para casar com as rotas
            elif MODO_ESTRATEGIA == "EMA_SCALP":
                return sig_ema_scalper
            elif MODO_ESTRATEGIA == "PNY":
                print(f"🤴 [PNY] Stoch: {stoch_val:.2f} | Banda_Inf: {l_band_val:.4f} | Preço: {df['close'].iloc[-1]:.4f}")
                return sig_pny
            
            # CORREÇÃO #3: Removido o bloco "ALL" obsoleto para evitar conflitos de ordens concorrentes
            return "HOLD"
        except Exception as e:
            print(f"❌ Erro ao calcular sinal interno: {e}")
            return "HOLD"
