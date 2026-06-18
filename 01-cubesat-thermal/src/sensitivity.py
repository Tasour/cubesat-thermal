"""
sensitivity.py — Analyse paramétrique de sensibilité thermique

Pour chaque paramètre d'étude, lance une série de simulations
et collecte T_min / T_max par nœud.
"""

import copy
import numpy as np
from .thermal_model import ThermalModel, NODE_NAMES
from .solver import run_simulation


def run_sensitivity(base_config: dict, param_name: str,
                    values: list, verbose: bool = True) -> list:
    """
    Lance une simulation pour chaque valeur de la liste.

    param_name : clé du paramètre à varier (voir PARAM_MAP ci-dessous)
    values     : liste de valeurs à tester
    
    Retourne une liste de dicts :
    [
      {'value': v, 'T_min_C': array[9], 'T_max_C': array[9], 'T_mean_C': array[9]},
      ...
    ]
    """
    PARAM_MAP = {
        "beta":          ("orbit", "beta_angle_deg"),
        "altitude":      ("orbit", "altitude_km"),
        "alpha_panels":  None,    # cas spécial : plusieurs faces
        "epsilon_panels": None,   # cas spécial
        "power_payload": ("power_dissipation", "payload_sun_W"),
        "power_obc":     ("power_dissipation", "obc_W"),
    }

    results = []

    for val in values:
        cfg = copy.deepcopy(base_config)

        # Modification du paramètre
        if param_name in ("alpha_panels", "epsilon_panels"):
            prop = "alpha" if param_name == "alpha_panels" else "epsilon"
            for face in ["plus_X", "minus_X", "plus_Y", "minus_Y", "plus_Z", "minus_Z"]:
                cfg["faces"][face][prop] = val
        else:
            section, key = PARAM_MAP[param_name]
            cfg[section][key] = val

        if verbose:
            print(f"  {param_name} = {val} ...", end="", flush=True)

        model  = ThermalModel(cfg)
        result = run_simulation(model, cfg)

        # Extraire les stats sur le régime établi
        T = result.T_steady_C

        if verbose:
            print(f" Payload T=[{T[8].min():.1f}, {T[8].max():.1f}]°C")

        results.append({
            "value":    val,
            "T_min_C":  T.min(axis=1),    # min temporel pour chaque nœud
            "T_max_C":  T.max(axis=1),
            "T_mean_C": T.mean(axis=1),
            "delta_T":  T.max(axis=1) - T.min(axis=1),
        })

    return results


def sensitivity_plot_data(results: list, node_name: str) -> dict:
    """
    Extrait les données de T_min et T_max pour un nœud donné,
    prêtes à être tracées.
    """
    idx    = NODE_NAMES.index(node_name)
    values = [r["value"]       for r in results]
    T_mins = [r["T_min_C"][idx] for r in results]
    T_maxs = [r["T_max_C"][idx] for r in results]
    return {"values": values, "T_min": T_mins, "T_max": T_maxs}
