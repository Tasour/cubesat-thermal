"""Tests unitaires pour le modèle thermique."""
import yaml
import numpy as np
import pytest
from src.thermal_model import ThermalModel, N_NODES


@pytest.fixture
def config():
    with open("config/cubesat_config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def model(config):
    return ThermalModel(config)


class TestThermalModel:

    def test_capacities_positive(self, model):
        """Toutes les capacités thermiques doivent être strictement positives."""
        assert all(c > 0 for c in model.C)

    def test_GL_symmetric(self, model):
        """La matrice GL doit être symétrique (GL[i,j] == GL[j,i])."""
        diff = np.abs(model.GL - model.GL.T)
        assert diff.max() < 1e-10, f"GL non symétrique, diff max = {diff.max()}"

    def test_GL_nonnegative(self, model):
        """Toutes les conductances doivent être ≥ 0."""
        assert model.GL.min() >= 0.0

    def test_dTdt_shape(self, model):
        """dTdt doit retourner un vecteur de la bonne dimension."""
        T = np.full(N_NODES, 280.0)
        dT = model.dTdt(0.0, T)
        assert dT.shape == (N_NODES,)

    def test_dTdt_finite(self, model):
        """dTdt ne doit pas produire de NaN ou d'infini."""
        T  = np.full(N_NODES, 280.0)
        dT = model.dTdt(0.0, T)
        assert np.all(np.isfinite(dT)), f"dT/dt contient NaN ou inf : {dT}"

    def test_energy_balance_cold_dark(self, model):
        """
        Dans le noir complet (éclipse) et sans dissipation interne,
        une surface chaude doit se refroidir (dT/dt < 0 pour les faces).
        """
        cfg = {**model.config}
        cfg["power_dissipation"] = {k: 0.0 for k in cfg["power_dissipation"]}
        m2  = ThermalModel(cfg)

        T   = np.full(N_NODES, 350.0)     # Bien chaud
        t   = model.T_orb * 0.85          # En éclipse (beta=0)
        dT  = m2.dTdt(t, T)

        # Les faces extérieures doivent se refroidir (flux sortant > entrant)
        for i in range(6):
            assert dT[i] < 0, f"Face {i} ne refroidit pas en éclipse à haute T"
