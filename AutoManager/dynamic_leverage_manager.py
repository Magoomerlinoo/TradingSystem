# dynamic_leverage_manager.py

import os
import sys

BASE_BOT_PATH = os.path.abspath('C:\Users\Administrator\Desktop\TradingBot')
if BASE_BOT_PATH not in sys.path:
    sys.path.append(BASE_BOT_PATH)

import settings_manager as manager_settings
import settings


def calculate_dynamic_leverage(confidence_score, market_phase, base_leverage=1.0, max_leverage=3.0):
    """
    Calcola la leva dinamica in base alla qualità del segnale e alla fase di mercato.

    Args:
        confidence_score (float): Score di fiducia del segnale (0-1).
        market_phase (str): Fase di mercato corrente ("bullish", "bearish", "neutral", "volatile").
        base_leverage (float): Leva di partenza.
        max_leverage (float): Leva massima consentita.

    Returns:
        float: Leva da applicare alla posizione.
    """

    # Fattore di amplificazione leva basato su confidence
    if confidence_score >= 0.9:
        confidence_multiplier = 1.5
    elif confidence_score >= 0.8:
        confidence_multiplier = 1.3
    elif confidence_score >= 0.7:
        confidence_multiplier = 1.1
    else:
        confidence_multiplier = 1.0  # Non aumentiamo leva su segnali deboli

    # Modifica in base alla fase di mercato
    if market_phase in ["bullish", "bearish"]:
        phase_multiplier = 1.2
    elif market_phase == "volatile":
        phase_multiplier = 0.8  # Meno leva in alta volatilità
    else:
        phase_multiplier = 1.0

    # Calcolo leva finale
    dynamic_leverage = base_leverage * confidence_multiplier * phase_multiplier

    # Limitazione leva massima
    dynamic_leverage = min(dynamic_leverage, max_leverage)

    return dynamic_leverage
