# progressive_scaling_manager.py

import os
import sys

BASE_BOT_PATH = os.path.abspath('C:\Users\Administrator\Desktop\TradingBot')
if BASE_BOT_PATH not in sys.path:
    sys.path.append(BASE_BOT_PATH)

import settings_manager as manager_settings
import settings

def should_scale_position(current_profit_percentage, scaling_trigger=0.5):
    """
    Decide se aumentare la posizione in base al profitto attuale.

    Args:
        current_profit_percentage (float): Guadagno attuale sulla posizione (%).
        scaling_trigger (float): Percentuale di profitto che scatena lo scaling.

    Returns:
        bool: True se si deve scalare, False altrimenti.
    """

    return current_profit_percentage >= scaling_trigger

def calculate_additional_lot_size(initial_lot_size, scaling_factor=0.2, max_scaling_steps=2, scaling_step=1):
    """
    Calcola la dimensione dell'aggiunta alla posizione.

    Args:
        initial_lot_size (float): Lotto iniziale.
        scaling_factor (float): Percentuale dell'iniziale da aggiungere.
        max_scaling_steps (int): Numero massimo di scaling consentiti.
        scaling_step (int): Quanti scaling sono già avvenuti.

    Returns:
        float: Nuova aggiunta di lotto, 0 se limite raggiunto.
    """

    if scaling_step >= max_scaling_steps:
        return 0  # Non scalare più
    else:
        return initial_lot_size * scaling_factor
