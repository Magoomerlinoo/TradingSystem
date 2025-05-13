# execution/trade_manager.py
import MetaTrader5 as mt5
import settings
from datetime import datetime
import pandas as pd
import pandas_ta as ta

class TradeManager:
    def __init__(self, manual_position_multiplier=settings.MANUAL_POSITION_MULTIPLIER):
        self.manual_position_multiplier = manual_position_multiplier
        if not mt5.initialize():
            raise ConnectionError(f"MT5 init failed: {mt5.last_error()}")

    def update_trailing_stop(self, symbol):
        # Fetch open position for this symbol
        positions = mt5.positions_get(symbol=symbol)
        if not positions or len(positions) == 0:
            return  # No open position to manage

        position = positions[0]
        is_buy = position.type == mt5.POSITION_TYPE_BUY

        # Get current price based on direction
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return

        current_price = tick.bid if is_buy else tick.ask
        current_sl = position.sl

        # Fetch recent candles for ATR calculation
        rates = mt5.copy_rates_from_pos(symbol, settings.DEFAULT_TIMEFRAME, 0, 20)
        if rates is None or len(rates) < 14:
            return

        df = pd.DataFrame(rates)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        atr = df['atr'].iloc[-1]

        # Calculate ideal SL
        sl_buffer = settings.ATR_MULTIPLIER * settings.SL_MULTIPLIER
        new_sl = current_price - sl_buffer if is_buy else current_price + sl_buffer

        # Only update SL if it's more favorable
        update = False
        if is_buy and (current_sl == 0 or new_sl > current_sl):
            update = True
        elif not is_buy and (current_sl == 0 or new_sl < current_sl):
            update = True

        if update:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": symbol,
                "position": position.ticket,
                "sl": new_sl,
                "tp": position.tp,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            mt5.order_send(request)

    def set_manual_multiplier(self, new_multiplier):
        self.manual_position_multiplier = new_multiplier
        print(f"Multiplier updated: {new_multiplier}")

    def calculate_position_size(self, balance, symbol, entry_price, sl_price, risk_percent, confidence):
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info or entry_price == sl_price:
            return symbol_info.volume_min if symbol_info else 0.01

        risk_amount = balance * risk_percent
        pip_value = symbol_info.point * 10
        risk_pips = abs(entry_price - sl_price) / symbol_info.point
        lot_size = risk_amount / (risk_pips * pip_value)
        lot_size *= confidence * self.manual_position_multiplier
        # assicurarsi nei limiti
        return max(symbol_info.volume_min, min(symbol_info.volume_max, round(lot_size, 2)))

    def execute_trade(self, symbol, direction, entry_price, atr, lot_size, confidence):
        symbol_info_tick = mt5.symbol_info_tick(symbol)
        if not symbol_info_tick:
            print(f"Trade failed: No tick data for {symbol}")
            return None

        # SL base calcolato su ATR
        sl_distance = atr * 2
        if direction == 'long':
            sl = entry_price - sl_distance
        else:
            sl = entry_price + sl_distance

        # R:R dinamico
        rr_ratio = settings.DEFAULT_RR_RATIO
        if settings.DYNAMIC_RR_ENABLED:
            rr_ratio *= confidence
            rr_ratio = min(3.0, max(1.0, rr_ratio))  # bounds di sicurezza

        tp_distance = sl_distance * rr_ratio
        if direction == 'long':
            tp = entry_price + tp_distance
        else:
            tp = entry_price - tp_distance

        order_type = mt5.ORDER_TYPE_BUY if direction == 'long' else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": entry_price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 123456,
            "comment": "AI bot trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[TradeManager] Trade failed for {symbol}")
            print(f"  ↳ retcode: {result.retcode}")
            print(f"  ↳ comment: {result.comment}")
            print(f"  ↳ request_id: {result.request_id}")
            print(f"  ↳ order: {result.order}")
            print(f"  ↳ volume: {lot_size} | direction: {direction}")
            return None

        return {
            'ticket': result.order,
            'symbol': symbol,
            'direction': direction,
            'size': lot_size,
            'entry': entry_price,
            'filled_price': result.price,
            'sl': sl,
            'tp': tp,
            'time': datetime.now(),
            'confidence': confidence,
            'rr_ratio': rr_ratio
        }


    def close_trade(self, ticket):
        positions = mt5.positions_get()
        # filtrare per ticket
        pos_list = [p for p in positions if p.ticket == ticket] if positions else []
        if not pos_list:
            print(f"Position not found: {ticket}")
            return False

        pos = pos_list[0]
        symbol = pos.symbol
        volume = pos.volume
        direction = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(symbol)
        price = (tick.bid if direction == mt5.ORDER_TYPE_SELL else tick.ask) if tick else 0

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": direction,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": 123456,
            "comment": "Manual close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    # Funzione aggiuntiva per chiusura sicura exportata
    @staticmethod
    def close_position_safely(symbol):
        """
        Chiude tutte le posizioni aperte per il simbolo e
        restituisce True se tutte le chiusure sono andate a buon fine.
        """
        if not mt5.initialize():
            print(f"[TradeManager] MT5 init failed in close_position_safely: {mt5.last_error()}")
            return False

        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return False

        results = []
        for pos in positions:
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                results.append(False)
                continue
            price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
            opp_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": opp_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 10,
                "magic": 123456,
                "comment": "Auto close safely",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(request)
            results.append(res.retcode == mt5.TRADE_RETCODE_DONE)

        return all(results)
    
    def revalidate_stop_targets(self, open_positions):
        """
        Dopo il riavvio, riallinea SL/TP o monitor interni per le posizioni aperte.
        """
        if not open_positions:
            print("[TradeManager] Nessuna posizione aperta da riconciliare.")
            return

        for pos in open_positions:
            symbol = pos.symbol
            ticket = pos.ticket
            sl     = pos.sl
            tp     = pos.tp
            entry  = pos.price_open
            volume = pos.volume
            direction = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"

            print(f"[TM] ➕ Validazione SL/TP → {symbol} (#{ticket}) {direction} {volume} @ {entry}")
            print(f"     SL attuale: {sl} | TP attuale: {tp}")

            # (Opzionale) Riattiva sistemi dinamici se servono:
            # es. trailing, break-even, TP multipli
            # self.activate_trailing_for(symbol, ticket, sl, tp)
