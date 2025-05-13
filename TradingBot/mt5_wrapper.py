# mt5_wrapper.py

import MetaTrader5 as mt5

def initialize_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"[MT5] Initialization failed: {mt5.last_error()}")

def shutdown_mt5():
    mt5.shutdown()

def get_all_open_symbols():
    """
    Ritorna l'insieme dei simboli con posizioni aperte.
    """
    positions = mt5.positions_get()
    if positions is None:
        return set()
    return {pos.symbol for pos in positions}

def is_position_open(symbol):
    """
    Controlla se esiste almeno una posizione aperta per il simbolo.
    Ritorna True se c'è, False altrimenti.
    """
    positions = mt5.positions_get(symbol=symbol)
    return bool(positions)

def close_position(symbol, volume=None):
    """
    Chiude tutte le posizioni aperte per il simbolo specificato.
    Se volume è indicato, chiude quella quantità, altrimenti chiude il volume della posizione.
    """
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        print(f"[MT5] No open positions for {symbol}")
        return

    for pos in positions:
        vol = volume or pos.volume
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": vol,
            "type": close_type,
            "position": pos.ticket,
            "deviation": 20,
            "magic": 0,
            "comment": "Auto-close by bot",
        }
        result = mt5.order_send(request)
        print(f"[MT5] Close {symbol} → Ticket {pos.ticket} → Result: {result.retcode}")