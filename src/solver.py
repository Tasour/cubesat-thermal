"""
solver.py — Intégration numérique du système d'ODE thermique

Utilise scipy.integrate.solve_ivp avec la méthode RK45 (Runge-Kutta adaptatif).
Retourne un objet SimulationResult avec les méthodes de post-traitement.
"""

import numpy as np
from scipy.integrate import solve_ivp
from dataclasses import dataclass, field
from typing import List


@dataclass
class SimulationResult:
    """
    Contient les résultats bruts de la simulation et des méthodes utilitaires.
    """
    t:               np.ndarray          # Vecteur temps [s]
    T_K:             np.ndarray          # Températures [K] — shape (9, N_points)
    node_names:      List[str]
    T_orb:           float               # Période orbitale [s]
    n_warmup_orbits: int = 2

    # ── Conversions ────────────────────────────────────────────────────────

    @property
    def T_C(self) -> np.ndarray:
        """Températures en degrés Celsius."""
        return self.T_K - 273.15

    @property
    def t_min(self) -> np.ndarray:
        """Temps en minutes."""
        return self.t / 60.0

    # ── Régime établi (après warmup) ──────────────────────────────────────

    @property
    def _steady_mask(self) -> np.ndarray:
        return self.t >= self.n_warmup_orbits * self.T_orb

    @property
    def t_steady_min(self) -> np.ndarray:
        return self.t[self._steady_mask] / 60.0

    @property
    def T_steady_C(self) -> np.ndarray:
        return self.T_C[:, self._steady_mask]

    # ── Statistiques ──────────────────────────────────────────────────────

    def summary(self) -> dict:
        """
        Tableau récapitulatif T_min / T_max / T_mean / ΔT
        calculé sur le régime établi seulement.
        """
        T = self.T_steady_C
        return {
            name: {
                "T_min_C":  round(float(T[i].min()),  1),
                "T_max_C":  round(float(T[i].max()),  1),
                "T_mean_C": round(float(T[i].mean()), 1),
                "delta_T":  round(float(T[i].max() - T[i].min()), 1),
            }
            for i, name in enumerate(self.node_names)
        }

    def thermal_margins(self, limits: dict) -> dict:
        """
        Calcule les marges thermiques (distance aux limites) pour chaque nœud.
        Une marge négative signifie un dépassement de limite → problème !
        """
        s = self.summary()

        # Mapping nœud → clé de limite dans la config
        node_to_limit = {
            "+X": "panels",    "-X": "panels",
            "+Y": "panels",    "-Y": "panels",
            "+Z": "panels",    "-Z": "panels",
            "Structure": "structure",
            "OBC/EPS":   "obc_eps",
            "Payload":   "payload",
        }

        margins = {}
        for name in self.node_names:
            lim_key = node_to_limit[name]
            lim     = limits[lim_key]
            stats   = s[name]
            margins[name] = {
                "margin_cold_K": round(stats["T_min_C"] - lim["min_C"], 1),
                "margin_hot_K":  round(lim["max_C"] - stats["T_max_C"], 1),
                "T_min_C":       stats["T_min_C"],
                "T_max_C":       stats["T_max_C"],
                "limit_min_C":   lim["min_C"],
                "limit_max_C":   lim["max_C"],
            }
        return margins


def run_simulation(model, config: dict) -> SimulationResult:
    """
    Lance la simulation thermique et retourne un SimulationResult.

    model  : instance de ThermalModel
    config : dictionnaire de configuration (issu du YAML)
    """
    sim = config["simulation"]

    # Condition initiale : tous les nœuds à la même température
    T_init = np.full(9, sim["T_init_K"])

    # Horizon de simulation
    t_final = sim["n_orbits"] * model.T_orb
    t_eval  = np.linspace(0.0, t_final, sim["n_points"])

    # Pas maximum : au moins 200 pas par orbite pour bien résoudre les transitions
    max_step = model.T_orb / 200.0

    print(f"  Lancement solve_ivp  (RK45, {sim['n_orbits']} orbites, "
          f"{sim['n_points']} points)...")

    sol = solve_ivp(
        fun           = lambda t, T: model.dTdt(t, T),
        t_span        = (0.0, t_final),
        y0            = T_init,
        method        = "RK45",
        t_eval        = t_eval,
        rtol          = 1e-4,
        atol          = 1e-6,
        max_step      = max_step,
        dense_output  = False,
    )

    if not sol.success:
        raise RuntimeError(f"Simulation échouée : {sol.message}")

    print(f"  Terminé en {sol.t[-1]/60:.1f} min simulées  "
          f"({sol.nfev} évaluations de la fonction)")

    from .thermal_model import NODE_NAMES
    return SimulationResult(
        t               = sol.t,
        T_K             = sol.y,
        node_names      = NODE_NAMES,
        T_orb           = model.T_orb,
        n_warmup_orbits = sim["n_warmup_orbits"],
    )
