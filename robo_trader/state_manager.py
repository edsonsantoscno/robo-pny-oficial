import json
import os

STATE_FILE = "trading_state.json"

# Adicionado o parâmetro current_symbol para identificar a moeda da operação
def save_state(position_active, entry_price, entry_quantity, banca_inicial, ganho_dia, current_symbol=None):
    state = {
        "position_active": position_active,
        "entry_price": entry_price,
        "entry_quantity": entry_quantity,
        "banca_inicial": banca_inicial,
        "ganho_dia": ganho_dia,
        "current_symbol": current_symbol  # NOVIDADE: Salva qual moeda está operando
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def clear_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
