"""
thermal_model.py — Modèle nodal thermique du CubeSat (9 nœuds)

Index des nœuds :
  0 : Face +X      3 : Face -Y
  1 : Face -X      4 : Face +Z (zenith)
  2 : Face +Y      5 : Face -Z (nadir)
                   6 : Structure interne
                   7 : OBC + EPS (électronique)
                   8 : Payload (caméra)
"""

import numpy as np
from .orbital import OrbitalParameters
from .environment import EnvironmentModel

N_NODES    = 9
NODE_NAMES = ["+X", "-X", "+Y", "-Y", "+Z", "-Z", "Structure", "OBC/EPS", "Payload"]

# Correspondance face-name → index de nœud
FACE_TO_IDX = {"+X": 0, "-X": 1, "+Y": 2, "-Y": 3, "+Z": 4, "-Z": 5}


class ThermalModel:
    """
    Encapsule toute la physique thermique du CubeSat.
    Expose la méthode dTdt(t, T) utilisée par solve_ivp.
    """

    def __init__(self, config: dict):
        self.config = config
        self.orb    = OrbitalParameters(
            altitude_km = config["orbit"]["altitude_km"],
            beta_deg    = config["orbit"]["beta_angle_deg"],
        )
        self.env    = EnvironmentModel(config)
        self.T_orb  = self.orb.T_orb

        # Vecteur des capacités thermiques C_i = m_i * cp_i [J/K]
        self.C  = self._build_capacities(config)

        # Matrice des conductances linéaires GL [W/K]
        # GL[i,j] = conductance entre le nœud i et le nœud j
        self.GL = self._build_GL_matrix(config)

        # Pré-calculer les profils de puissance interne
        self._pd = config["power_dissipation"]

    # ─── Construction des matrices ─────────────────────────────────────────

    def _build_capacities(self, config: dict) -> np.ndarray:
        C = np.zeros(N_NODES)

        # Nœuds 0–5 : les 6 faces
        face_order = ["plus_X", "minus_X", "plus_Y", "minus_Y", "plus_Z", "minus_Z"]
        for i, fname in enumerate(face_order):
            fc   = config["faces"][fname]
            C[i] = fc["mass_kg"] * fc["cp_JkgK"]

        # Nœuds 6–8 : nœuds internes
        ic   = config["internal_nodes"]
        C[6] = ic["structure"]["mass_kg"] * ic["structure"]["cp_JkgK"]
        C[7] = ic["obc_eps"]["mass_kg"]   * ic["obc_eps"]["cp_JkgK"]
        C[8] = ic["payload"]["mass_kg"]   * ic["payload"]["cp_JkgK"]

        return C

    def _build_GL_matrix(self, config: dict) -> np.ndarray:
        GL = np.zeros((N_NODES, N_NODES))
        gl = config["conductances_GL"]

        # Toutes les faces (0–5) sont conductivement liées à la structure (6)
        for i in range(6):
            v = gl["face_to_structure"]
            GL[i, 6] = v
            GL[6, i] = v

        # Structure (6) ↔ OBC/EPS (7)
        v = gl["structure_to_obc"]
        GL[6, 7] = v
        GL[7, 6] = v

        # Structure (6) ↔ Payload (8)
        v = gl["structure_to_payload"]
        GL[6, 8] = v
        GL[8, 6] = v

        # OBC/EPS (7) ↔ Payload (8)  [très faible — vide entre les cartes]
        v = gl["obc_to_payload"]
        GL[7, 8] = v
        GL[8, 7] = v

        return GL

    # ─── Puissance interne dissipée ────────────────────────────────────────

    def _internal_power(self, t: float) -> np.ndarray:
        """
        Retourne le vecteur de dissipation thermique [W] pour chaque nœud.
        Dépend de la phase orbitale (soleil vs éclipse).
        """
        from .orbital import in_eclipse
        sunlight = not in_eclipse(t, self.orb)
        pd = self._pd
        Q  = np.zeros(N_NODES)

        if sunlight:
            # Nœud 7 (OBC + EPS + Radio) : mode actif au soleil
            Q[7] = pd["obc_W"] + pd["eps_sun_W"] + pd["radio_sun_W"]
            # Nœud 8 (Payload) : caméra active au soleil
            Q[8] = pd["payload_sun_W"]
        else:
            # Nœud 7 : mode veille pendant l'éclipse
            Q[7] = pd["obc_W"] + pd["eps_eclipse_W"]
            # Nœud 8 : payload éteint
            Q[8] = pd["payload_eclipse_W"]

        # ADCS (réaction magnétique) : toujours actif → dans la structure
        Q[6] = pd["adcs_W"]

        return Q

    # ─── Équation différentielle principale ────────────────────────────────

    def dTdt(self, t: float, T: np.ndarray) -> np.ndarray:
        """
        Fonction d'état pour scipy.integrate.solve_ivp.

        T [K] → dT/dt [K/s]

        Bilan par nœud i :
          C_i * dT_i/dt = Q_ext,i - Q_rad_out,i + Q_int,i + Σ_j GL_ij*(Tj - Ti)
        """
        dT    = np.zeros(N_NODES)
        fluxes = self.env.compute(t, self.orb)
        Q_int  = self._internal_power(t)

        for i in range(N_NODES):
            Q_net = Q_int[i]          # Sources internes (électronique)

            # ── Flux externes (uniquement sur les faces, nœuds 0–5) ─────────
            if i < 6:
                face_name = NODE_NAMES[i]
                fl = fluxes[face_name]

                # Flux entrants
                Q_net += fl["solar"] + fl["albedo"] + fl["earth_ir"]

                # Flux sortant : rayonnement vers l'espace (Stefan-Boltzmann)
                # Q_out = ε·σ·A·T⁴ = rad_coef * T⁴
                Q_net -= fl["rad_coef"] * T[i] ** 4

            # ── Conduction avec les nœuds voisins ───────────────────────────
            for j in range(N_NODES):
                if self.GL[i, j] > 0.0:
                    Q_net += self.GL[i, j] * (T[j] - T[i])

            # ── Équation de bilan ────────────────────────────────────────────
            dT[i] = Q_net / self.C[i]

        return dT
