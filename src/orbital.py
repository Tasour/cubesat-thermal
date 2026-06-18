"""
orbital.py — Mécanique orbitale pour simulation thermique CubeSat

Hypothèses simplificatrices :
- Orbite parfaitement circulaire (excentricité nulle)
- Angle bêta constant pendant la simulation (valide sur quelques orbites)
- Ombre de la Terre cylindrique (l'ombre pénombre est ignorée)
- Orientation satellite : nadir-pointing (une face toujours vers la Terre)
"""

import numpy as np
from dataclasses import dataclass, field

# ─── Constantes physiques ────────────────────────────────────────────────────
R_EARTH  = 6_371_000.0      # Rayon moyen de la Terre [m]
MU_EARTH = 3.986_004_418e14 # Paramètre gravitationnel standard [m³/s²]


@dataclass
class OrbitalParameters:
    """
    Regroupe tous les paramètres orbitaux calculés à partir de l'altitude et de beta.

    altitude_km : altitude de l'orbite circulaire [km]
    beta_deg    : angle entre le plan orbital et la direction Soleil [degrés]
                  0° = éclipses maximales (worst cold case)
                  90° = jamais d'éclipse (worst hot case)
    """
    altitude_km: float
    beta_deg:    float

    # Ces champs sont calculés automatiquement dans __post_init__
    r:           float = field(init=False)
    T_orb:       float = field(init=False)
    omega:       float = field(init=False)
    beta:        float = field(init=False)
    beta_crit:   float = field(init=False)

    def __post_init__(self):
        self.r        = R_EARTH + self.altitude_km * 1_000.0
        self.T_orb    = 2 * np.pi * np.sqrt(self.r**3 / MU_EARTH)
        self.omega    = 2 * np.pi / self.T_orb
        self.beta     = np.radians(self.beta_deg)
        # Angle critique au-delà duquel il n'y a plus d'éclipse
        self.beta_crit = np.arcsin(R_EARTH / self.r)

    @property
    def eclipse_fraction(self) -> float:
        """Fraction de l'orbite passée en éclipse (0.0 à ~0.4)."""
        if abs(self.beta) >= self.beta_crit:
            return 0.0
        num = np.sqrt(1.0 - (R_EARTH / self.r)**2 * np.cos(self.beta)**2)
        return (1.0 / np.pi) * np.arccos(num / np.cos(self.beta))

    @property
    def eclipse_duration_min(self) -> float:
        return self.eclipse_fraction * self.T_orb / 60.0

    @property
    def sunlight_duration_min(self) -> float:
        return (1.0 - self.eclipse_fraction) * self.T_orb / 60.0

    def summary(self) -> dict:
        return {
            "altitude_km":          self.altitude_km,
            "beta_deg":             self.beta_deg,
            "period_min":           round(self.T_orb / 60.0, 2),
            "eclipse_fraction":     round(self.eclipse_fraction, 4),
            "eclipse_min":          round(self.eclipse_duration_min, 2),
            "sunlight_min":         round(self.sunlight_duration_min, 2),
            "beta_critical_deg":    round(np.degrees(self.beta_crit), 2),
        }


def sun_vector_rtn(t: float, orb: OrbitalParameters) -> np.ndarray:
    """
    Vecteur unitaire pointant vers le Soleil, exprimé dans le repère RTN.

    Repère RTN (Radial – Transverse – Normal) :
      R : du centre Terre vers le satellite (radial)
      T : perpendiculaire à R dans le plan orbital (transverse, sens du mouvement)
      N : perpendiculaire au plan orbital (normal)

    Avec l'hypothèse beta constant et orbite circulaire :
      La composante N du Soleil = sin(beta)  [constante]
      Les composantes R et T tournent avec la position du satellite.
    """
    theta = orb.omega * t          # Position angulaire sur l'orbite [rad]
    beta  = orb.beta

    s_R =  np.cos(beta) * np.sin(theta)   # Note : signe selon convention
    s_T =  np.cos(beta) * np.cos(theta)
    s_N =  np.sin(beta)

    vec = np.array([s_R, s_T, s_N])
    return vec / np.linalg.norm(vec)       # Normalisation de sécurité


def in_eclipse(t: float, orb: OrbitalParameters) -> bool:
    """
    Retourne True si le satellite est dans l'ombre de la Terre au temps t.

    Méthode : ombre cylindrique.
    Le satellite est en éclipse si ET SEULEMENT SI :
      1. Il se trouve "derrière" la Terre par rapport au Soleil (x_shadow > 0)
      2. Sa distance à l'axe Soleil-Terre est inférieure au rayon terrestre
    """
    if abs(orb.beta) >= orb.beta_crit:
        return False   # Jamais d'éclipse pour ce beta

    theta = orb.omega * t
    beta  = orb.beta
    r     = orb.r

    # Coordonnées dans le repère centré Terre, axe X = direction anti-Soleil
    # x > 0 signifie "derrière la Terre"
    x = -r * np.cos(beta) * np.cos(theta)
    y =  r * np.cos(beta) * np.sin(theta)
    z =  r * np.sin(beta)

    # Dans l'ombre si derrière la Terre ET dans le cylindre d'ombre
    return bool(x > 0 and np.sqrt(y**2 + z**2) < R_EARTH)
